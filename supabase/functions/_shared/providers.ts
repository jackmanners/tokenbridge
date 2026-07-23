export interface Provider {
  authUrl: string
  tokenUrl: string
  scopes: string[]
  pkce: boolean
  /** extra static params added to the auth redirect URL */
  authParams?: Record<string, string>
  /** extra static params added to every token exchange / refresh request body */
  extraTokenParams?: Record<string, string>
  /**
   * How client credentials are sent on the token exchange request.
   * 'body' (default) puts client_id/client_secret in the form body.
   * 'basic' sends them as an `Authorization: Basic base64(id:secret)` header
   * instead, and omits them from the body (required by e.g. Polar).
   */
  tokenAuthMethod?: 'body' | 'basic'
  /** transform token response body before storage (e.g. Withings wraps in .body) */
  unwrapTokenResponse?: (raw: Record<string, unknown>) => Record<string, unknown>
  /** extract provider-specific metadata to store in the provider_data jsonb column */
  extractProviderData?: (tokenData: Record<string, unknown>) => Record<string, unknown>
  /**
   * Run once, immediately after a successful token exchange, before the token
   * is stored. Used for providers that require a registration call before any
   * data endpoint works (e.g. Polar's `POST /v3/users`). Return additional
   * provider_data fields to merge in (e.g. a provider-assigned user id).
   * Throwing here aborts the whole auth-callback with a 502.
   */
  postTokenExchange?: (ctx: {
    accessToken: string
    clientId: string
    clientSecret: string
    userId: string
  }) => Promise<Record<string, unknown>>
}

