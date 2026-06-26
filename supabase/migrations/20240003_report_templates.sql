create table report_templates (
  name        text primary key,
  description text,
  metadata    jsonb not null default '{}',
  html        text not null,
  created_at  timestamptz default now(),
  updated_at  timestamptz default now()
);
