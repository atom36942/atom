## Final connection string
```text
postgresql://user_read:123456@127.0.0.1/postgres
```
```sql
DO $$
DECLARE
  s record;
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'user_read') THEN
    CREATE ROLE user_read LOGIN PASSWORD '123456';
  ELSE
    ALTER ROLE user_read WITH LOGIN PASSWORD '123456';
  END IF;
  EXECUTE format('GRANT CONNECT ON DATABASE %I TO user_read', current_database());
  FOR s IN
    SELECT nspname
    FROM pg_namespace
    WHERE nspname NOT LIKE 'pg_%'
      AND nspname <> 'information_schema'
  LOOP
    EXECUTE format('GRANT USAGE ON SCHEMA %I TO user_read', s.nspname);
    EXECUTE format('GRANT SELECT ON ALL TABLES IN SCHEMA %I TO user_read', s.nspname);
    EXECUTE format('GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA %I TO user_read', s.nspname);
    EXECUTE format('ALTER DEFAULT PRIVILEGES IN SCHEMA %I GRANT SELECT ON TABLES TO user_read', s.nspname);
    EXECUTE format('ALTER DEFAULT PRIVILEGES IN SCHEMA %I GRANT USAGE, SELECT ON SEQUENCES TO user_read', s.nspname);
  END LOOP;
END $$;
```
