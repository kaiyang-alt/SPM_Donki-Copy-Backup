-- Read-only snapshot for reconciling docs/architecture/database_schema.md.
-- Run the complete SELECT as postgres in the shared project's SQL Editor.
-- Export the full result as JSON and send it to the developer updating docs.
-- Scope: public application objects, excluding extension-owned routines.
-- No application rows, auth.users, credentials, role passwords or JWTs are read.
-- Review routine bodies/defaults before sharing: custom SQL can contain literals.
-- This is an inspection, not a migration or proof of end-to-end app behavior.
WITH app_relations AS (
  SELECT c.* FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
  WHERE n.nspname='public' AND c.relkind IN ('r','p','v','m')
), app_routines AS (
  SELECT p.* FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace
  WHERE n.nspname='public' AND p.prokind IN ('f','p')
    AND NOT EXISTS (SELECT 1 FROM pg_depend d
      WHERE d.classid='pg_proc'::regclass AND d.objid=p.oid AND d.deptype='e')
), relevant_roles AS (
  SELECT relowner AS oid FROM app_relations
  UNION SELECT proowner FROM app_routines
  UNION SELECT oid FROM pg_roles WHERE rolname IN ('postgres','authenticated','anon','service_role')
)
SELECT jsonb_pretty(jsonb_build_object(
  'snapshot', jsonb_build_object('captured_at',current_timestamp,
    'execution_role',current_user,'server_version',current_setting('server_version'),
    'scope','public application objects; extension routines excluded'),
  'relations', (
    SELECT coalesce(jsonb_agg(jsonb_build_object('name',relname,'kind',relkind,
      'owner',pg_get_userbyid(relowner),'rls_enabled',relrowsecurity,
      'rls_forced',relforcerowsecurity,'acl',relacl::text) ORDER BY relname),'[]'::jsonb)
    FROM app_relations
  ),
  'columns', (
    SELECT coalesce(jsonb_agg(jsonb_build_object('table',c.relname,'position',a.attnum,
      'name',a.attname,'type',format_type(a.atttypid,a.atttypmod),
      'not_null',a.attnotnull,'default',pg_get_expr(d.adbin,d.adrelid),
      'identity',a.attidentity,'generated',a.attgenerated,'acl',a.attacl::text)
      ORDER BY c.relname,a.attnum),'[]'::jsonb)
    FROM app_relations c JOIN pg_attribute a ON a.attrelid=c.oid
    LEFT JOIN pg_attrdef d ON d.adrelid=c.oid AND d.adnum=a.attnum
    WHERE a.attnum>0 AND NOT a.attisdropped
  ),
  'constraints', (
    SELECT coalesce(jsonb_agg(jsonb_build_object('table',c.relname,'name',con.conname,
      'validated',con.convalidated,'definition',pg_get_constraintdef(con.oid,true))
      ORDER BY c.relname,con.conname),'[]'::jsonb)
    FROM pg_constraint con JOIN app_relations c ON c.oid=con.conrelid
  ),
  'indexes', (
    SELECT coalesce(jsonb_agg(jsonb_build_object('table',c.relname,
      'name',i.relname,'valid',x.indisvalid,'definition',pg_get_indexdef(x.indexrelid))
      ORDER BY c.relname,i.relname),'[]'::jsonb)
    FROM pg_index x JOIN app_relations c ON c.oid=x.indrelid
    JOIN pg_class i ON i.oid=x.indexrelid
  ),
  'triggers', (
    SELECT coalesce(jsonb_agg(jsonb_build_object('table',c.relname,'name',t.tgname,
      'enabled',t.tgenabled,'definition',pg_get_triggerdef(t.oid,true),
      'routine',t.tgfoid::regprocedure::text) ORDER BY c.relname,t.tgname),'[]'::jsonb)
    FROM pg_trigger t JOIN app_relations c ON c.oid=t.tgrelid WHERE NOT t.tgisinternal
  ),
  'routines', (
    SELECT coalesce(jsonb_agg(jsonb_build_object('signature',p.oid::regprocedure::text,
      'owner',pg_get_userbyid(p.proowner),'security_definer',p.prosecdef,
      'settings',p.proconfig,'acl',p.proacl::text,
      'definition',pg_get_functiondef(p.oid)) ORDER BY p.oid::regprocedure::text),'[]'::jsonb)
    FROM app_routines p
  ),
  'policies', (
    SELECT coalesce(jsonb_agg(to_jsonb(p) ORDER BY p.tablename,p.policyname),'[]'::jsonb)
    FROM pg_policies p WHERE p.schemaname='public'
  ),
  'views', (
    SELECT coalesce(jsonb_agg(jsonb_build_object('name',c.relname,
      'options',c.reloptions,'definition',pg_get_viewdef(c.oid,true)) ORDER BY c.relname),'[]'::jsonb)
    FROM app_relations c WHERE c.relkind IN ('v','m')
  ),
  'enums', (
    SELECT coalesce(jsonb_agg(jsonb_build_object('type',t.typname,'label',e.enumlabel,
      'position',e.enumsortorder) ORDER BY t.typname,e.enumsortorder),'[]'::jsonb)
    FROM pg_type t JOIN pg_namespace n ON n.oid=t.typnamespace
    JOIN pg_enum e ON e.enumtypid=t.oid WHERE n.nspname='public'
  ),
  'schema_acl', (SELECT nspacl::text FROM pg_namespace WHERE nspname='public'),
  'default_privileges', (
    SELECT coalesce(jsonb_agg(jsonb_build_object('owner',pg_get_userbyid(d.defaclrole),
      'schema',n.nspname,'object_type',d.defaclobjtype,'acl',d.defaclacl::text)
      ORDER BY d.defaclrole,d.defaclnamespace,d.defaclobjtype),'[]'::jsonb)
    FROM pg_default_acl d LEFT JOIN pg_namespace n ON n.oid=d.defaclnamespace
    WHERE d.defaclnamespace=0 OR n.nspname='public'
  ),
  'roles', (
    SELECT coalesce(jsonb_agg(jsonb_build_object('name',r.rolname,
      'inherits',r.rolinherit,'bypass_rls',r.rolbypassrls,'can_login',r.rolcanlogin)
      ORDER BY r.rolname),'[]'::jsonb)
    FROM pg_roles r WHERE r.oid IN (SELECT oid FROM relevant_roles)
  ),
  'role_memberships', (
    SELECT coalesce(jsonb_agg(jsonb_build_object('role',pg_get_userbyid(m.roleid),
      'member',pg_get_userbyid(m.member),'admin_option',m.admin_option,
      'inherit_option',to_jsonb(m)->'inherit_option','set_option',to_jsonb(m)->'set_option')
      ORDER BY m.roleid,m.member),'[]'::jsonb)
    FROM pg_auth_members m WHERE m.roleid IN (SELECT oid FROM relevant_roles)
      OR m.member IN (SELECT oid FROM relevant_roles)
  )
)) AS current_schema_inspection;
