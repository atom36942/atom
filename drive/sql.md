## Create Read Only User
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

## Index Tracker
```sql
SELECT
t.relname AS table_name,
a.attname AS column_name,
format_type(a.atttypid, a.atttypmod) AS data_type,
COUNT(DISTINCT ix.indexrelid) FILTER (WHERE am.amname='btree') AS btree_cnt,
COUNT(DISTINCT ix.indexrelid) FILTER (WHERE am.amname='gin') AS gin_cnt,
COUNT(DISTINCT ix.indexrelid) FILTER (WHERE am.amname='gist') AS gist_cnt,
COUNT(DISTINCT ix.indexrelid) FILTER (WHERE am.amname='brin') AS brin_cnt,
COUNT(DISTINCT ix.indexrelid) FILTER (WHERE am.amname='hash') AS hash_cnt,
COUNT(DISTINCT ix.indexrelid) FILTER (WHERE am.amname='spgist') AS spgist_cnt,
COUNT(DISTINCT ix.indexrelid) AS total_index_cnt,
COUNT(DISTINCT ix.indexrelid) FILTER (WHERE a.attnum = ix.indkey[0]) AS usable_index_cnt
FROM pg_class t
JOIN pg_namespace n ON n.oid=t.relnamespace
JOIN pg_attribute a ON a.attrelid=t.oid AND a.attnum>0 AND NOT a.attisdropped
LEFT JOIN pg_index ix ON ix.indrelid=t.oid AND a.attnum=ANY(ix.indkey)
LEFT JOIN pg_class i ON i.oid=ix.indexrelid
LEFT JOIN pg_am am ON am.oid=i.relam
WHERE t.relkind='r' AND n.nspname='public'
GROUP BY t.relname,a.attname,a.atttypid,a.atttypmod
ORDER BY t.relname,a.attname;
```
