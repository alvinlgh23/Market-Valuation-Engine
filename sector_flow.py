"""Sector money-flow measurements (checklist P5).

Relative strength says where prices went; these measures say whether participation and
money backed it. All are stored in the signal history (family "flow") so the card can use
percentiles in each series' own history.

Per sector ETF and trading day:
    flow.<ETF>.breadth_50          share of its listed top holdings above their 50-day average
    flow.<ETF>.breadth_200         same, 200-day average
    flow.<ETF>.dollar_volume_20d   ETF 20-day average of close x volume (USD)
    flow.<ETF>.updown_volume_20d   ETF volume on up days / volume on down days, last 20 days
    flow.<ETF>.shares_outstanding  ETF shares outstanding snapshot (LIVE only; Yahoo has no history)

"Top holdings" are the ~10 names per ETF in Valuation_model.SECTOR_CANDIDATES, not the full
constituent list, so breadth is labelled as top-holdings breadth.

Crowding state (checklist 5.5), from percentiles in own history:
    CROWDED     breadth_50 >= 0.8 and dollar-volume percentile >= 0.8 and 3M RS percentile >= 0.67
    EXTENDED    two of those three conditions
    UNLOVED     breadth_50 <= 0.2 and 3M RS percentile <= 0.33
    NEUTRAL     otherwise
    None        any input missing or fewer than 60 stored observations

Run:  python sector_flow.py backfill --years 2     (downloads ~3y of OHLCV for ~330 tickers)
      python sector_flow.py snapshot               (records today's ETF shares outstanding)
"""

from __future__ import annotations

import argparse
import contextlib
import io
import sys
from typing import Any

from signal_history import SignalStore, observation

SOURCE = "Yahoo daily OHLCV (flow backfill)"


def download_ohlcv(tickers: list[str], period: str = "3y") -> dict[str, Any]:
    import yfinance as yf

    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        raw = yf.download(sorted(set(tickers)), period=period, auto_adjust=True, progress=False, group_by="ticker", threads=True)
    frames = {}
    for ticker in sorted(set(tickers)):
        try:
            frame = raw[ticker][["Close", "Volume"]].dropna(subset=["Close"])
        except KeyError:
            continue
        if len(frame):
            frame.index = frame.index.tz_localize(None) if getattr(frame.index, "tz", None) else frame.index
            frames[ticker] = frame
    return frames


def prepare(frames: dict[str, Any]) -> dict[str, Any]:
    """Precompute rolling series once so each date is a lookup."""
    prepared = {}
    for ticker, frame in frames.items():
        close, volume = frame["Close"], frame["Volume"].fillna(0)
        up = close.diff() > 0
        down = close.diff() < 0
        up_volume = volume.where(up, 0).rolling(20).sum()
        down_volume = volume.where(down, 0).rolling(20).sum()
        prepared[ticker] = {
            "close": close,
            "above_50": (close > close.rolling(50).mean()).where(close.rolling(50).count() >= 50),
            "above_200": (close > close.rolling(200).mean()).where(close.rolling(200).count() >= 200),
            "dollar_volume_20d": (close * volume).rolling(20).mean(),
            "updown_volume_20d": (up_volume / down_volume).where(down_volume > 0),
        }
    return prepared


def _at(series, day):
    try:
        value = series.loc[:day].iloc[-1]
    except (IndexError, KeyError):
        return None
    if value is None or value != value:
        return None
    return float(value)


def metrics_at(etf: str, day, prepared: dict[str, Any], members: list[str]) -> dict[str, float | None]:
    def breadth(key):
        flags = [_at(prepared[member][key], day) for member in members if member in prepared and member != etf]
        flags = [flag for flag in flags if flag is not None]
        return sum(flags) / len(flags) if len(flags) >= 5 else None  # fewer than five names is not breadth
    own = prepared.get(etf)
    return {
        "breadth_50": breadth("above_50"),
        "breadth_200": breadth("above_200"),
        "dollar_volume_20d": None if own is None else _at(own["dollar_volume_20d"], day),
        "updown_volume_20d": None if own is None else _at(own["updown_volume_20d"], day),
    }


def backfill(years: float = 2.0, store: SignalStore | None = None, frames: dict[str, Any] | None = None) -> dict[str, Any]:
    import Valuation_model as vm
    import pandas as pd

    store = store or SignalStore()
    universe = {etf: [member for member in vm.SECTOR_CANDIDATES.get(etf, []) if member != etf] for etf in vm.SECTOR_ETFS}
    if frames is None:
        frames = download_ohlcv(list(universe) + [member for members in universe.values() for member in members] + ["SPY"])
    prepared = prepare(frames)
    if "SPY" not in prepared:
        return {"state": "FAILED", "error": "SPY unavailable; no trading calendar.", "written": 0}
    calendar = prepared["SPY"]["close"].index
    start = calendar[-1] - pd.Timedelta(days=int(365 * years))
    written = 0
    for day in [item for item in calendar if item >= start]:
        batch = []
        for etf, members in universe.items():
            if etf not in prepared:
                continue
            for key, value in metrics_at(etf, day, prepared, members).items():
                batch.append(observation(f"flow.{etf}.{key}", day, value, source=SOURCE, source_state="BACKFILL"))
        written += store.append(batch)
    missing_members = sorted({member for members in universe.values() for member in members} - set(frames))
    return {"state": "COMPLETED", "written": written, "first": str(start.date()), "last": str(calendar[-1].date()),
            "etfs": sum(etf in prepared for etf in universe), "tickers_downloaded": len(frames), "missing_tickers": missing_members}


