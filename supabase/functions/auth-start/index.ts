import { createClient } from '@supabase/supabase-js'
import { providers, envPrefix } from '../_shared/providers.ts'
import { generateCodeVerifier, generateCodeChallenge } from '../_shared/pkce.ts'

Deno.serve(async (req) => {
  const url = new URL(req.url)
  const providerName = url.searchParams.get('provider')
  const userId = url.searchParams.get('user_id')

  if (!providerName || !userId) {
    return json({ error: 'provider and user_id are required query params' }, 400)
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

  const params = new URLSearchParams({
    client_id: clientId,
    redirect_uri: callbackUrl,
    response_type: 'code',
    scope: provider.scopes.join(' '),
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
