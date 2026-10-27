/**
 * TokenBridge platform client (JavaScript).
 *
 * Token retrieval and auth-link generation only - this package does not
 * wrap provider data APIs (see the Python/R packages if you want that).
 * Once you have a token, call the provider's own API directly.
 *
 * Quick start:
 *   import { TokenBridge } from "tokenbridge";
 *
 *   const tb = new TokenBridge();               // reads TOKENBRIDGE_URL/TOKENBRIDGE_API_KEY from .env
 *
 *   console.log(tb.authUrl("p001"));            // send to participant
 *   const token = await tb.getToken("p001", "withings");
 *   // now call https://wbsapi.withings.net/... (or whichever provider) with `token` yourself
 */

import { createHmac } from "node:crypto";
import { existsSync, readFileSync } from "node:fs";

const AUTH_LINK_LIFETIME_S = 7 * 24 * 3600;

function loadEnvFile(envFile: string): void {
  if (!existsSync(envFile)) return;
  for (const rawLine of readFileSync(envFile, "utf8").split("\n")) {
    const line = rawLine.trim();
    const eq = line.indexOf("=");
    if (!line || line.startsWith("#") || eq === -1) continue;
    const key = line.slice(0, eq).trim();
    const value = line.slice(eq + 1).trim().replace(/^['"]|['"]$/g, "");
    if (process.env[key] === undefined) process.env[key] = value;
  }
}

export class TokenBridgeError extends Error {}

export interface TokenBridgeOptions {
  /** TokenBridge deployment URL, e.g. https://xxx.supabase.co/functions/v1. Falls back to TOKENBRIDGE_URL. */
  url?: string;
  /** TokenBridge API key. Falls back to TOKENBRIDGE_API_KEY. */
  apiKey?: string;
  /** .env file to read the above from if not passed/set. Default ".env". */
  envFile?: string;
  /** Default provider id used by authUrl()/authUrls()/getToken(). Default "google-health". */
  provider?: string;
}

/**
 * Client for the TokenBridge token management service.
 *
 * Responsible only for auth-link generation and token retrieval - fetching
 * data from a provider's API with the returned token is up to you.
 */
export class TokenBridge {
  readonly url: string;
  readonly apiKey: string;
  provider: string;

  constructor(options: TokenBridgeOptions = {}) {
    loadEnvFile(options.envFile ?? ".env");

    this.url = (options.url ?? process.env.TOKENBRIDGE_URL ?? "").replace(/\/+$/, "");
    this.apiKey = options.apiKey ?? process.env.TOKENBRIDGE_API_KEY ?? "";
    this.provider = options.provider ?? "google-health";

    if (!this.url) throw new TokenBridgeError("TOKENBRIDGE_URL is not set");
    if (!this.apiKey) throw new TokenBridgeError("TOKENBRIDGE_API_KEY is not set");
  }

  /**
   * Return a signed, time-limited auth URL for one participant.
   * Send this to them - once they complete OAuth, their token is stored
   * and getToken() will return it immediately.
   */
  authUrl(userId: string, provider: string = this.provider): string {
    const exp = Math.floor(Date.now() / 1000) + AUTH_LINK_LIFETIME_S;
    const sig = createHmac("sha256", this.apiKey)
      .update(`${provider}:${userId}:${exp}`)
      .digest("hex");
    const params = new URLSearchParams({ provider, user_id: userId, exp: String(exp), sig });
    return `${this.url}/auth-start?${params.toString()}`;
  }

  /** Batch version of authUrl() - returns a map of user_id to auth URL. */
  authUrls(userIds: string[], provider: string = this.provider): Record<string, string> {
    return Object.fromEntries(userIds.map((id) => [id, this.authUrl(id, provider)]));
  }

  /**
   * Return a valid access token for this user + provider, auto-refreshing
   * if it's near expiry. Throws TokenBridgeError (with a re-auth link) if
   * the participant hasn't authorised yet or their refresh token expired.
   */
  async getToken(userId: string, provider: string = this.provider): Promise<string> {
    const res = await fetch(`${this.url}/token`, {
      method: "POST",
      headers: { Authorization: `Bearer ${this.apiKey}`, "Content-Type": "application/json" },
      body: JSON.stringify({ provider, user_id: userId }),
    });

    const body = (await res.json().catch(() => ({}))) as Record<string, unknown>;

    if (res.status === 404) {
      throw new TokenBridgeError(
        `No token found for user '${userId}' (provider: ${provider}). ` +
          `Send them this link to authorise: ${this.authUrl(userId, provider)}`,
      );
    }
    if (res.status === 401) {
      throw new TokenBridgeError(
        `Token for '${userId}' has expired and cannot be refreshed - they need to re-authorise: ` +
          this.authUrl(userId, provider),
      );
    }
    if (!res.ok) {
      throw new TokenBridgeError(`TokenBridge error (${res.status}): ${JSON.stringify(body.error ?? body)}`);
    }

    return body.access_token as string;
  }
}
