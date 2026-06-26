# TokenBridge Report Templates

Reports are self-contained HTML files stored in the `report_templates` Postgres table and served by the `sleep-report` edge function.

## How it works

1. Caller sends a `POST /sleep-report` with `{ label, template, data }`.
2. The function fetches the named template from the DB.
3. It injects `window.SLEEP_DATA` into the `<!-- __SLEEP_DATA__ -->` placeholder.
4. Returns the fully rendered HTML page.

The server does **no domain processing** — all data arrives pre-flattened and the template renders whatever it finds.

---

## Request format

```bash
curl -X POST https://<ref>.supabase.co/functions/v1/sleep-report \
  -H "Authorization: Bearer $TOKENBRIDGE_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "label":    "P001",
    "template": "full",
    "data": {
      "withings-summary": [ { ...flat record... }, ... ]
    }
  }'
```

The response is `text/html` — write it to a `.html` file or stream it to the browser.

### Data keys per template

| Template    | Required data key(s)                        | Notes                              |
|-------------|---------------------------------------------|------------------------------------|
| `full`      | `withings-summary`                          | Sleep summary series               |
| `sleep-bp`  | `withings-summary`, `withings-bp`           | Sleep + blood pressure combined    |
| `bp`        | `withings-bp`                               | Blood pressure only                |

### `withings-summary` record shape

One flat object per sleep session (from Withings Sleep Summary Series):

```json
{
  "startdate":  1700000000,
  "enddate":    1700030000,
  "timezone":   "Australia/Adelaide",
  "total_sleep_time": 25200,
  "sleep_efficiency": 0.91,
  "apnea_hypopnea_index": 3.2,
  "hr_average": 58,
  ...
}
```

All Withings summary fields are accepted. `startdate`/`enddate` are Unix epoch seconds.

### `withings-bp` record shape

One flat object per Withings measurement group (meastype 9=diastolic, 10=systolic, 11=heart_pulse):

```json
{
  "date":        1700000000,
  "systolic":    118,
  "diastolic":   76,
  "heart_pulse": 64
}
```

`heart_pulse` is optional. `date` is the group timestamp (Unix epoch seconds).

---

## Managing templates

Templates are managed via the `template-manager` edge function.

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

### Upload / update a template

```bash
python3 -c "
import json
html = open('supabase/templates/full.html').read()
print(json.dumps({
  'name': 'full',
  'description': 'Sleep summary report',
  'metadata': {
    'columnHints': {
      'withings-summary': ['startdate','enddate','timezone','total_sleep_time', ...]
    }
  },
  'html': html
}))
" | curl -X POST https://<ref>.supabase.co/functions/v1/template-manager \
  -H "Authorization: Bearer $TOKENBRIDGE_API_KEY" \
  -H "Content-Type: application/json" \
  -d @-
```

`metadata.columnHints` sets the column order in the CSV download for each data key. If omitted, columns are inferred from `Object.keys(records[0])`.

The template **must** contain `<!-- __SLEEP_DATA__ -->` somewhere in `<head>` — the function will reject it otherwise.

### Delete a template

```bash
curl -X DELETE "https://<ref>.supabase.co/functions/v1/template-manager?name=old-template" \
  -H "Authorization: Bearer $TOKENBRIDGE_API_KEY"
```

---

## Writing a template

Templates are self-contained HTML files. At runtime the placeholder is replaced with:

```html
<script>
window.SLEEP_DATA = {
  "label": "P001",
  "reportTimestamp": "2024-01-15 09:30:00",
  "data": {
    "withings-summary": {
      "records": [ ... ],
      "csvDataUri": "data:text/csv;charset=utf-8;base64,..."
    }
  }
};
</script>
```

Access data in your template JS:

```js
const records  = window.SLEEP_DATA.data['withings-summary']?.records ?? [];
const csvLink  = window.SLEEP_DATA.data['withings-summary']?.csvDataUri;
const label    = window.SLEEP_DATA.label;
const ts       = window.SLEEP_DATA.reportTimestamp;
```

**Important:** Use HTML entities (`&#x25B8;`) and CSS unicode escapes (`'\25B8'`) for any non-ASCII characters in the template source. Raw Unicode (e.g. `▸`) can be corrupted in the JSON storage roundtrip.

---

## Local template files

Source templates live in `supabase/templates/`. They are **not** auto-deployed — upload manually via `template-manager` after editing.

| File                        | Template name | Description                    |
|-----------------------------|---------------|--------------------------------|
| `supabase/templates/full.html`     | `full`        | Sleep summary                  |
| `supabase/templates/sleep-bp.html` | `sleep-bp`    | Sleep + blood pressure combined |
| `supabase/templates/bp.html`       | `bp`          | Blood pressure only            |
