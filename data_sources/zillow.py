"""Official Zillow Research ZORI adapter."""

import csv
import io


def parse_zori_csv(payload):
    text = payload.decode("utf-8-sig") if isinstance(payload, bytes) else payload
    reader = csv.DictReader(io.StringIO(text))
    for row in reader:
        if row.get("RegionName", "").strip().lower() == "united states":
            observations = []
            for column, value in row.items():
                if not column or len(column) != 10 or column[4] != "-" or not value:
                    continue
                try:
                    observations.append((column, float(value)))
                except ValueError:
                    continue
            observations.sort()
            if not observations:
                raise ValueError("United States row contained no valid date columns")
            return observations, {
                "geography": "United States",
                "property_type": "All Homes Plus Multifamily",
                "seasonal_adjustment": "Smoothed, not seasonally adjusted",
            }
    raise ValueError("United States row not found in Zillow ZORI CSV")
