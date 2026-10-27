import { createClient } from '@supabase/supabase-js'
import { providers, envPrefix } from '../_shared/providers.ts'
import { generateCodeVerifier, generateCodeChallenge } from '../_shared/pkce.ts'

Deno.serve(async (req) => {
  const url = new URL(req.url)
  const providerName = url.searchParams.get('provider')
  const userId = url.searchParams.get('user_id')
  const exp = url.searchParams.get('exp')
  const sig = url.searchParams.get('sig')

  if (!providerName || !userId || !exp || !sig) {
    return json({ error: 'provider, user_id, exp and sig are required query params - use auth_url()/tb_auth_url() to generate a valid link' }, 400)
  }

  // Links are HMAC-signed with TOKENBRIDGE_API_KEY (by auth_url()/tb_auth_url())
  // and time-limited, so an arbitrary user_id can't be injected by just
  // guessing this URL's shape.
  const apiKey = Deno.env.get('TOKENBRIDGE_API_KEY')
  const expNum = Number(exp)
  const validLink = apiKey
    && Number.isFinite(expNum)
    && expNum >= Date.now() / 1000
    && sig === await hmacHex(apiKey, `${providerName}:${userId}:${exp}`)

  if (!validLink) {
    return json({ error: 'this auth link is invalid or has expired - ask your researcher for a new one' }, 401)
  }

  const provider = providers[providerName]
  if (!provider) {
    return json({ error: `unknown provider "${providerName}". known: ${Object.keys(providers).join(', ')}` }, 400)
  }

  const clientId = Deno.env.get(`${envPrefix(providerName)}_CLIENT_ID`)
  if (!clientId) {
    return json({ error: `${envPrefix(providerName)}_CLIENT_ID is not configured` }, 500)
  }

  const supabase = createClient(
    Deno.env.get('SUPABASE_URL')!,
    Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!,
  )

  const state = crypto.randomUUID()
  let codeVerifier: string | null = null

  if (provider.pkce) {
    codeVerifier = generateCodeVerifier()
  }

  const { error: dbError } = await supabase.from('oauth_states').insert({
    state,
    provider: providerName,
    user_id: userId,
    code_verifier: codeVerifier,
  })

  if (dbError) {
    console.error('Failed to store oauth state:', dbError)
    return json({ error: 'internal error storing state' }, 500)
  }

  const callbackUrl = `${Deno.env.get('SUPABASE_URL')}/functions/v1/auth-callback`

  let scopeDelimiter = ' '; // Default fallback
  if (providerName === 'withings') {
    scopeDelimiter = ',';
  }

  const params = new URLSearchParams({
    client_id: clientId,
    redirect_uri: callbackUrl,
    response_type: 'code',
    scope: provider.scopes.join(scopeDelimiter),
    state,
    ...provider.authParams,
  })

  if (provider.pkce && codeVerifier) {
    const challenge = await generateCodeChallenge(codeVerifier)
    params.set('code_challenge', challenge)
    params.set('code_challenge_method', 'S256')
  }

  const authUrl = `${provider.authUrl}?${params}`
  if (url.searchParams.get('format') === 'json') {
    return json({ url: authUrl })
  }
  return Response.redirect(authUrl, 302)
})

function json(data: unknown, status = 200): Response {
  return new Response(JSON.stringify(data), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
}

async function hmacHex(key: string, msg: string): Promise<string> {
  const cryptoKey = await crypto.subtle.importKey(
    'raw', new TextEncoder().encode(key), { name: 'HMAC', hash: 'SHA-256' }, false, ['sign'],
  )
  const sigBuf = await crypto.subtle.sign('HMAC', cryptoKey, new TextEncoder().encode(msg))
  return Array.from(new Uint8Array(sigBuf)).map((b) => b.toString(16).padStart(2, '0')).join('')
}
