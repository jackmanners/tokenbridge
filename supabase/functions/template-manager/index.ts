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

Deno.serve(async (req) => {
  if (req.method === 'OPTIONS') return new Response('ok', { headers: cors })

  const apiKey = Deno.env.get('TOKENBRIDGE_API_KEY')
  const auth = req.headers.get('Authorization')
  if (!apiKey || auth !== `Bearer ${apiKey}`) return json({ error: 'unauthorized' }, 401)

  const supabase = createClient(
    Deno.env.get('SUPABASE_URL')!,
    Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!,
  )

  const url = new URL(req.url)
  const name = url.searchParams.get('name')

  if (req.method === 'GET') {
    if (name) {
      const { data, error } = await supabase
        .from('report_templates')
        .select('*')
        .eq('name', name)
        .single()
      if (error || !data) return json({ error: `template "${name}" not found` }, 404)
      return json(data)
    }
    const { data, error } = await supabase
      .from('report_templates')
      .select('name, description, metadata, created_at, updated_at')
      .order('name')
    if (error) return json({ error: error.message }, 500)
    return json(data)
  }

  if (req.method === 'POST') {
    let body: { name: string; description?: string; metadata?: Record<string, unknown>; html: string }
    try { body = await req.json() }
    catch { return json({ error: 'invalid json' }, 400) }

    if (!body.name || !body.html) return json({ error: 'name and html are required' }, 400)
    if (!body.html.includes('<!-- __SLEEP_DATA__ -->')) {
      return json({ error: 'html must contain <!-- __SLEEP_DATA__ --> placeholder' }, 400)
    }

    const { error } = await supabase.from('report_templates').upsert({
      name: body.name,
      description: body.description ?? null,
      metadata: body.metadata ?? {},
      html: body.html,
      updated_at: new Date().toISOString(),
    }, { onConflict: 'name' })

    if (error) return json({ error: error.message }, 500)
    return json({ ok: true, name: body.name })
  }

  if (req.method === 'DELETE') {
    if (!name) return json({ error: '?name= required' }, 400)
    const { error } = await supabase.from('report_templates').delete().eq('name', name)
    if (error) return json({ error: error.message }, 500)
    return json({ ok: true })
  }

  return json({ error: 'method not allowed' }, 405)
})
