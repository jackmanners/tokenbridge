export interface Provider {
  authUrl: string
  tokenUrl: string
  scopes: string[]
  pkce: boolean
  /** extra static params added to the auth redirect URL */
  authParams?: Record<string, string>
  /** extra static params added to every token exchange / refresh request body */
  extraTokenParams?: Record<string, string>
  /** transform token response body before storage (e.g. Withings wraps in .body) */
  unwrapTokenResponse?: (raw: Record<string, unknown>) => Record<string, unknown>
  /** extract provider-specific metadata to store in the provider_data jsonb column */
  extractProviderData?: (tokenData: Record<string, unknown>) => Record<string, unknown>
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
    // Withings requires action= on both token exchange and refresh
    extraTokenParams: { action: 'requesttoken' },
    // Withings wraps the token payload in a `.body` key
    unwrapTokenResponse: (raw) => (raw.body as Record<string, unknown>) ?? raw,
    // Withings userid is needed for partner endpoints (revoke, webhooks, etc.)
    extractProviderData: (td) => ({ userid: td.userid }),
  },
}

/** Derive the env var prefix from a provider name, e.g. "google-health" → "GOOGLE_HEALTH" */
export function envPrefix(providerName: string): string {
  return providerName.toUpperCase().replace(/-/g, '_')
}