export const providers: Record<string, Provider> = {
  'google-health': {
    authUrl: 'https://accounts.google.com/o/oauth2/v2/auth',
    tokenUrl: 'https://oauth2.googleapis.com/token',
    scopes: [
      // Google Health API readonly scopes (full list as of 2026)
      'https://www.googleapis.com/auth/googlehealth.activity_and_fitness.readonly',
      'https://www.googleapis.com/auth/googlehealth.ecg.readonly',
      'https://www.googleapis.com/auth/googlehealth.health_metrics_and_measurements.readonly',
      'https://www.googleapis.com/auth/googlehealth.irn.readonly',
      'https://www.googleapis.com/auth/googlehealth.location.readonly',
      'https://www.googleapis.com/auth/googlehealth.nutrition.readonly',
      'https://www.googleapis.com/auth/googlehealth.profile.readonly',
      'https://www.googleapis.com/auth/googlehealth.settings.readonly',
      'https://www.googleapis.com/auth/googlehealth.sleep.readonly',
    ],
    pkce: true,
    authParams: {
      access_type: 'offline',
      prompt: 'consent', // always return refresh_token
    },
  },

  'oura': {
    authUrl: 'https://cloud.ouraring.com/oauth/authorize',
    tokenUrl: 'https://api.ouraring.com/oauth/token',
    scopes: ['email', 'personal', 'daily', 'heartrate', 'workout', 'tag', 'session', 'spo2Daily'],
    pkce: false,
  },

  'withings': {
    authUrl: 'https://account.withings.com/oauth2_user/authorize2',
    tokenUrl: 'https://wbsapi.withings.net/v2/oauth2',
    scopes: ['user.info', 'user.metrics', 'user.activity', 'user.sleepevents'],
    pkce: false,
    authParams: { response_type: 'code' },
    extraTokenParams: { action: 'requesttoken' },
    unwrapTokenResponse: (raw) => (raw.body as Record<string, unknown>) ?? raw,
    extractProviderData: (td) => ({ userid: td.userid }),
  },

  // ── Polar ─────────────────────────────────────────────────────────────────
  // Polar access tokens never expire (no refresh_token) - they're only
  // invalidated if the user revokes access in Polar Flow.
  'polar': {
    authUrl: 'https://flow.polar.com/oauth2/authorization',
    tokenUrl: 'https://polarremote.com/v2/oauth2/token',
    scopes: ['accesslink.read_all'],
    pkce: false,
    tokenAuthMethod: 'basic',
    // New users must be registered with AccessLink before any data endpoint
    // works. Do this once, right after the token exchange, and store the
    // Polar-assigned user id for reference.
    postTokenExchange: async ({ accessToken, userId }) => {
      const res = await fetch('https://www.polaraccesslink.com/v3/users', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${accessToken}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ 'member-id': userId }),
      })
      // 409 = already registered (e.g. re-auth) - not an error.
      if (res.status === 409) return {}
      if (!res.ok) {
        throw new Error(`Polar user registration failed (${res.status}): ${await res.text()}`)
      }
      const body = await res.json()
      return { 'polar-user-id': body['polar-user-id'] }
    },
  },

  // ── Strava ────────────────────────────────────────────────────────────────
  'strava': {
    authUrl: 'https://www.strava.com/oauth/authorize',
    tokenUrl: 'https://www.strava.com/oauth/token',
    scopes: ['activity:read_all', 'profile:read_all'],
    pkce: false,
    authParams: { approval_prompt: 'auto' },
    // Strava returns athlete profile in the token response
    extractProviderData: (td) => ({
      athlete_id: (td.athlete as Record<string, unknown>)?.id ?? null,
    }),
  },

  // ── WHOOP ─────────────────────────────────────────────────────────────────
  'whoop': {
    authUrl: 'https://api.prod.whoop.com/oauth2/auth',
    tokenUrl: 'https://api.prod.whoop.com/oauth2/token',
    scopes: [
      'read:recovery',
      'read:sleep',
      'read:workout',
      'read:profile',
      'read:cycles',
      'read:body_measurement',
      'offline',
    ],
    pkce: true,
  },

  // ── Garmin ───────────────────────────────────────────────────────────────
  // Requires Garmin developer program approval (invite-only).
  // https://developer.garmin.com/gc-developer-program/overview/
  'garmin': {
    authUrl: 'https://connect.garmin.com/oauthConfirm',
    tokenUrl: 'https://connectapi.garmin.com/oauth-service/oauth/token',
    scopes: ['HEALTH_API'],
    pkce: false,
    // TODO: Garmin's token endpoint may require additional params —
    // verify against approved developer documentation.
  },

  // ── Huawei Health Kit ─────────────────────────────────────────────────────
  // Requires AppGallery Connect registration with Health Kit scope.
  // https://developer.huawei.com/consumer/en/doc/appgallery-connect-guides/agcapi-getstarted-0000001111845114
  'huawei': {
    authUrl: 'https://oauth-login.cloud.huawei.com/oauth2/v3/authorize',
    tokenUrl: 'https://oauth-login.cloud.huawei.com/oauth2/v3/token',
    scopes: [
      'https://www.huawei.com/healthkit/step.read',
      'https://www.huawei.com/healthkit/sleep.read',
      'https://www.huawei.com/healthkit/heartrate.read',
      'https://www.huawei.com/healthkit/activity.record.read',
      'https://www.huawei.com/healthkit/oxygenSaturation.read',
      'https://www.huawei.com/healthkit/bloodPressure.read',
      'https://www.huawei.com/healthkit/bodyWeight.read',
      'https://www.huawei.com/healthkit/calories.read',
      'https://www.huawei.com/healthkit/stress.read',
    ],
    pkce: false,
  },

  // ── Health Connect ────────────────────────────────────────────────────────
  // Health Connect is an Android SDK — no cloud OAuth flow.
  // Data access requires a gateway app on the participant's device.
  // This entry is a placeholder; auth-start will not work for this provider.
  // 'health-connect': { ... }

  // ── Dexcom (continuous glucose monitoring) ────────────────────────────────
  // Sandbox access is immediate and self-service; production access for real
  // users requires a short application (no lengthy sales process for small
  // participant counts). Swap tokenUrl/authUrl to the sandbox host while
  // developing: https://sandbox-api.dexcom.com
  'dexcom': {
    authUrl: 'https://api.dexcom.com/v2/oauth2/login',
    tokenUrl: 'https://api.dexcom.com/v2/oauth2/token',
    scopes: ['offline_access'],
    pkce: false,
  },
}

/** Derive the env var prefix from a provider name, e.g. "google-health" → "GOOGLE_HEALTH" */
export function envPrefix(providerName: string): string {
  return providerName.toUpperCase().replace(/-/g, '_')
}
