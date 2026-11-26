"""Deterministic SEC filing retrieval, section splitter, and XBRL segment parser (solution plan Stage 2).

Uses only Python's standard library (``html.parser``, ``xml.etree.ElementTree``, ``hashlib``)
so deployment needs no extra packages. Filed SEC accessions are immutable, so cached documents
under ``.cache/sec_filings/`` are content-addressed with SHA-256 provenance and never expire.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import html as html_lib
import json
import os
import re
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
CACHE_DIR = ROOT / ".cache" / "sec_filings"

SEGMENT_AXES = (
    "StatementBusinessSegmentsAxis",
    "SegmentsAxis",
)
SEGMENT_REVENUE_CONCEPTS = (
    "RevenueFromContractWithCustomerExcludingAssessedTax",
    "Revenues",
    "SalesRevenueNet",
    "SalesRevenueGoodsNet",
    "RevenueFromExternalCustomers",
    "Revenue",
    "RevenueFromContractsWithCustomers",
)
SEGMENT_OPERATING_INCOME_CONCEPTS = (
    "OperatingIncomeLoss",
    "ProfitLossFromOperatingActivities",
    "SegmentReportingInformationOperatingIncomeLoss",
)
RECONCILING_MEMBER_TOKENS = (
    "corporate",
    "reconcil",
    "eliminat",
    "unallocat",
    "intersegment",
    "allother",
    "total",
)


@dataclass(frozen=True)
class FilingRef:
    cik: int
    accession_number: str
    form: str
    filing_date: str
    report_date: str
    primary_document: str

    @property
    def cik_key(self) -> str:
        return f"CIK{self.cik:010d}"

    @property
    def accession_nodash(self) -> str:
        return self.accession_number.replace("-", "")

    @property
    def base_url(self) -> str:
        return f"https://www.sec.gov/Archives/edgar/data/{self.cik}/{self.accession_nodash}"

    @property
    def url(self) -> str:
        return f"{self.base_url}/{self.primary_document}"

    @property
    def instance_xml_filename(self) -> str | None:
        lower = self.primary_document.lower()
        if lower.endswith((".htm", ".html")):
            stem = self.primary_document.rsplit(".", 1)[0]
            return f"{stem}_htm.xml"
        return None

    @property
    def instance_xml_url(self) -> str | None:
        name = self.instance_xml_filename
        return f"{self.base_url}/{name}" if name else None


def list_filings(
    submissions: dict,
    cik: int,
    *,
    forms: tuple[str, ...] = ("10-K", "20-F", "10-Q", "8-K"),
    limit: int = 10,
) -> list[FilingRef]:
    recent = (submissions or {}).get("filings", {}).get("recent", {})
    form_list = recent.get("form") or []
    acc_list = recent.get("accessionNumber") or []
    fdate_list = recent.get("filingDate") or []
    rdate_list = recent.get("reportDate") or []
    doc_list = recent.get("primaryDocument") or []
    out: list[FilingRef] = []
    for idx, form in enumerate(form_list):
        if form not in forms:
            continue
        acc = acc_list[idx] if idx < len(acc_list) else ""
        doc = doc_list[idx] if idx < len(doc_list) else ""
        if not acc or not doc:
            continue
        out.append(
            FilingRef(
                cik=int(cik),
                accession_number=str(acc),
                form=str(form),
                filing_date=str(fdate_list[idx]) if idx < len(fdate_list) else "",
                report_date=str(rdate_list[idx]) if idx < len(rdate_list) else "",
                primary_document=str(doc),
            )
        )
        if len(out) >= limit:
            break
    return out


def fetch_filing_text(
    url: str,
    cache_path: Path,
    *,
    timeout: int = 30,
) -> tuple[str, dict[str, Any]]:
    """Fetch and cache an immutable SEC filing artifact, returning ``(text, meta)``."""
    meta_path = cache_path.with_suffix(cache_path.suffix + ".meta.json")
    if cache_path.exists():
        text = cache_path.read_text(encoding="utf-8", errors="replace")
        if meta_path.exists():
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            meta["source_status"] = "OBSERVED_CACHED"
        else:
            meta = {
                "url": url,
                "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
                "retrieved_at": dt.datetime.fromtimestamp(cache_path.stat().st_mtime, dt.timezone.utc).isoformat(),
                "source_status": "OBSERVED_CACHED",
            }
        return text, meta

    from data_sources.sec_company import USER_AGENT

    request = Request(url, headers={"User-Agent": USER_AGENT, "Accept-Encoding": "identity"})
    with urlopen(request, timeout=timeout) as response:
        raw = response.read()
    text = raw.decode("utf-8", errors="replace")
    sha256 = hashlib.sha256(text.encode("utf-8")).hexdigest()
    retrieved_at = dt.datetime.now(dt.timezone.utc).isoformat()
    meta = {"url": url, "sha256": sha256, "retrieved_at": retrieved_at, "source_status": "OBSERVED_LIVE"}
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(text, encoding="utf-8")
    meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    return text, meta


class _FilingHTMLToTextParser(HTMLParser):
    """Convert SEC inline-XBRL HTML to clean text and pipe-delimited Markdown tables."""

    SKIP_TAGS = {"script", "style", "head", "ix:header", "ix:hidden"}
    BLOCK_TAGS = {"p", "div", "section", "article", "li", "h1", "h2", "h3", "h4", "h5", "h6", "br", "hr"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._skip_depth = 0
        self._in_table = 0
        self._in_cell = False
        self._current_row: list[str] = []
        self._current_cell: list[str] = []
        self._chunks: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        low = tag.lower()
        if low in self.SKIP_TAGS or low.startswith("ix:header") or low.startswith("ix:hidden"):
            self._skip_depth += 1
            return
        if self._skip_depth:
            return
        style = dict(attrs).get("style") or ""
        if "display:none" in style.replace(" ", "").lower():
            # Track hidden spans/divs with a sentinel only if paired; keep simple by not breaking nesting.
            pass
        if low == "table":
            self._in_table += 1
            self._chunks.append("\n")
        elif low == "tr" and self._in_table:
            self._current_row = []
        elif low in {"td", "th"} and self._in_table:
            self._in_cell = True
            self._current_cell = []
        elif low in self.BLOCK_TAGS and not self._in_cell:
            self._chunks.append("\n")

    def handle_endtag(self, tag: str) -> None:
        low = tag.lower()
        if low in self.SKIP_TAGS or low.startswith("ix:header") or low.startswith("ix:hidden"):
            if self._skip_depth > 0:
                self._skip_depth -= 1
            return
        if self._skip_depth:
            return
        if low in {"td", "th"} and self._in_table and self._in_cell:
            cell_text = re.sub(r"\s+", " ", "".join(self._current_cell)).strip()
            self._current_row.append(cell_text)
            self._in_cell = False
        elif low == "tr" and self._in_table:
            if any(cell for cell in self._current_row):
                # Merge currency symbols like "$" into adjacent numeric cells when split across columns.
                compact = [cell for cell in self._current_row if cell != ""]
                if compact:
                    self._chunks.append("| " + " | ".join(compact) + " |\n")
            self._current_row = []
        elif low == "table" and self._in_table:
            self._in_table -= 1
            self._chunks.append("\n")
        elif low in self.BLOCK_TAGS and not self._in_cell:
            self._chunks.append("\n")

    def handle_data(self, data: str) -> None:
        if self._skip_depth:
            return
        if self._in_cell:
            self._current_cell.append(data)
        else:
            self._chunks.append(data)

    def get_text(self) -> str:
        raw = html_lib.unescape("".join(self._chunks)).replace("\xa0", " ")
        lines = [re.sub(r"[ \t]+", " ", line).strip() for line in raw.splitlines()]
        out: list[str] = []
        blank = 0
        for line in lines:
            if not line:
                blank += 1
                if blank <= 1:
                    out.append("")
            else:
                blank = 0
                out.append(line)
        return "\n".join(out).strip()


def html_to_clean_text(html_content: str) -> str:
    parser = _FilingHTMLToTextParser()
    parser.feed(html_content)
    parser.close()
    return parser.get_text()


def _find_section_span(
    text: str,
    start_patterns: tuple[str, ...],
    end_patterns: tuple[str, ...],
    *,
    min_body_chars: int = 600,
    max_chars: int = 60000,
) -> str:
    """Locate a real filing section (skipping short Table-of-Contents matches)."""
    candidates: list[str] = []
    for start_pat in start_patterns:
        for match in re.finditer(start_pat, text, flags=re.IGNORECASE | re.MULTILINE):
            start_idx = match.end()
            # Skip TOC lines where the heading line ends with a page number or pipe table cell.
            line_end = text.find("\n", match.start())
            heading_line = text[match.start() : line_end if line_end != -1 else match.start() + 160]
            if heading_line.lstrip().startswith("|") and re.search(r"\|\s*\d+\s*\|?\s*$", heading_line):
                continue
            end_idx = len(text)
            search_window = text[start_idx : start_idx + max_chars * 2]
            for end_pat in end_patterns:
                end_match = re.search(end_pat, search_window, flags=re.IGNORECASE | re.MULTILINE)
                if end_match and end_match.start() >= min_body_chars:
                    end_idx = min(end_idx, start_idx + end_match.start())
            body = text[start_idx:min(end_idx, start_idx + max_chars)].strip()
            if len(body) >= min_body_chars:
                candidates.append(body)
    if not candidates:
        return ""
    # Prefer the first substantive match after any front-matter TOC.
    return candidates[0]


def extract_sections(html_or_text: str, *, form: str = "10-K") -> dict[str, str]:
    """Slice a filing into named sections (``item_1``, ``item_7``, ``segment_note``)."""
    text = html_to_clean_text(html_or_text) if "<" in html_or_text and ">" in html_or_text else html_or_text
    sections: dict[str, str] = {}
    upper_form = form.upper()
    if upper_form.startswith("20-F"):
        item4 = _find_section_span(
            text,
            (r"^\s*(?:\|\s*)?item\s+4(?:[\.\s:\-—]+)\s*information\s+on\s+the\s+company\b[^\n]*",),
            (r"^\s*(?:\|\s*)?item\s+4a[\.\s:\-—]*\b", r"^\s*(?:\|\s*)?item\s+5[\.\s:\-—]*\b"),
        )
        item5 = _find_section_span(
            text,
            (r"^\s*(?:\|\s*)?item\s+5(?:[\.\s:\-—]+)\s*operating\s+and\s+financial\s+review\b[^\n]*",),
            (r"^\s*(?:\|\s*)?item\s+6[\.\s:\-—]*\b",),
        )
        if item4:
            sections["item_1"] = item4
            sections["item_4"] = item4
        if item5:
            sections["item_7"] = item5
            sections["item_5"] = item5
    elif upper_form.startswith("10-Q"):
        mda = _find_section_span(
            text,
            (r"^\s*(?:\|\s*)?item\s+2(?:[\.\s:\-—]+)\s*management[’']?s\s+discussion\b[^\n]*",),
            (r"^\s*(?:\|\s*)?item\s+3[\.\s:\-—]*\b", r"^\s*(?:\|\s*)?item\s+4[\.\s:\-—]*\b"),
        )
        if mda:
            sections["item_7"] = mda
    else:
        item1 = _find_section_span(
            text,
            (r"^\s*(?:\|\s*)?item\s+1(?:[\.\s:\-—]+)\s*business\b[^\n]*",),
            (r"^\s*(?:\|\s*)?item\s+1a[\.\s:\-—]*\s*risk\s+factors\b", r"^\s*(?:\|\s*)?item\s+1b[\.\s:\-—]*\b", r"^\s*(?:\|\s*)?item\s+2(?:[\.\s:\-—]+)\s*properties\b"),
        )
        item7 = _find_section_span(
            text,
            (r"^\s*(?:\|\s*)?item\s+7(?:[\.\s:\-—]+)\s*management[’']?s\s+discussion\b[^\n]*",),
            (r"^\s*(?:\|\s*)?item\s+7a[\.\s:\-—]*\b", r"^\s*(?:\|\s*)?item\s+8[\.\s:\-—]*\b"),
        )
        if item1:
            sections["item_1"] = item1
        if item7:
            sections["item_7"] = item7

    seg_note = _find_section_span(
        text,
        (
            r"^\s*(?:note\s+\d+[\s.\-—:]*)?segment\s+(?:information|reporting|and\s+geographic\s+information)\b[^\n]*",
        ),
        (r"^\s*note\s+\d+\b", r"^\s*item\s+9\b"),
        min_body_chars=300,
        max_chars=30000,
    )
    if seg_note:
        sections["segment_note"] = seg_note
    sections["full_text"] = text
    return sections


def extract_business_description(html_or_text: str, *, form: str = "10-K", max_chars: int = 4000) -> str:
    """Return prose paragraphs from Item 1 (or 20-F Item 4) suitable for deterministic classification."""
    sections = extract_sections(html_or_text, form=form)
    raw = sections.get("item_1") or ""
    if not raw:
        return ""
    paragraphs = []
    for line in raw.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("|"):
            continue
        # Skip short boilerplate sub-headings until we collect prose sentences.
        if len(stripped) < 40 and "." not in stripped:
            continue
        paragraphs.append(stripped)
        if sum(len(p) for p in paragraphs) >= max_chars:
            break
    joined = " ".join(paragraphs).strip()
    return joined[:max_chars].rsplit(" ", 1)[0] if len(joined) > max_chars else joined


def _local_name(tag: str) -> str:
    if "}" in tag:
        return tag.split("}", 1)[1]
    if ":" in tag:
        return tag.split(":", 1)[1]
    return tag


def _humanize_member(member_qname: str) -> tuple[str, str]:
    raw = member_qname.split(":", 1)[-1]
    for suffix in ("SegmentMember", "OperatingSegmentMember", "Member"):
        if raw.endswith(suffix) and len(raw) > len(suffix):
            raw = raw[: -len(suffix)]
            break
    seg_id = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", raw).lower()
    seg_id = re.sub(r"[^a-z0-9]+", "_", seg_id).strip("_")
    words = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", raw)
    words = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1 \2", words)
    return seg_id, words.strip()


def _is_reconciling_member(member_qname: str) -> bool:
    low = member_qname.split(":", 1)[-1].lower()
    return any(token in low for token in RECONCILING_MEMBER_TOKENS)


def extract_xbrl_segments(instance_xml: str, *, target_period_end: str | None = None) -> list[dict[str, Any]]:
    """Parse reportable business-segment revenue and operating income from an XBRL instance XML."""
    try:
        root = ET.fromstring(instance_xml)
    except ET.ParseError:
        return []

    units: dict[str, str] = {}
    contexts: dict[str, dict[str, Any]] = {}
    for elem in root.iter():
        lname = _local_name(elem.tag)
        if lname == "unit" and elem.attrib.get("id"):
            measures = [_local_name(child.text.strip()) for child in elem.iter() if _local_name(child.tag) == "measure" and child.text]
            if len(measures) == 1:
                units[elem.attrib["id"]] = measures[0]
        elif lname == "context" and elem.attrib.get("id"):
            cid = elem.attrib["id"]
            start_date = end_date = None
            members: list[tuple[str, str]] = []
            has_typed = False
            for sub in elem.iter():
                sname = _local_name(sub.tag)
                if sname == "startDate" and sub.text:
                    start_date = sub.text.strip()
                elif sname == "endDate" and sub.text:
                    end_date = sub.text.strip()
                elif sname == "explicitMember" and sub.text:
                    dim = _local_name(sub.attrib.get("dimension", ""))
                    members.append((dim, sub.text.strip()))
                elif sname == "typedMember":
                    has_typed = True
            # ASC 280 / ASU 2023-07 filers often pair StatementBusinessSegmentsAxis with
            # ConsolidationItemsAxis=OperatingSegmentsMember; keep only that qualifier and
            # reject sub-breakdowns or elimination members.
            filtered_members = [
                (d, m)
                for (d, m) in members
                if not (d == "ConsolidationItemsAxis" and m.split(":", 1)[-1] == "OperatingSegmentsMember")
            ]
            if has_typed or len(filtered_members) != 1 or not start_date or not end_date:
                continue
            dim, member = filtered_members[0]
            if dim not in SEGMENT_AXES or _is_reconciling_member(member):
                continue
            try:
                days = (dt.date.fromisoformat(end_date) - dt.date.fromisoformat(start_date)).days
            except ValueError:
                continue
            if not (330 <= days <= 380):
                continue
            contexts[cid] = {"start": start_date, "end": end_date, "axis": dim, "member": member}

    if not contexts:
        return []

    rev_rank = {name: idx for idx, name in enumerate(SEGMENT_REVENUE_CONCEPTS)}
    op_rank = {name: idx for idx, name in enumerate(SEGMENT_OPERATING_INCOME_CONCEPTS)}
    # (member, end) -> best (priority, value, concept, unit, start)
    rev_facts: dict[tuple[str, str], tuple[int, float, str, str | None, str]] = {}
    op_facts: dict[tuple[str, str], tuple[int, float, str, str | None, str]] = {}

    for elem in root:
        ctx_id = elem.attrib.get("contextRef")
        if not ctx_id or ctx_id not in contexts:
            continue
        if elem.attrib.get("{http://www.w3.org/2001/XMLSchema-instance}nil") == "true":
            continue
        raw_text = (elem.text or "").strip()
        if not raw_text:
            continue
        try:
            value = float(raw_text)
        except ValueError:
            continue
        concept = _local_name(elem.tag)
        unit = units.get(elem.attrib.get("unitRef", ""))
        if unit in {"shares", "pure"}:
            continue
        ctx = contexts[ctx_id]
        key = (ctx["member"], ctx["end"])
        if concept in rev_rank:
            prio = rev_rank[concept]
            if key not in rev_facts or prio < rev_facts[key][0]:
                rev_facts[key] = (prio, value, concept, unit, ctx["start"])
        elif concept in op_rank:
            prio = op_rank[concept]
            if key not in op_facts or prio < op_facts[key][0]:
                op_facts[key] = (prio, value, concept, unit, ctx["start"])

    if not rev_facts:
        return []

    available_ends = sorted({end for (_, end) in rev_facts}, reverse=True)
    chosen_end = target_period_end if target_period_end in available_ends else available_ends[0]
    prior_ends = [end for end in available_ends if end < chosen_end]
    prior_end = prior_ends[0] if prior_ends else None

    members = sorted({member for (member, end) in rev_facts if end == chosen_end})
    segments: list[dict[str, Any]] = []
    for member in members:
        _, rev_val, rev_concept, unit, start_date = rev_facts[(member, chosen_end)]
        prior_rev = rev_facts.get((member, prior_end))[1] if prior_end and (member, prior_end) in rev_facts else None
        rev_growth = (rev_val / prior_rev - 1) if (prior_rev is not None and prior_rev > 0) else None
        op_tuple = op_facts.get((member, chosen_end))
        op_val = op_tuple[1] if op_tuple else None
        op_concept = op_tuple[2] if op_tuple else None
        op_margin = (op_val / rev_val) if (op_val is not None and rev_val > 0) else None
        seg_id, seg_name = _humanize_member(member)
        segments.append(
            {
                "segment_id": seg_id,
                "segment_name": seg_name,
                "xbrl_member": member,
                "period_start": start_date,
                "period_end": chosen_end,
                "prior_period_end": prior_end,
                "currency": unit,
                "revenue": rev_val,
                "prior_revenue": prior_rev,
                "revenue_growth": rev_growth,
                "revenue_concept": rev_concept,
                "operating_income": op_val,
                "operating_margin": op_margin,
                "operating_income_concept": op_concept,
            }
        )
    segments.sort(key=lambda item: item["revenue"], reverse=True)
    return segments


def enrich_sec_filing_metadata(
    data: dict[str, Any],
    submissions: dict[str, Any],
    cik: int,
    *,
    fetcher: Callable[[str, Path], tuple[str, dict[str, Any]]] | None = None,
    cache_dir: Path = CACHE_DIR,
) -> dict[str, Any]:
    """Populate Item 1 ``longBusinessSummary`` and XBRL ``segments`` from the latest annual filing."""
    if fetcher is None and os.environ.get("CHAINSTOX_FETCH_SEC_FILINGS", "1") == "0":
        return data
    fetch = fetcher or fetch_filing_text
    annual = list_filings(submissions, cik, forms=("10-K", "20-F"), limit=1)
    if not annual:
        return data
    ref = annual[0]
    filing_dir = cache_dir / ref.cik_key / ref.accession_nodash
    envelopes = dict(data.get("evidence_envelopes") or {})

    # 1. Business description from primary HTML filing (Item 1 / 20-F Item 4).
    info = data.setdefault("info", {})
    if not info.get("longBusinessSummary"):
        try:
            html_text, html_meta = fetch(ref.url, filing_dir / ref.primary_document)
            summary = extract_business_description(html_text, form=ref.form)
            if summary:
                info["longBusinessSummary"] = summary
                envelopes["business_description"] = {
                    "source_id": f"sec-filing:{ref.cik_key}:{ref.accession_number}:item1",
                    "source_name": f"SEC {ref.form} ({ref.filing_date})",
                    "source_url": ref.url,
                    "source_type": "regulatory_filing_prose",
                    "provider_status": "OK",
                    "retrieved_at": html_meta.get("retrieved_at"),
                    "observation_date": ref.report_date or ref.filing_date,
                    "fiscal_period_end": ref.report_date or None,
                    "filing_date": ref.filing_date,
                    "unit": "text",
                    "value": summary,
                    "normalized_concept": "business_description",
                    "transformation": f"Deterministic {ref.form} Item 1/4 prose slice (<=4000 chars)",
                    "coverage_status": "COMPLETE",
                    "validation_status": "VALID",
                    "staleness_status": "HISTORICAL",
                    "entity_identifier": ref.cik_key,
                    "source_status": html_meta.get("source_status", "HISTORICAL_REPORTED"),
                    "source_locator": "Item 4" if ref.form.startswith("20-F") else "Item 1. Business",
                    "extraction_method": f"deterministic_sec_section_parser:sha256:{html_meta.get('sha256', '')[:12]}",
                }
        except (HTTPError, URLError, TimeoutError, OSError):
            pass

    # 2. Reportable business segments from extracted XBRL instance XML.
    if not data.get("segments") and ref.instance_xml_url and ref.instance_xml_filename:
        try:
            xml_text, xml_meta = fetch(ref.instance_xml_url, filing_dir / ref.instance_xml_filename)
            target_end = (data.get("periods") or {}).get("revenue")
            segments = extract_xbrl_segments(
                xml_text,
                target_period_end=target_end if target_end and target_end != "Unavailable" else None,
            )
            if segments:
                for seg in segments:
                    seg["accession_number"] = ref.accession_number
                    seg["filing_date"] = ref.filing_date
                    seg["form"] = ref.form
                    seg["source_url"] = ref.instance_xml_url
                    seg["sha256"] = xml_meta.get("sha256")
                data["segments"] = segments
        except (HTTPError, URLError, TimeoutError, OSError):
            pass

    data["evidence_envelopes"] = envelopes
    data["latest_annual_filing"] = asdict(ref)
    return data
