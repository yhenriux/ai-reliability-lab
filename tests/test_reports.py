"""CSV export must preserve data and prevent spreadsheet formula execution."""
import csv
import io

from reports import export_cases_csv


def test_csv_export_neutralizes_formula_cells():
    text = export_cases_csv([
        {"case_id": "C-001", "answer": "=HYPERLINK(\"https://example.org\",\"click\")", "passed": False},
        {"case_id": "C-002", "answer": "  @SUM(1,1)", "passed": True},
        {"case_id": "C-003", "answer": "Texto seguro", "passed": True},
    ])
    rows = list(csv.DictReader(io.StringIO(text)))
    assert rows[0]["answer"].startswith("'=")
    assert rows[1]["answer"].startswith("'  @")
    assert rows[2]["answer"] == "Texto seguro"
    assert len(rows) == 3


def test_csv_export_preserves_unicode_and_lists():
    text = export_cases_csv([{"answer": "Não encontrei", "citations": ["POL-001"]}])
    row = next(csv.DictReader(io.StringIO(text)))
    assert row["answer"] == "Não encontrei"
    assert row["citations"] == '["POL-001"]'
