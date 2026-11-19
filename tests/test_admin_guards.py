"""Even role 1 is limited: admin writes check the role and deactivation live and are rate limited, audit columns are Atom's, the write runner takes one INSERT, UPDATE or DELETE (with a WHERE)."""
import unittest
import config
from function.query_runners import func_postgres_write_sql_check

ADMIN_WRITES = {"blob-container-ops", "blob-delete-url", "blob-container-sas", "clickhouse-query-runner-write", "mssql-query-runner-write", "postgres-query-runner-write", "mongodb-import", "object-create", "object-delete", "object-update", "postgres-import", "postgres-slow-queries-reset", "user-create", "user-delete", "user-update"}


class AdminGuardTests(unittest.TestCase):
    def test_every_admin_write_checks_live_and_is_rate_limited(self):
        for name in sorted(ADMIN_WRITES):
            with self.subTest(route=name):
                cfg = config.config_api[f"/admin/{name}"]
                self.assertEqual(cfg["user_check_role"], {"mode": "realtime", "roles": [1]})
                self.assertEqual(cfg["user_check_deactivated"], {"mode": "realtime"})
                self.assertIn("rate_limit", cfg)
                if "user_check_permission" in cfg: self.assertEqual(cfg["user_check_permission"]["mode"], "realtime")

    def test_a_new_admin_write_route_is_listed_here(self):
        # an /admin route that is not a read must be in ADMIN_WRITES, so it gets the guards above
        reads = {"monitor", "object-read", "object-read-export", "postgres-info", "postgres-schema", "postgres-slow-queries", "postgres-query-runner-read", "postgres-query-runner-read-export", "postgres-query-ai", "mssql-query-runner-read", "mssql-query-runner-read-export", "clickhouse-query-runner-read", "clickhouse-query-runner-read-export", "clickhouse-query-ai", "table-column-groupby", "table-column-distinct", "blob-container-read", "blob-preview-urls", "sync"}
        routes = {path.removeprefix("/admin/") for path in config.config_api if path.startswith("/admin/")}
        self.assertEqual(sorted(routes - reads - ADMIN_WRITES), [])

    def test_audit_columns_are_atoms(self):
        self.assertEqual(config.config_column_audit_blocked, ["created_at", "created_by_id", "updated_at", "updated_by_id", "deleted_at", "deleted_by_id"])

    def test_write_runner_takes_one_insert_update_or_delete(self):
        for sql in ("UPDATE t SET a = 1 WHERE id = 2", "insert into t (a) values (1)", "DELETE FROM t WHERE id = 3;", "update t set note = 'drop table x; truncate' where id = 3"):
            with self.subTest(ok=sql): func_postgres_write_sql_check(sql=sql)
        for sql, message in (("DROP TABLE t", "DROP is not allowed"), ("TRUNCATE t", "TRUNCATE is not allowed"), ("ALTER TABLE t ADD c int", "ALTER is not allowed"), ("CREATE TABLE x (a int)", "CREATE is not allowed"), ("GRANT ALL ON t TO x", "GRANT is not allowed"),
                             ("DO $$ BEGIN DROP TABLE t; END $$", "DO is not allowed"), ("DELETE FROM t", "DELETE needs a WHERE"), ("UPDATE t SET a = 1", "UPDATE needs a WHERE"), ("UPDATE t SET a = 1 WHERE id = 1; DROP TABLE t", "one statement only"),
                             ("INSERT INTO t (a) VALUES (1) RETURNING id", "RETURNING"), ("SELECT 1", "read SQL"), ("update t set a = 'x where'", "UPDATE needs a WHERE"), ("", "SQL required")):
            with self.subTest(refused=sql):
                with self.assertRaisesRegex(Exception, message): func_postgres_write_sql_check(sql=sql)


if __name__ == "__main__":
    unittest.main()
