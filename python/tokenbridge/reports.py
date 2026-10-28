"""Self-contained HTML report generation.

Renders a stored template with participant data into a single HTML file -
no server round-trip, since the data is already in memory after a `fetch()`
call. Templates are plain HTML files shipped with this package (or your own,
via `templates_dir=`) with a `<!-- __SLEEP_DATA__ -->` placeholder that gets
replaced with a `<script>` block setting `window.SLEEP_DATA`.

    from tokenbridge import TokenBridge
    from tokenbridge.reports import generate_report

    tb = TokenBridge()
    token = tb.get_token("p001", provider="withings")
    sleep = tb.fetch("p001", "sleep-summary", start, end, provider="withings", token=token)
    bp    = tb.fetch("p001", "blood-pressure", start, end, provider="withings", token=token)

    html = generate_report("P001", {"withings-summary": sleep, "withings-bp": bp}, template="sleep-bp")
    open("report.html", "w", encoding="utf-8").write(html)
"""

import base64
import csv
import io
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

_TEMPLATE_DIR = Path(__file__).parent / "templates"
_PLACEHOLDER = "<!-- __SLEEP_DATA__ -->"


def _csv_cell(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        return json.dumps(value)
    return str(value)


def _to_csv_data_uri(records: list[dict], columns: list[str]) -> str:
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(columns)
    for record in records:
        writer.writerow([_csv_cell(record.get(c)) for c in columns])
    csv_bytes = buf.getvalue().encode("utf-8")
    return f"data:text/csv;charset=utf-8;base64,{base64.b64encode(csv_bytes).decode()}"


def generate_report(
    label: str,
    data: dict[str, list[dict]],
    template: str = "full",
    *,
    column_hints: Optional[dict[str, list[str]]] = None,
    templates_dir: Optional[Path] = None,
) -> str:
    """Render a report template with participant data.

    Args:
        label: Shown in the report header - typically a participant ID.
        data: Named arrays of flat records, e.g.
            `{"withings-summary": [...], "withings-bp": [...]}`. Empty
            arrays are skipped.
        template: Template name - a `.html` file in `templates_dir`
            (default: this package's bundled templates: `"full"`,
            `"sleep-bp"`, `"bp"`).
        column_hints: Optional CSV column order per data key, e.g.
            `{"withings-bp": ["date", "systolic", "diastolic"]}`. Falls
            back to the first record's key order when not given.
        templates_dir: Directory to look for `{template}.html` in.
            Defaults to this package's bundled templates - pass your own
            directory to use a custom template.

    Returns:
        The rendered HTML as a string.

    Raises:
        FileNotFoundError: If the template file doesn't exist.
        ValueError: If the template is missing the `<!-- __SLEEP_DATA__ -->`
            placeholder.
    """
    html_path = (templates_dir or _TEMPLATE_DIR) / f"{template}.html"
    if not html_path.exists():
        raise FileNotFoundError(f"template {template!r} not found at {html_path}")
    html = html_path.read_text(encoding="utf-8")

    if _PLACEHOLDER not in html:
        raise ValueError(f"template {template!r} is missing the {_PLACEHOLDER} placeholder")

    column_hints = column_hints or {}
    injected = {}
    for key, records in data.items():
        if not records:
            continue
        columns = column_hints.get(key) or list(records[0].keys())
        injected[key] = {"records": records, "csvDataUri": _to_csv_data_uri(records, columns)}

    report_timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    payload = {"label": label, "reportTimestamp": report_timestamp, "data": injected}
    script = f"<script>\nwindow.SLEEP_DATA = {json.dumps(payload)};\n</script>"

    return html.replace(_PLACEHOLDER, script, 1)