def record_shares_snapshot(etfs: list[str] | None = None, store: SignalStore | None = None) -> dict[str, Any]:
    """Shares outstanding has no Yahoo history, so the series starts with these LIVE snapshots."""
    import datetime as dt
    import Valuation_model as vm
    import yfinance as yf

    store = store or SignalStore()
    today = dt.date.today().isoformat()
    batch, failures = [], {}
    for etf in etfs or list(vm.SECTOR_ETFS):
        try:
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                shares = yf.Ticker(etf).info.get("sharesOutstanding")
        except Exception as exc:  # noqa: BLE001
            failures[etf] = f"{type(exc).__name__}: {exc}"
            continue
        if shares is None:
            failures[etf] = "Yahoo returned no sharesOutstanding"
            continue
        batch.append(observation(f"flow.{etf}.shares_outstanding", today, shares, source="Yahoo Finance quote summary", source_state="LIVE"))
    return {"written": store.append(batch), "failures": failures, "date": today}


def rs_persistence(store: SignalStore, etf: str, as_of: str | None = None, window: int = 63) -> float | None:
    """Share of the last `window` stored observations with positive 3M relative strength (checklist 5.4)."""
    points = store.series(f"sector.{etf}.rel_3m", as_of)[-window:]
    return sum(value > 0 for _, value in points) / len(points) if len(points) >= window else None


def crowding_state(breadth_50: float | None, dollar_volume_pct: float | None, rs_pct: float | None) -> str | None:
    if breadth_50 is None or dollar_volume_pct is None or rs_pct is None:
        return None
    hot = [breadth_50 >= 0.8, dollar_volume_pct >= 0.8, rs_pct >= 0.67]
    if all(hot):
        return "CROWDED"
    if sum(hot) == 2:
        return "EXTENDED"
    if breadth_50 <= 0.2 and rs_pct <= 0.33:
        return "UNLOVED"
    return "NEUTRAL"


CROWDING_WORDS = {"CROWDED": "Crowded", "EXTENDED": "Extended", "UNLOVED": "Unloved", "NEUTRAL": "Neutral", None: "Unavailable"}


def latest_sector_flow(store: SignalStore, etf: str) -> dict[str, Any]:
    """Everything the card and the Markets page need for one ETF, with dates and percentiles."""
    def last(key):
        row = store.latest(f"flow.{etf}.{key}")
        return (row["observation_date"], row["value"]) if row and row["value"] is not None else (None, None)
    day, breadth_50 = last("breadth_50")
    _, breadth_200 = last("breadth_200")
    volume_day, dollar_volume = last("dollar_volume_20d")
    _, updown = last("updown_volume_20d")
    dollar_volume_pct = store.percentile(f"flow.{etf}.dollar_volume_20d", value=dollar_volume, as_of=volume_day) if dollar_volume is not None else None
    rs = store.latest(f"sector.{etf}.rel_3m")
    rs_pct = store.percentile(f"sector.{etf}.rel_3m", value=rs["value"], as_of=rs["observation_date"]) if rs and rs["value"] is not None else None
    shares = store.series(f"flow.{etf}.shares_outstanding")
    shares_change = None
    if len(shares) >= 2 and shares[0][1]:
        shares_change = {"from": shares[0][0], "to": shares[-1][0], "change": shares[-1][1] / shares[0][1] - 1}
    state = crowding_state(breadth_50, dollar_volume_pct, rs_pct)
    return {
        "etf": etf, "as_of": day, "breadth_50": breadth_50, "breadth_200": breadth_200,
        "dollar_volume_20d": dollar_volume, "dollar_volume_percentile": dollar_volume_pct, "updown_volume_20d": updown,
        "rs_3m_percentile": rs_pct, "rs_persistence_63": rs_persistence(store, etf), "crowding_state": state,
        "crowding": CROWDING_WORDS[state], "shares_outstanding_change": shares_change,
        "breadth_basis": "top holdings listed in the sector engine (about 10 names), not the full constituent list",
    }


def all_sector_flow(store: SignalStore | None = None) -> dict[str, dict[str, Any]]:
    import Valuation_model as vm
    store = store or SignalStore()
    return {etf: latest_sector_flow(store, etf) for etf in vm.SECTOR_ETFS}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="CHAINSTOX sector money-flow measurements")
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("backfill")
    run.add_argument("--years", type=float, default=2.0)
    sub.add_parser("snapshot")
    show = sub.add_parser("show")
    show.add_argument("etf")
    args = parser.parse_args(argv)
    if args.command == "backfill":
        result = backfill(args.years)
        print({key: value for key, value in result.items() if key != "missing_tickers"})
        if result.get("missing_tickers"):
            print("  no Yahoo data:", ", ".join(result["missing_tickers"]))
        return 0 if result["state"] == "COMPLETED" else 1
    if args.command == "snapshot":
        print(record_shares_snapshot())
        return 0
    print(latest_sector_flow(SignalStore(), args.etf.upper()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
