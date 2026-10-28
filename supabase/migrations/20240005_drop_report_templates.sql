-- Reports moved out of Supabase entirely - rendering now happens locally in
-- the Python package (tokenbridge.reports.generate_report), reading from
-- template files shipped with the package instead of this table. The
-- sleep-report and template-manager edge functions are removed along with it.
drop table if exists report_templates;
