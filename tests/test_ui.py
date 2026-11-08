"""Integration smoke checks for all six Streamlit modules using AppTest."""
import pytest
from streamlit.testing.v1 import AppTest


@pytest.mark.parametrize("page", [
    "Dashboard", "Banking FAQ Playground", "Evaluation Studio",
    "Regression Testing", "Safety Lab", "Reports & History",
])
def test_six_modules_render(page):
    at = AppTest.from_file("app.py", default_timeout=30).run()
    assert not at.exception
    at.radio[0].set_value(page).run()
    assert not at.exception


def test_full_evaluation_from_interface():
    at = AppTest.from_file("app.py", default_timeout=30).run()
    at.radio[0].set_value("Evaluation Studio").run()
    assert not at.exception
    assert any(b.label == "Run Full Evaluation" for b in at.button)
    next(b for b in at.button if b.label == "Run Full Evaluation").click().run()
    assert not at.exception
    assert at.session_state["latest"]["metrics"]["n"] == 100


def test_safety_single_case_from_interface():
    at = AppTest.from_file("app.py", default_timeout=30).run()
    at.radio[0].set_value("Safety Lab").run()
    assert not at.exception
    next(b for b in at.button if b.label == "Run Selected Safety Case").click().run()
    assert not at.exception
    assert at.session_state["safety"]["metrics"]["n"] == 1
