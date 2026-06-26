import { createClient } from '@supabase/supabase-js'

const cors = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
}

function json(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { ...cors, 'Content-Type': 'application/json' },
  })
}

function toCsv(rows: Record<string, unknown>[], columns: string[]): string {
  const escape = (v: unknown) => {
    if (v == null) return ''
    const s = typeof v === 'object' ? JSON.stringify(v) : String(v)
    return s.includes(',') || s.includes('"') || s.includes('\n')
      ? `"${s.replace(/"/g, '""')}"` : s
  }
  return [
    columns.map(escape).join(','),
    ...rows.map(row => columns.map(c => escape(row[c])).join(',')),
  ].join('\n')
}

function toDataUri(csv: string): string {
  const bytes = new TextEncoder().encode(csv)
  let binary = ''
  for (const b of bytes) binary += String.fromCharCode(b)
  return `data:text/csv;charset=utf-8;base64,${btoa(binary)}`
}

Deno.serve(async (req) => {
  if (req.method === 'OPTIONS') return new Response('ok', { headers: cors })

  const apiKey = Deno.env.get('TOKENBRIDGE_API_KEY')
  const auth = req.headers.get('Authorization')
  if (!apiKey || auth !== `Bearer ${apiKey}`) return json({ error: 'unauthorized' }, 401)
  if (req.method !== 'POST') return json({ error: 'method not allowed' }, 405)

  let body: { label: string; template?: string; data: Record<string, unknown[]> }
  try { body = await req.json() }
  catch { return json({ error: 'invalid json' }, 400) }

  const { label, template: templateName = 'full', data } = body
  if (!label || !data || typeof data !== 'object' || Array.isArray(data)) {
    return json({
      error: 'invalid request body',
      expected: {
        label: 'string — shown in report header (e.g. participant ID)',
        template: 'string — template name in DB, defaults to "full"',
        data: 'object — named arrays of flat records, e.g. { "withings-summary": [...] }',
      },
      example: {
        label: 'P001',
        template: 'full',
        data: { 'withings-summary': [{ id: 1, startdate: 1700000000, enddate: 1700030000, timezone: 'Australia/Adelaide' }] },
      },
    }, 400)
  }

  const supabase = createClient(
    Deno.env.get('SUPABASE_URL')!,
    Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!,
  )

  const { data: tmpl, error: tmplError } = await supabase
    .from('report_templates')
    .select('html, metadata')
    .eq('name', templateName)
    .single()

  if (tmplError || !tmpl) {
    return json({ error: `template "${templateName}" not found` }, 404)
  }

  // Build injection: one { records, csvDataUri } per data key.
  // Column order comes from template metadata.columnHints[key], falling back to key inference.
  const columnHints: Record<string, string[]> = tmpl.metadata?.columnHints ?? {}
  const injected: Record<string, { records: unknown[]; csvDataUri: string }> = {}

  for (const [key, records] of Object.entries(data)) {
    if (!Array.isArray(records) || records.length === 0) continue
    const columns = columnHints[key] ?? Object.keys(records[0] as Record<string, unknown>)
    injected[key] = {
      records,
      csvDataUri: toDataUri(toCsv(records as Record<string, unknown>[], columns)),
    }
  }

  const reportTimestamp = new Date().toISOString().replace('T', ' ').slice(0, 19)
  const scriptBlock = `<script>
window.SLEEP_DATA = ${JSON.stringify({ label, reportTimestamp, data: injected })};
</script>`

  const html = tmpl.html.replace('<!-- __SLEEP_DATA__ -->', scriptBlock)

  return new Response(html, {
    status: 200,
    headers: { ...cors, 'Content-Type': 'text/html; charset=utf-8' },
  })
})
