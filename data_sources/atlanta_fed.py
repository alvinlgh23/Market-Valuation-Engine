"""Official Atlanta Fed Wage Growth Tracker XLSX adapter using only stdlib."""

from datetime import datetime, timedelta
import re
import xml.etree.ElementTree as ET
import zipfile
import io


NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"


def _column(ref):
    letters = re.match(r"[A-Z]+", ref).group(0)
    value = 0
    for letter in letters:
        value = value * 26 + ord(letter) - 64
    return value - 1


def parse_wage_growth_xlsx(payload):
    with zipfile.ZipFile(io.BytesIO(payload)) as workbook:
        shared = []
        if "xl/sharedStrings.xml" in workbook.namelist():
            root = ET.fromstring(workbook.read("xl/sharedStrings.xml"))
            shared = ["".join(node.text or "" for node in item.iter(NS + "t")) for item in root]
        sheet = ET.fromstring(workbook.read("xl/worksheets/sheet1.xml"))
        rows = []
        for row in sheet.findall(".//" + NS + "row"):
            cells = {}
            for cell in row.findall(NS + "c"):
                value_node = cell.find(NS + "v")
                if value_node is None:
                    continue
                value = value_node.text
                if cell.attrib.get("t") == "s":
                    value = shared[int(value)]
                cells[_column(cell.attrib["r"])] = value
            if 0 not in cells or 1 not in cells or cells[1] in {"", ".", None}:
                continue
            try:
                date = datetime(1899, 12, 30) + timedelta(days=float(cells[0]))
                rows.append((date.strftime("%Y-%m-%d"), float(cells[1])))
            except (TypeError, ValueError):
                continue
        if not rows:
            raise ValueError("No Overall wage-growth observations found in data_overall")
        rows.sort()
        return rows, {"series": "Overall", "moving_average": "3-month", "weighting": "Unweighted"}
