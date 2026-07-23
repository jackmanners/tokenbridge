import { createClient } from '@supabase/supabase-js'
import { providers, envPrefix } from '../_shared/providers.ts'

Deno.serve(async (req) => {
  const url = new URL(req.url)
  const code = url.searchParams.get('code')
  const state = url.searchParams.get('state')
  const oauthError = url.searchParams.get('error')
  const errorDesc = url.searchParams.get('error_description')

  if (oauthError) {
    return text(`Authorisation denied

${oauthError}${errorDesc ? ': ' + errorDesc : ''}

You can close this window and try again.`, 400)
  }

  if (!code || !state) {
    return text('Bad request: missing required parameters. Please use the link provided by your researcher.', 400)
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
    return text('This authorisation link has expired or has already been used. Ask your researcher for a new link.', 400)
  }

  // Consume state (one-time use) and opportunistically clean up any other expired rows
  await supabase.from('oauth_states').delete().eq('state', state)
  supabase.rpc('cleanup_oauth_states').then(() => {}).catch(() => {})

  const provider = providers[stateRow.provider]
  if (!provider) {
    return text(`Internal error: provider "${stateRow.provider}" is not configured.`, 500)
  }

  const clientId = Deno.env.get(`${envPrefix(stateRow.provider)}_CLIENT_ID`)!
  const clientSecret = Deno.env.get(`${envPrefix(stateRow.provider)}_CLIENT_SECRET`)!
  const callbackUrl = `${Deno.env.get('SUPABASE_URL')}/functions/v1/auth-callback`

  const useBasicAuth = provider.tokenAuthMethod === 'basic'

  const tokenParams: Record<string, string> = {
    code,
    redirect_uri: callbackUrl,
    grant_type: 'authorization_code',
    ...(useBasicAuth ? {} : { client_id: clientId, client_secret: clientSecret }),
    ...provider.extraTokenParams,
  }

  if (stateRow.code_verifier) {
    tokenParams.code_verifier = stateRow.code_verifier
  }

  const tokenHeaders: Record<string, string> = { 'Content-Type': 'application/x-www-form-urlencoded' }
  if (useBasicAuth) {
    tokenHeaders.Authorization = `Basic ${btoa(`${clientId}:${clientSecret}`)}`
  }

  const tokenRes = await fetch(provider.tokenUrl, {
    method: 'POST',
    headers: tokenHeaders,
    body: new URLSearchParams(tokenParams),
  })

  const raw = await tokenRes.json() as Record<string, unknown>

  if (!tokenRes.ok || (raw.error as string)) {
    console.error('Token exchange failed:', raw)
    return text(`Token exchange failed. Check the edge function logs for details.\n\n${JSON.stringify(raw, null, 2)}`, 502)
  }

  const tokenData = provider.unwrapTokenResponse ? provider.unwrapTokenResponse(raw) : raw

  const expiresAt = typeof tokenData.expires_in === 'number'
    ? new Date(Date.now() + tokenData.expires_in * 1000).toISOString()
    : null

  const scopeStr = tokenData.scope as string | undefined
  const scopes = scopeStr ? scopeStr.split(/[\s,]+/) : provider.scopes

  let providerData = provider.extractProviderData ? provider.extractProviderData(tokenData) : {}

  if (provider.postTokenExchange) {
    try {
      const extra = await provider.postTokenExchange({
        accessToken: tokenData.access_token as string,
        clientId,
        clientSecret,
        userId: stateRow.user_id,
      })
      providerData = { ...providerData, ...extra }
    } catch (e) {
      console.error('postTokenExchange failed:', e)
      return text(
        `Token exchange succeeded but a required setup step failed: ${e instanceof Error ? e.message : e}\n\n` +
        'Check the edge function logs for details.',
        502,
      )
    }
  }

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
    return text('The token was received but could not be saved. Check the edge function logs for details.', 500)
  }

  return text(`Connected

Provider:       ${stateRow.provider}
Participant ID: ${stateRow.user_id}

You can close this window.`)
})

function text(message: string, status = 200): Response {
  return new Response(message, { status, headers: { 'Content-Type': 'text/plain' } })
}
