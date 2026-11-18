"""pgweb's guard against unbounded writes in the query runner."""
import unittest

from function.pgweb import func_pgweb_write_check


class PgwebWriteCheckTests(unittest.TestCase):
    def refused(self, sql):
        with self.assertRaisesRegex(Exception, "unbounded_write"): func_pgweb_write_check(sql=sql)

    def test_bounded_and_read_statements_pass(self):
        for sql in ("SELECT 1", "UPDATE t SET a = 1 WHERE id = 2", "DELETE FROM t WHERE id = 2", "EXPLAIN DELETE FROM t", "WITH x AS (SELECT 1) SELECT * FROM x"):
            func_pgweb_write_check(sql=sql)

    def test_unbounded_writes_are_refused_however_written(self):
        for sql in ("DELETE FROM t", "update t set a = 1", "TRUNCATE t", "DROP TABLE t", "-- note\nDELETE FROM t", "/* x */ delete from t",
                    "SELECT 1; DELETE FROM t", "EXPLAIN ANALYZE DELETE FROM t", "EXPLAIN (ANALYZE, BUFFERS) UPDATE t SET a = 1",
                    "WITH x AS (DELETE FROM t RETURNING 1) SELECT 1"):
            self.refused(sql)

    def test_confirmed_or_read_only_skips_the_guard_but_not_empty_sql(self):
        func_pgweb_write_check(sql="DELETE FROM t", is_confirmed=True)
        func_pgweb_write_check(sql="DELETE FROM t", is_read_only=True)
        with self.assertRaisesRegex(Exception, "sql is required"): func_pgweb_write_check(sql="  ")
