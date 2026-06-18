import { createClient } from '@supabase/supabase-js'

// Google Health webhook notification structure
interface WebhookNotification {
  version: string
  clientProvidedSubscriptionName: string
  healthUserId: string
  operation: 'UPSERT' | 'DELETE'
  dataType: string
  intervals: Array<{
    startTime: string        // UTC ISO 8601
    endTime: string          // UTC ISO 8601
    civilStartTime?: string  // local datetime ISO 8601
    civilEndTime?: string
  }>
}

Deno.serve(async (req) => {
  // Verify this came from our subscription using the shared secret
  const secret = Deno.env.get('WEBHOOK_SECRET')
  const authHeader = req.headers.get('Authorization')
  if (!secret || authHeader !== `Bearer ${secret}`) {
    return new Response('Unauthorized', { status: 401 })
  }

  let notification: WebhookNotification
  try {
    notification = await req.json()
  } catch {
    return new Response('Bad request', { status: 400 })
  }

  const supabase = createClient(
    Deno.env.get('SUPABASE_URL')!,
    Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!,
  )

  // Map Google's healthUserId → our user_id
  const { data: tokenRow } = await supabase
    .from('oauth_tokens')
    .select('user_id')
    .eq('health_user_id', notification.healthUserId)
    .eq('provider', 'google-health')
    .single()

  if (!tokenRow) {
    // Unknown user — log and acknowledge (returning non-2xx causes retries)
    console.warn('Received webhook for unknown healthUserId:', notification.healthUserId)
    return new Response(null, { status: 204 })
  }

  // Extract all calendar dates covered by the notification intervals
  const dates = new Set<string>()
  for (const interval of notification.intervals) {
    // Prefer civil (local) time for date attribution; fall back to UTC
    const startStr = interval.civilStartTime ?? interval.startTime
    const endStr = interval.civilEndTime ?? interval.endTime
    const start = new Date(startStr)
    const end = new Date(endStr)

    // Walk day by day through the interval
    const cursor = new Date(start)
    cursor.setHours(0, 0, 0, 0)
    const endDay = new Date(end)
    endDay.setHours(0, 0, 0, 0)

    while (cursor <= endDay) {
      dates.add(cursor.toISOString().slice(0, 10)) // YYYY-MM-DD
      cursor.setDate(cursor.getDate() + 1)
    }
  }

  if (dates.size === 0) {
    return new Response(null, { status: 204 })
  }

  const rows = Array.from(dates).map((date) => ({
    user_id: tokenRow.user_id,
    provider: 'google-health',
    data_type: notification.dataType,
    data_date: date,
    operation: notification.operation,
  }))

  if (notification.operation === 'DELETE') {
    // Mark deleted dates rather than removing rows, so gaps are visible in reports
    for (const row of rows) {
      await supabase
        .from('data_availability')
        .upsert(row, { onConflict: 'user_id,provider,data_type,data_date' })
    }
  } else {
    const { error } = await supabase
      .from('data_availability')
      .upsert(rows, { onConflict: 'user_id,provider,data_type,data_date' })

    if (error) {
      console.error('Failed to upsert data_availability:', error)
      return new Response('Internal error', { status: 500 })
    }
  }

  // Must respond 204 promptly — Google retries on any other status
  return new Response(null, { status: 204 })
})
