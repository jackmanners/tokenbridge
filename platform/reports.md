# Reports

TokenBridge can generate self-contained HTML reports from health data. Reports are rendered server-side from stored templates and returned as a single HTML file you can open in a browser or attach to an email.

---

## Generating a report

Send a `POST` to `/sleep-report` with your data:

```bash
curl -X POST https://<ref>.supabase.co/functions/v1/sleep-report \
  -H "Authorization: Bearer $TOKENBRIDGE_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "label":    "P001",
    "template": "sleep-bp",
    "data": {
      "withings-summary": [ { "startdate": 1700000000, "enddate": 1700030000, ... } ],
      "withings-bp":      [ { "date": 1700000000, "systolic": 118, "diastolic": 76 } ]
    }
  }' \
  --output report.html
```

The response is `text/html` — write it to a file or stream it directly to a browser.

### Request fields

| Field | Type | Description |
|---|---|---|
| `label` | string | Shown in the report header — typically a participant ID |
| `template` | string | Template name (see below). Defaults to `"full"` |
| `data` | object | Named arrays of flat records — one key per data source |

### Available templates

| Template | Data keys required | Description |
|---|---|---|
| `full` | `withings-summary` | Sleep summary only |
| `sleep-bp` | `withings-summary`, `withings-bp` | Sleep + blood pressure, synced charts |
| `bp` | `withings-bp` | Blood pressure only |

### Data shapes

**`withings-summary`** — one object per sleep session:

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

**`withings-bp`** — one object per Withings measurement group:

```json
{
  "date":        1700000000,
  "systolic":    118,
  "diastolic":   76,
  "heart_pulse": 64
}
```

`heart_pulse` is optional. `date` is the Unix epoch timestamp of the measurement.

### Generating from the Python client

```python
import json, requests
from tokenbridge import TokenBridge
from tokenbridge.providers.withings import _fetch_all

tb = TokenBridge()
token = tb.get_token("p001", provider="withings")

sleep = _fetch_all(token, "sleep-summary",  "2024-01-01", "2024-06-30")
bp    = _fetch_all(token, "blood-pressure", "2024-01-01", "2024-06-30")

resp = requests.post(
    f"{tb.url}/sleep-report",
    headers={"Authorization": f"Bearer {tb.api_key}"},
    json={"label": "P001", "template": "sleep-bp", "data": {
        "withings-summary": sleep,
        "withings-bp":      bp,
    }},
)
open("report_p001.html", "wb").write(resp.content)
```

---

## Managing templates

Templates are stored in the `report_templates` Postgres table and managed via the `template-manager` edge function.

### List all templates

```bash
curl https://<ref>.supabase.co/functions/v1/template-manager \
  -H "Authorization: Bearer $TOKENBRIDGE_API_KEY"
```

### Get a template (with HTML)

```bash
curl "https://<ref>.supabase.co/functions/v1/template-manager?name=full" \
  -H "Authorization: Bearer $TOKENBRIDGE_API_KEY"
```

### Upload or update a template

```bash
python3 -c "
import json
html = open('supabase/templates/sleep-bp.html').read()
print(json.dumps({
  'name': 'sleep-bp',
  'description': 'Sleep + blood pressure combined report',
  'metadata': {
    'columnHints': {
      'withings-summary': ['startdate','enddate','timezone','total_sleep_time','sleep_efficiency','apnea_hypopnea_index'],
      'withings-bp':      ['date','systolic','diastolic','heart_pulse']
    }
  },
  'html': html
}))
" | curl -X POST https://<ref>.supabase.co/functions/v1/template-manager \
  -H "Authorization: Bearer $TOKENBRIDGE_API_KEY" \
  -H "Content-Type: application/json" \
  -d @-
```

`metadata.columnHints` controls the column order in the CSV download for each data key. If omitted, column order is inferred from `Object.keys(records[0])`.

### Delete a template

```bash
curl -X DELETE "https://<ref>.supabase.co/functions/v1/template-manager?name=old-template" \
  -H "Authorization: Bearer $TOKENBRIDGE_API_KEY"
```

---

## Writing a custom template

Templates are self-contained HTML files. At runtime, the function replaces `<!-- __SLEEP_DATA__ -->` with a `<script>` block that sets `window.SLEEP_DATA`.

### Placeholder

Place this somewhere in `<head>`:

```html
<!-- __SLEEP_DATA__ -->
```

The function injects:

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

### Important: encoding

**Use HTML entities and JS/CSS unicode escapes for all non-ASCII characters.** Raw Unicode (e.g. `–`, `±`, `▸`) can be corrupted in the JSON storage roundtrip through Postgres.

```js
// Bad  — raw UTF-8 bytes will corrupt
var range = start + ' – ' + end;

// Good — JS unicode escape, always safe
var range = start + ' – ' + end;
```

```css
/* Bad  — raw UTF-8 */
content: '▸';

/* Good — CSS unicode escape */
content: '\25B8';
```

### Template source files

Local copies live in `supabase/templates/`. They are not auto-deployed — upload manually via `template-manager` after editing.

| File | Template name | Description |
|---|---|---|
| `supabase/templates/full.html` | `full` | Sleep summary |
| `supabase/templates/sleep-bp.html` | `sleep-bp` | Sleep + blood pressure |
| `supabase/templates/bp.html` | `bp` | Blood pressure only |
