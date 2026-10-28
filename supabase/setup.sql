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

-- Store the Google Health user ID so we can map webhook notifications back to our user_id
alter table oauth_tokens add column if not exists health_user_id text;
create index if not exists oauth_tokens_health_user_id on oauth_tokens (health_user_id);

-- Lightweight index of which dates we have data for each user + provider + data type.
-- Populated by webhooks. Stores availability metadata only - no actual health values.
create table data_availability (
  user_id       text not null,
  provider      text not null,
  data_type     text not null,
  data_date     date not null,
  operation     text not null default 'UPSERT', -- UPSERT or DELETE
  updated_at    timestamptz default now(),
  primary key (user_id, provider, data_type, data_date)
);

create or replace function set_data_availability_updated_at()
returns trigger language plpgsql as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

create trigger data_availability_updated_at
  before update on data_availability
  for each row execute function set_data_availability_updated_at();

-- Lock down direct PostgREST access. All real access to these tables goes
-- through service-role edge functions, which bypass RLS entirely - so
-- enabling RLS with zero policies denies anon/authenticated clients while
-- changing nothing for the app.
alter table oauth_states      enable row level security;
alter table oauth_tokens      enable row level security;
alter table data_availability enable row level security;

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
