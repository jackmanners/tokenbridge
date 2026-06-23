import { providers, envPrefix, type Provider } from './providers.ts'

export type RefreshResult =
  | { ok: true;  data: Record<string, unknown> }
  | { ok: false; error: unknown }

export async function doRefresh(
  providerName: string,
  provider: Provider,
  refreshToken: string,
): Promise<RefreshResult> {
  const clientId     = Deno.env.get(`${envPrefix(providerName)}_CLIENT_ID`)!
  const clientSecret = Deno.env.get(`${envPrefix(providerName)}_CLIENT_SECRET`)!

  const params: Record<string, string> = {
    grant_type:    'refresh_token',
    refresh_token: refreshToken,
    client_id:     clientId,
    client_secret: clientSecret,
    ...provider.extraTokenParams,
  }

  const res = await fetch(provider.tokenUrl, {
    method:  'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body:    new URLSearchParams(params),
  })

  const raw = await res.json() as Record<string, unknown>

  if (!res.ok || raw.error) {
    return { ok: false, error: raw }
  }

  const data = provider.unwrapTokenResponse ? provider.unwrapTokenResponse(raw) : raw
  return { ok: true, data }
}

export async function refreshAndStore(
  supabase: ReturnType<typeof import('@supabase/supabase-js').createClient>,
  row: { user_id: string; provider: string; refresh_token: string; expires_at: string | null; scopes: string[] },
): Promise<{ ok: true } | { ok: false; error: unknown }> {
  const provider = providers[row.provider]
  if (!provider) return { ok: false, error: `unknown provider: ${row.provider}` }

  const result = await doRefresh(row.provider, provider, row.refresh_token)
  if (!result.ok) return result

  const td = result.data
  const newExpiresAt = typeof td.expires_in === 'number'
    ? new Date(Date.now() + (td.expires_in as number) * 1000).toISOString()
    : row.expires_at

  const providerData = provider.extractProviderData ? provider.extractProviderData(td) : {}

  const { error } = await supabase
    .from('oauth_tokens')
    .update({
      access_token:       td.access_token as string,
      refresh_token:      (td.refresh_token as string | undefined) ?? row.refresh_token,
      expires_at:         newExpiresAt,
      provider_data:      providerData,
      last_refreshed_at:  new Date().toISOString(),
      raw:                td,
    })
    .eq('user_id', row.user_id)
    .eq('provider', row.provider)

  if (error) return { ok: false, error }
  return { ok: true }
}
