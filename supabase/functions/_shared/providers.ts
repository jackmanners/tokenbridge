export interface Provider {
  authUrl: string
  tokenUrl: string
  scopes: string[]
  pkce: boolean
  /** extra static params for the auth URL (e.g. Google needs access_type=offline) */
  authParams?: Record<string, string>
  /** transform token response body before storage (e.g. Withings wraps in .body) */
  unwrapTokenResponse?: (raw: Record<string, unknown>) => Record<string, unknown>
}

export const providers: Record<string, Provider> = {
  'google-health': {
    authUrl: 'https://accounts.google.com/o/oauth2/v2/auth',
    tokenUrl: 'https://oauth2.googleapis.com/token',
    scopes: [
      'openid',
      'https://www.googleapis.com/auth/fitness.activity.read',
      'https://www.googleapis.com/auth/fitness.body.read',
      'https://www.googleapis.com/auth/fitness.heart_rate.read',
      'https://www.googleapis.com/auth/fitness.sleep.read',
      'https://www.googleapis.com/auth/fitness.nutrition.read',
      'https://www.googleapis.com/auth/fitness.location.read',
    ],
    pkce: true,
    authParams: {
      access_type: 'offline',
      prompt: 'consent', // always return refresh_token
    },
  },

  'withings': {
    authUrl: 'https://account.withings.com/oauth2_user/authorize2',
    tokenUrl: 'https://wbsapi.withings.net/v2/oauth2',
    scopes: ['user.activity', 'user.metrics', 'user.sleepevents'],
    pkce: false,
    authParams: { response_type: 'code' },
    // Withings wraps the token payload in a `.body` key
    unwrapTokenResponse: (raw) => (raw.body as Record<string, unknown>) ?? raw,
  },
}

/** Derive the env var prefix from a provider name, e.g. "google-health" → "GOOGLE_HEALTH" */
export function envPrefix(providerName: string): string {
  return providerName.toUpperCase().replace(/-/g, '_')
}
