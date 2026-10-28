# Reports (Python)

The Python package can render self-contained HTML reports from data you've already fetched - sleep summaries, blood pressure over time, or combined views. Rendering happens locally, in-process - no server round-trip, since the data is already in memory.

This is Python-only; R and JS/TS don't have it.

---

## Generating a report

```python
from tokenbridge import TokenBridge
from tokenbridge.reports import generate_report

tb = TokenBridge()
token = tb.get_token("p001", provider="withings")

sleep = tb.fetch("p001", "sleep-summary",  "2024-01-01", "2024-06-30", provider="withings", token=token)
bp    = tb.fetch("p001", "blood-pressure", "2024-01-01", "2024-06-30", provider="withings", token=token)

html = generate_report("P001", {"withings-summary": sleep, "withings-bp": bp}, template="sleep-bp")
open("report_p001.html", "w", encoding="utf-8").write(html)
```

### `generate_report(label, data, template="full", *, column_hints=None, templates_dir=None)`

| Argument | Description |
|---|---|
| `label` | Shown in the report header - typically a participant ID |
| `data` | Named arrays of flat records - one key per data source. Empty arrays are skipped |
| `template` | Template name (see below). Defaults to `"full"` |
| `column_hints` | Optional CSV column order per data key, e.g. `{"withings-bp": ["date", "systolic", "diastolic"]}`. Falls back to the first record's key order |
| `templates_dir` | Directory to look for `{template}.html` in. Defaults to this package's bundled templates - pass your own to use a custom one |

Returns the rendered HTML as a string - write it to a file, attach it to an email, or stream it to a browser.

### Available templates

| Template | Data keys required | Description |
|---|---|---|
| `full` | `withings-summary` | Sleep summary only |
| `sleep-bp` | `withings-summary`, `withings-bp` | Sleep + blood pressure, synced charts |
| `bp` | `withings-bp` | Blood pressure only |

### Data shapes

**`withings-summary`** - one object per sleep session:

```json
{
  "startdate":            1700000000,
  "enddate":              1700030000,
  "timezone":             "Australia/Adelaide",
  "total_sleep_time":     25200,
  "sleep_efficiency":     0.91,
  "apnea_hypopnea_index": 3.2,
  "hr_average":           58
}
```

All Withings Sleep Summary Series fields are accepted. `startdate`/`enddate` are Unix epoch seconds.

**`withings-bp`** - one object per Withings measurement group:

```json
{
  "date":        1700000000,
  "systolic":    118,
  "diastolic":   76,
  "heart_pulse": 64
}
```

`heart_pulse` is optional. `date` is the Unix epoch timestamp of the measurement.

---

## Writing a custom template

Templates are self-contained HTML files with a `<!-- __SLEEP_DATA__ -->` placeholder that `generate_report()` replaces with a `<script>` block.

### Placeholder

Place this somewhere in `<head>`:

```html
<!-- __SLEEP_DATA__ -->
```

`generate_report()` injects:

```html
<script>
window.SLEEP_DATA = {
  "label": "P001",
  "reportTimestamp": "2024-01-15 09:30:00",
  "data": {
    "withings-summary": {
      "records":    [ ... ],
      "csvDataUri": "data:text/csv;charset=utf-8;base64,..."
    }
  }
};
</script>
```

### Accessing data in your template

```js
const records = window.SLEEP_DATA.data['withings-summary']?.records ?? [];
const csvLink = window.SLEEP_DATA.data['withings-summary']?.csvDataUri;
const label   = window.SLEEP_DATA.label;
const ts      = window.SLEEP_DATA.reportTimestamp;
```

### Using a custom template

```python
from pathlib import Path
html = generate_report("P001", data, template="my-template", templates_dir=Path("my_templates"))
```

`templates_dir` should contain a file named `{template}.html`.

### Bundled template source files

The default templates ship inside the package at `python/tokenbridge/templates/`:

| File | Template name | Description |
|---|---|---|
| `full.html` | `full` | Sleep summary |
| `sleep-bp.html` | `sleep-bp` | Sleep + blood pressure |
| `bp.html` | `bp` | Blood pressure only |
