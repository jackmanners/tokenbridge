-- Lock down direct PostgREST access. All real access to these tables goes
-- through service-role edge functions, which bypass RLS entirely - so
-- enabling RLS with zero policies denies anon/authenticated clients while
-- changing nothing for the app.
alter table oauth_states      enable row level security;
alter table oauth_tokens      enable row level security;
alter table data_availability enable row level security;
alter table report_templates  enable row level security;
