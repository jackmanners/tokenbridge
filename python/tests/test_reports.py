import pytest

from tokenbridge.reports import generate_report


def test_generate_report_injects_data_and_label():
    html = generate_report(
        "P001",
        {"withings-summary": [{"startdate": 1700000000, "total_sleep_time": 25200}]},
        template="full",
    )
    assert "<!-- __SLEEP_DATA__ -->" not in html
    assert "window.SLEEP_DATA" in html
    assert "P001" in html
    assert "data:text/csv" in html


def test_generate_report_skips_empty_data_keys():
    html = generate_report("P001", {"withings-summary": [], "withings-bp": []}, template="full")
    assert '"data": {}' in html


def test_generate_report_respects_column_hints():
    html = generate_report(
        "P001",
        {"withings-bp": [{"date": 1, "systolic": 118, "diastolic": 76}]},
        template="bp",
        column_hints={"withings-bp": ["date", "diastolic", "systolic"]},
    )
    assert "window.SLEEP_DATA" in html


def test_generate_report_unknown_template_raises():
    with pytest.raises(FileNotFoundError):
        generate_report("P001", {"x": [{"a": 1}]}, template="does-not-exist")


def test_generate_report_missing_placeholder_raises(tmp_path):
    bad = tmp_path / "bad.html"
    bad.write_text("<html>no placeholder here</html>", encoding="utf-8")
    with pytest.raises(ValueError):
        generate_report("P001", {"x": [{"a": 1}]}, template="bad", templates_dir=tmp_path)
