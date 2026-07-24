import { createClient } from '@supabase/supabase-js'
import { providers } from '../_shared/providers.ts'
import { doRefresh } from '../_shared/refresh.ts'

const cors = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
}

// Refresh a token this many ms before it actually expires
const REFRESH_BUFFER_MS = 5 * 60 * 1000

Deno.serve(async (req) => {
  if (req.method === 'OPTIONS') return new Response('ok', { headers: cors })

  // Verify caller API key
  const apiKey = Deno.env.get('TOKENBRIDGE_API_KEY')
  const auth = req.headers.get('Authorization')
  if (!apiKey || auth !== `Bearer ${apiKey}`) {
    return json({ error: 'unauthorized' }, 401)
  }

  let body: { provider?: string; user_id?: string }
  try {
    body = await req.json()
  } catch {
    return json({ error: 'request body must be JSON with provider and user_id' }, 400)
  }

  const { provider: providerName, user_id: userId } = body

  if (!providerName || !userId) {
    return json({ error: 'provider and user_id are required' }, 400)
  }

  const provider = providers[providerName]
  if (!provider) {
    return json({ error: `unknown provider "${providerName}"` }, 400)
  }

  const supabase = createClient(
    Deno.env.get('SUPABASE_URL')!,
    Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!,
  )

  const { data: row, error } = await supabase
    .from('oauth_tokens')
    .select('*')
    .eq('user_id', userId)
    .eq('provider', providerName)
    .single()

  if (error || !row) {
    const baseUrl = Deno.env.get('SUPABASE_URL')
    return json(
      {
        error: 'no token found for this user + provider',
        hint: `authorize at ${baseUrl}/functions/v1/auth-start?provider=${providerName}&user_id=${userId}`,
      },
      404,
    )
  }

  const expiresMs = row.expires_at ? new Date(row.expires_at).getTime() : null
  const needsRefresh = expiresMs !== null && expiresMs < Date.now() + REFRESH_BUFFER_MS

  if (!needsRefresh) {
    return json({
      access_token: row.access_token,
      expires_at: row.expires_at,
      scopes: row.scopes,
      provider: providerName,
      user_id: userId,
      refreshed: false,
      ...(row.provider_data ?? {}),
    })
  }

  if (!row.refresh_token) {
    return json({ error: 'token expired and no refresh_token is stored - re-authorize' }, 401)
  }

  const refreshResult = await doRefresh(providerName, provider, row.refresh_token)
  if (!refreshResult.ok) {
    console.error('Refresh failed:', refreshResult.error)
    return json({ error: 'token refresh failed', details: refreshResult.error }, 502)
  }

  const td = refreshResult.data
  const newExpiresAt = typeof td.expires_in === 'number'
    ? new Date(Date.now() + td.expires_in * 1000).toISOString()
    : row.expires_at

  const providerData = provider.extractProviderData ? provider.extractProviderData(td) : {}

  const { error: updateError } = await supabase
    .from('oauth_tokens')
    .update({
      access_token:      td.access_token as string,
      refresh_token:     (td.refresh_token as string | undefined) ?? row.refresh_token,
      expires_at:        newExpiresAt,
      provider_data:     providerData,
      last_refreshed_at: new Date().toISOString(),
      raw:               td,
    })
    .eq('user_id', userId)
    .eq('provider', providerName)

  if (updateError) {
    console.error('Failed to persist refreshed token:', updateError)
    // Still return the new token - the refresh succeeded
  }

  return json({
    access_token: td.access_token as string,
    expires_at: newExpiresAt,
    scopes: row.scopes,
    provider: providerName,
    user_id: userId,
    refreshed: true,
    ...providerData,
  })
})


function json(data: unknown, status = 200): Response {
  return new Response(JSON.stringify(data), {
    status,
    headers: { ...cors, 'Content-Type': 'application/json' },
  })
}
