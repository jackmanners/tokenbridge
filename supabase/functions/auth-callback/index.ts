import { createClient } from '@supabase/supabase-js'
import { providers, envPrefix } from '../_shared/providers.ts'

Deno.serve(async (req) => {
  const url = new URL(req.url)
  const code = url.searchParams.get('code')
  const state = url.searchParams.get('state')
  const oauthError = url.searchParams.get('error')
  const errorDesc = url.searchParams.get('error_description')

  if (oauthError) {
    const safe = (s: string) => s.replace(/[<>&"]/g, (c) => `&#${c.charCodeAt(0)};`)
    return page('warn', 'Authorisation denied',
      `<p class="lead">${safe(oauthError)}${errorDesc ? ': ' + safe(errorDesc) : ''}</p>
       <p class="note">You can close this window and try again.</p>`, 400)
  }

  if (!code || !state) {
    return page('error', 'Bad request',
      `<p class="lead">Missing required parameters. Please use the link provided by your researcher.</p>`, 400)
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
    return page('error', 'Link expired',
      `<p class="lead">This authorisation link has expired or already been used.</p>
       <p class="note">Ask your researcher for a new link.</p>`, 400)
  }

  // Consume state (one-time use) and opportunistically clean up any other expired rows
  await supabase.from('oauth_states').delete().eq('state', state)
  supabase.rpc('cleanup_oauth_states').then(() => {}).catch(() => {})

  const provider = providers[stateRow.provider]
  if (!provider) {
    return page('error', 'Unknown provider',
      `<p class="lead">Provider <code>${stateRow.provider}</code> is not configured.</p>`, 500)
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
    return page('error', 'Token exchange failed',
      `<pre>${JSON.stringify(raw, null, 2)}</pre>
       <p class="note">Check the edge function logs for details.</p>`, 502)
  }

  const tokenData = provider.unwrapTokenResponse ? provider.unwrapTokenResponse(raw) : raw

  const expiresAt = typeof tokenData.expires_in === 'number'
    ? new Date(Date.now() + tokenData.expires_in * 1000).toISOString()
    : null

  const scopeStr = tokenData.scope as string | undefined
  const scopes = scopeStr ? scopeStr.split(/[\s,]+/) : provider.scopes

  const providerData = provider.extractProviderData ? provider.extractProviderData(tokenData) : {}

  const { error: upsertError } = await supabase.from('oauth_tokens').upsert(
    {
      user_id:           stateRow.user_id,
      provider:          stateRow.provider,
      access_token:      tokenData.access_token as string,
      refresh_token:     (tokenData.refresh_token as string | undefined) ?? null,
      expires_at:        expiresAt,
      scopes,
      provider_data:     providerData,
      last_refreshed_at: new Date().toISOString(),
      raw,
    },
    { onConflict: 'user_id,provider' },
  )

  if (upsertError) {
    console.error('Failed to store token:', upsertError)
    return page('error', 'Failed to store token',
      `<p class="lead">The token was received but could not be saved.</p>
       <p class="note">Check the edge function logs for details.</p>`, 500)
  }

  return page('success', 'Connected', `
    <p class="lead">Your account has been linked successfully.</p>
    <dl>
      <dt>Provider</dt><dd>${stateRow.provider}</dd>
      <dt>Participant ID</dt><dd>${stateRow.user_id}</dd>
    </dl>
    <p class="note">You can close this window.</p>
  `)
})

function page(type: 'success' | 'error' | 'warn', title: string, body: string, status = 200): Response {
  const icon   = type === 'success' ? '✓' : type === 'warn' ? '!' : '✕'
  const color  = type === 'success' ? '#16a34a' : type === 'warn' ? '#d97706' : '#dc2626'
  const bg     = type === 'success' ? '#f0fdf4' : type === 'warn' ? '#fffbeb' : '#fef2f2'
  const border = type === 'success' ? '#bbf7d0' : type === 'warn' ? '#fde68a' : '#fecaca'

  return new Response(`<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>TokenBridge — ${title}</title>
  <style>
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0 }
    body {
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      background: #f8fafc;
      min-height: 100vh;
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 1.5rem;
      color: #1e293b;
    }
    .card {
      background: #fff;
      border: 1px solid #e2e8f0;
      border-radius: 12px;
      padding: 2.5rem 2rem;
      max-width: 440px;
      width: 100%;
      box-shadow: 0 1px 3px rgba(0,0,0,.06), 0 4px 16px rgba(0,0,0,.04);
    }
    .badge {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      width: 48px; height: 48px;
      border-radius: 50%;
      background: ${bg};
      border: 1.5px solid ${border};
      color: ${color};
      font-size: 1.4rem;
      font-weight: 700;
      margin-bottom: 1.25rem;
    }
    h1 { font-size: 1.25rem; font-weight: 600; margin-bottom: .5rem }
    .lead { color: #475569; font-size: .95rem; margin-bottom: 1.25rem }
    dl {
      background: #f8fafc;
      border: 1px solid #e2e8f0;
      border-radius: 8px;
      padding: .75rem 1rem;
      margin-bottom: 1.25rem;
      display: grid;
      grid-template-columns: auto 1fr;
      gap: .35rem .75rem;
      font-size: .875rem;
    }
    dt { color: #64748b; font-weight: 500 }
    dd { color: #1e293b; font-family: 'SF Mono', 'Fira Code', monospace; font-size: .825rem }
    .note { font-size: .8rem; color: #94a3b8 }
    pre {
      background: #f8fafc;
      border: 1px solid #e2e8f0;
      border-radius: 8px;
      padding: .75rem 1rem;
      font-size: .8rem;
      overflow-x: auto;
      white-space: pre-wrap;
      word-break: break-all;
      margin-bottom: 1rem;
    }
  </style>
</head>
<body>
  <div class="card">
    <div class="badge">${icon}</div>
    <h1>${title}</h1>
    ${body}
  </div>
</body>
</html>`, { status, headers: { 'Content-Type': 'text/html' } })
}
