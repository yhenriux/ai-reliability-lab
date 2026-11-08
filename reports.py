"""Safe, portable exports for synthetic model evaluation reports."""
import csv
import io
import json


def _safe_cell(value):
    if value is None:
        return ""
    if isinstance(value, (list, dict)):
        value = json.dumps(value, ensure_ascii=False)
    value = str(value)
    # Spreadsheet applications can interpret leading =,+,-,@ as formulas.
    if value.lstrip(" \t\r\n").startswith(("=", "+", "-", "@")):
        return "'" + value
    return value


def export_cases_csv(rows):
    if not rows:
        return ""
    fields = list(dict.fromkeys(key for row in rows for key in row))
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=fields)
    writer.writeheader()
    for row in rows:
        writer.writerow({key: _safe_cell(row.get(key)) for key in fields})
    return stream.getvalue()
