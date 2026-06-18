-- Store the Google Health user ID so we can map webhook notifications back to our user_id
alter table oauth_tokens add column if not exists health_user_id text;
create index if not exists oauth_tokens_health_user_id on oauth_tokens (health_user_id);

-- Lightweight index of which dates we have data for each user + provider + data type.
-- Populated by webhooks. Stores availability metadata only — no actual health values.
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
