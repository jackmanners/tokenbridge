import { createClient } from '@supabase/supabase-js'
import { providers, envPrefix } from '../_shared/providers.ts'

Deno.serve(async (req) => {
  const url = new URL(req.url)
  const code = url.searchParams.get('code')
  const state = url.searchParams.get('state')
  const oauthError = url.searchParams.get('error')
  const errorDesc = url.searchParams.get('error_description')

  if (oauthError) {
    return html(`<h1>Authorization denied</h1><p>${oauthError}: ${errorDesc ?? ''}</p>`, 400)
  }

  if (!code || !state) {
    return html('<h1>Bad request</h1><p>Missing code or state parameter.</p>', 400)
  }

  const supabase = createClient(
    Deno.env.get('SUPABASE_URL')!,
    Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!,
  )

  const { data: stateRow, error: stateError } = await supabase
    .from('oauth_states')
    .select('*')
    .eq('state', state)
    .gt('expires_at', new Date().toISOString())
    .single()

  if (stateError || !stateRow) {
    return html('<h1>Invalid or expired state</h1><p>Try authorizing again.</p>', 400)
  }

  // Consume state (one-time use) and opportunistically clean up any other expired rows
  await supabase.from('oauth_states').delete().eq('state', state)
  supabase.rpc('cleanup_oauth_states').then(() => {}).catch(() => {})

  const provider = providers[stateRow.provider]
  if (!provider) {
    return html(`<h1>Unknown provider</h1><p>${stateRow.provider}</p>`, 500)
  }

  const clientId = Deno.env.get(`${envPrefix(stateRow.provider)}_CLIENT_ID`)!
  const clientSecret = Deno.env.get(`${envPrefix(stateRow.provider)}_CLIENT_SECRET`)!
  const callbackUrl = `${Deno.env.get('SUPABASE_URL')}/functions/v1/auth-callback`

  const tokenParams: Record<string, string> = {
    code,
    client_id: clientId,
    client_secret: clientSecret,
    redirect_uri: callbackUrl,
    grant_type: 'authorization_code',
    ...provider.extraTokenParams,
  }

  if (stateRow.code_verifier) {
    tokenParams.code_verifier = stateRow.code_verifier
  }

  const tokenRes = await fetch(provider.tokenUrl, {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: new URLSearchParams(tokenParams),
  })

  const raw = await tokenRes.json() as Record<string, unknown>

  if (!tokenRes.ok || (raw.error as string)) {
    console.error('Token exchange failed:', raw)
    return html(`<h1>Token exchange failed</h1><pre>${JSON.stringify(raw, null, 2)}</pre>`, 502)
  }

  const tokenData = provider.unwrapTokenResponse ? provider.unwrapTokenResponse(raw) : raw

  const expiresAt = typeof tokenData.expires_in === 'number'
    ? new Date(Date.now() + tokenData.expires_in * 1000).toISOString()
    : null

  const scopeStr = tokenData.scope as string | undefined
  const scopes = scopeStr ? scopeStr.split(/[\s,]+/) : provider.scopes

  const { error: upsertError } = await supabase.from('oauth_tokens').upsert(
    {
      user_id: stateRow.user_id,
      provider: stateRow.provider,
      access_token: tokenData.access_token as string,
      refresh_token: (tokenData.refresh_token as string | undefined) ?? null,
      expires_at: expiresAt,
      scopes,
      raw,
    },
    { onConflict: 'user_id,provider' },
  )

  if (upsertError) {
    console.error('Failed to store token:', upsertError)
    return html('<h1>Failed to store token</h1><p>Check function logs.</p>', 500)
  }

  return html(`
    <h1>✅ Connected!</h1>
    <p><strong>Provider:</strong> ${stateRow.provider}</p>
    <p><strong>User:</strong> ${stateRow.user_id}</p>
    <p>Token stored. You can close this window.</p>
  `)
})

function html(body: string, status = 200): Response {
  return new Response(
    `<!DOCTYPE html><html><head><meta charset="utf-8"><title>TokenBridge</title></head>` +
    `<body style="font-family:sans-serif;max-width:560px;margin:3rem auto;padding:0 1rem">${body}</body></html>`,
    { status, headers: { 'Content-Type': 'text/html' } },
  )
}
