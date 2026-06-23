/**
 * token-keepalive — proactive token refresh to prevent refresh token expiry.
 *
 * Called weekly by GitHub Actions. Refreshes all tokens where
 * last_refreshed_at is older than 80 days (targeting a 90-day cycle,
 * well within Google's 6-month and Withings' 1-year refresh token windows).
 *
 * Tokens are processed oldest-first so the most at-risk are always handled
 * first, even if the run is interrupted.
 */

import { createClient } from '@supabase/supabase-js'
import { refreshAndStore } from '../_shared/refresh.ts'

const REFRESH_AFTER_DAYS = 80

Deno.serve(async (req) => {
  // Reuse the same API key as the /token endpoint
  const apiKey = Deno.env.get('TOKENBRIDGE_API_KEY')
  const auth   = req.headers.get('Authorization')
  if (!apiKey || auth !== `Bearer ${apiKey}`) {
    return json({ error: 'unauthorized' }, 401)
  }

  const supabase = createClient(
    Deno.env.get('SUPABASE_URL')!,
    Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!,
  )

  const cutoff = new Date(Date.now() - REFRESH_AFTER_DAYS * 24 * 60 * 60 * 1000).toISOString()

  // Tokens that haven't been refreshed in 80+ days, oldest first
  const { data: rows, error } = await supabase
    .from('oauth_tokens')
    .select('user_id, provider, refresh_token, expires_at, scopes, last_refreshed_at')
    .or(`last_refreshed_at.is.null,last_refreshed_at.lt.${cutoff}`)
    .not('refresh_token', 'is', null)
    .order('last_refreshed_at', { ascending: true, nullsFirst: true })

  if (error) return json({ error: error.message }, 500)
  if (!rows || rows.length === 0) return json({ refreshed: 0, message: 'nothing due' })

  const results = await Promise.allSettled(
    rows.map((row) => refreshAndStore(supabase, row as Parameters<typeof refreshAndStore>[1]))
  )

  const succeeded = results.filter((r) => r.status === 'fulfilled' && r.value.ok).length
  const failed    = results.length - succeeded

  const failures = results
    .map((r, i) => ({ row: rows[i], result: r }))
    .filter((x) => x.result.status === 'rejected' || (x.result.status === 'fulfilled' && !x.result.value.ok))
    .map((x) => ({
      user_id:  x.row.user_id,
      provider: x.row.provider,
      error:    x.result.status === 'rejected'
        ? x.result.reason
        : (x.result.value as { ok: false; error: unknown }).error,
    }))

  if (failures.length > 0) {
    console.error('token-keepalive: some refreshes failed:', JSON.stringify(failures))
  }

  return json({ refreshed: succeeded, failed, total: rows.length, failures })
})

function json(data: unknown, status = 200): Response {
  return new Response(JSON.stringify(data), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
}
