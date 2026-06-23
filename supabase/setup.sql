-- TokenBridge - database setup
-- Paste this entire file into the Supabase SQL Editor and click Run.

-- Short-lived state records for in-flight OAuth flows (CSRF protection + PKCE)
create table oauth_states (
  id            uuid primary key default gen_random_uuid(),
  state         text unique not null,
  provider      text not null,
  user_id       text not null,
  code_verifier text,
  created_at    timestamptz default now(),
  expires_at    timestamptz default now() + interval '10 minutes'
);

-- Stored tokens, one row per (user, provider)
create table oauth_tokens (
  id                uuid primary key default gen_random_uuid(),
  user_id           text not null,
  provider          text not null,
  access_token      text not null,
  refresh_token     text,
  expires_at        timestamptz,
  scopes            text[],
  provider_data     jsonb default '{}',   -- provider-specific metadata (e.g. Withings userid)
  last_refreshed_at timestamptz,          -- tracks proactive keepalive; null = never refreshed
  raw               jsonb,
  created_at        timestamptz default now(),
  updated_at        timestamptz default now(),
  unique (user_id, provider)
);

create or replace function set_updated_at()
returns trigger language plpgsql as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

create trigger oauth_tokens_updated_at
  before update on oauth_tokens
  for each row execute function set_updated_at();

-- Clean up expired state rows
create or replace function cleanup_oauth_states()
returns void language sql as $$
  delete from oauth_states where expires_at < now();
$$;

-- Schedule cleanup every 10 minutes via pg_cron
create extension if not exists pg_cron;
select cron.schedule(
  'cleanup-oauth-states',
  '*/10 * * * *',
  'select cleanup_oauth_states()'
);
