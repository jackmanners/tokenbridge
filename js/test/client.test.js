const test = require("node:test");
const assert = require("node:assert/strict");
const { createHmac } = require("node:crypto");
const { TokenBridge, TokenBridgeError } = require("../dist/index.js");

const opts = { url: "https://example.supabase.co/functions/v1/", apiKey: "test-key", envFile: "nonexistent.env" };

test("authUrl is HMAC-signed and shaped correctly", () => {
  const tb = new TokenBridge({ ...opts, provider: "withings" });
  const link = tb.authUrl("p001");
  const u = new URL(link);

  assert.equal(u.origin + u.pathname, "https://example.supabase.co/functions/v1/auth-start");
  assert.equal(u.searchParams.get("provider"), "withings");
  assert.equal(u.searchParams.get("user_id"), "p001");

  const exp = u.searchParams.get("exp");
  const expected = createHmac("sha256", "test-key").update(`withings:p001:${exp}`).digest("hex");
  assert.equal(u.searchParams.get("sig"), expected);
});

test("authUrls batches by user_id", () => {
  const tb = new TokenBridge(opts);
  const links = tb.authUrls(["p001", "p002"]);
  assert.deepEqual(Object.keys(links).sort(), ["p001", "p002"]);
  assert.match(links.p001, /user_id=p001/);
});

test("throws TokenBridgeError when url/apiKey are missing", () => {
  const saved = { url: process.env.TOKENBRIDGE_URL, key: process.env.TOKENBRIDGE_API_KEY };
  delete process.env.TOKENBRIDGE_URL;
  delete process.env.TOKENBRIDGE_API_KEY;
  try {
    assert.throws(() => new TokenBridge({ envFile: "nonexistent.env" }), TokenBridgeError);
  } finally {
    if (saved.url !== undefined) process.env.TOKENBRIDGE_URL = saved.url;
    if (saved.key !== undefined) process.env.TOKENBRIDGE_API_KEY = saved.key;
  }
});
