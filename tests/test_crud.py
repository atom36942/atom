"""CRUD contracts with actual builders/serializers and a mocked database."""
import unittest
from function import (
    func_postgres_create, func_postgres_read, func_postgres_update, func_postgres_delete,
    func_postgres_serialize, func_postgres_where_build, func_postgres_relation, func_regex_check,
)
from tests.support import database


class CrudTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.pool, self.conn = database()
        self.schema = {"product": {name: {"datatype": dtype} for name, dtype in
                       [("id", "bigint"), ("name", "text"), ("created_by_id", "bigint"), ("password", "text")]}}
        self.common = dict(client_postgres=self.pool, client_password_hasher=None,
                           func_postgres_serialize=func_postgres_serialize, cache_postgres_schema=self.schema, table="product")
        self.write_args = self.common | dict(client_postgres_conn=None, func_regex_check=func_regex_check, config_column_regex={})

    async def create(self, **changes):
        return await func_postgres_create(**(self.write_args | dict(cache_postgres_buffer={}, buffer_limit=10,
            mode="now", obj_list=[{"name": "item", "created_by_id": 7}]) | changes))

    async def read(self, **changes):
        return await func_postgres_read(**(self.common | dict(func_postgres_where_build=func_postgres_where_build,
            func_postgres_relation=func_postgres_relation, config_sql_read_limit_max=100,
            config_sql_read_relation_fetch_limit_max=100, filter=[], limit=10, page=1,
            order="id desc", column="*", relation=[]) | changes))

    async def update(self, **changes):
        return await func_postgres_update(**(self.write_args | dict(obj_list=[{"id": 3, "name": "new"}], created_by_id=7) | changes))

    async def delete(self, **changes):
        return await func_postgres_delete(**(dict(client_postgres=self.pool, client_postgres_conn=None,
            cache_postgres_schema=self.schema, table="product", ids=[3], created_by_id=7) | changes))

    async def test_create_binds_values_and_ignores_client_supplied_id(self):
        self.conn.fetch.return_value = [{"id": 42}]
        payload = [{"id": 999, "name": "O'Reilly", "created_by_id": 7}]
        self.assertEqual(await self.create(obj_list=payload), [42])
        sql, *values = self.conn.fetch.await_args.args
        self.assertNotIn("O'Reilly", sql)
        self.assertEqual(values, ["O'Reilly", 7])
        self.assertEqual(payload[0]["id"], 999)
        self.assertNotIn('"id"', sql.split("VALUES")[0])

    async def test_create_invalid_fields_and_regex_never_write(self):
        for changes, message in [({"obj_list": []}, "object list required"),
                                 ({"obj_list": [{"missing": 1}]}, "not found"),
                                 ({"config_column_regex": {"name": ["^[0-9]+$", "invalid name"]}}, "invalid name")]:
            with self.subTest(changes=changes), self.assertRaisesRegex(Exception, message):
                await self.create(**changes)
        self.conn.fetch.assert_not_awaited()

    async def test_create_database_failure_exits_transaction_with_error(self):
        self.conn.fetch.side_effect = RuntimeError("database write failed")
        with self.assertRaisesRegex(RuntimeError, "database write failed"):
            await self.create()
        exit_args = self.conn.transaction.return_value.__aexit__.await_args.args
        self.assertIs(exit_args[0], RuntimeError)
        self.pool.acquire.return_value.__aexit__.assert_awaited_once()

    async def test_buffered_create_does_not_write_until_flush(self):
        buffer = {}
        self.assertEqual(await self.create(mode="buffer", cache_postgres_buffer=buffer), "buffered")
        self.conn.fetch.assert_not_awaited()
        self.conn.fetch.return_value = [{"id": 42}]
        self.assertEqual(await self.create(mode="flush", cache_postgres_buffer=buffer), "flushed")
        self.conn.fetch.assert_awaited_once()
        self.assertTrue(all(not values for values in buffer.values()))

    async def test_failed_buffer_flush_retains_pending_rows(self):
        buffer = {}
        await self.create(mode="buffer", cache_postgres_buffer=buffer)
        self.conn.fetch.side_effect = RuntimeError("database unavailable")
        with self.assertRaisesRegex(RuntimeError, "database unavailable"):
            await self.create(mode="flush", cache_postgres_buffer=buffer)
        self.assertEqual(sum(map(len, buffer.values())), 1)

    async def test_read_binds_filters_and_pagination_and_removes_password(self):
        self.conn.fetch.return_value = [{"id": 3, "name": "item", "password": "private"}]
        result = await self.read(filter=[{"created_by_id": "eq,7"}], limit=10, page=2)
        sql, *values = self.conn.fetch.await_args.args
        self.assertEqual(values, [7, 11, 10])
        self.assertIn('"created_by_id" = $1', sql)
        self.assertIn("LIMIT $2 OFFSET $3", sql)
        self.assertEqual(result, [{"id": 3, "name": "item"}])

    async def test_read_invalid_pagination_and_restricted_column_never_query(self):
        for changes in ({"limit": 0}, {"page": 0}, {"limit": 101}, {"column": "password"}):
            with self.subTest(changes=changes), self.assertRaises(Exception):
                await self.read(**changes)
        self.conn.fetch.assert_not_awaited()

    async def test_filter_values_stay_outside_sql(self):
        value = "x' OR 1=1 --"
        sql, values = await func_postgres_where_build(**self.common, filter=[{"name": "eq," + value}])
        self.assertNotIn(value, sql)
        self.assertEqual(values, [value])

    async def test_filter_rejects_unknown_and_restricted_columns(self):
        for column in ("missing", "password"):
            with self.subTest(column=column), self.assertRaises(Exception):
                await func_postgres_where_build(**self.common, filter=[{column: "eq,hello"}])

    async def test_update_includes_owner_in_query_and_returns_updated_ids(self):
        self.conn.fetch.return_value = [{"id": 3}]
        self.assertEqual(await self.update(), [3])
        sql, *values = self.conn.fetch.await_args.args
        self.assertIn('AND "created_by_id"=$4', sql)
        self.assertEqual(values, [3, "new", 3, 7])
        self.conn.fetch.return_value = []
        self.assertEqual(await self.update(), [])

    async def test_update_invalid_batches_never_write(self):
        for objects in ([{"name": "no id"}], [{"id": 3}], [{"id": 3, "name": "a"}, {"id": 4, "created_by_id": 7}]):
            with self.subTest(objects=objects), self.assertRaises(Exception):
                await self.update(obj_list=objects)
        self.conn.fetch.assert_not_awaited()

    async def test_delete_binds_ids_and_owner_and_reports_zero_matches(self):
        self.conn.fetchval.return_value = 1
        self.assertEqual(await self.delete(), 1)
        sql, *values = self.conn.fetchval.await_args.args
        self.assertIn('AND "created_by_id"=$2::bigint', sql)
        self.assertEqual(values, [[3], 7])
        self.conn.fetchval.return_value = 0
        self.assertEqual(await self.delete(), 0)

    async def test_crud_rejects_invalid_table_identifier_before_query(self):
        for operation in (self.create, self.read, self.update, self.delete):
            with self.subTest(operation=operation.__name__), self.assertRaisesRegex(Exception, "invalid identifier"):
                await operation(table='product"; DROP TABLE users; --')
        self.conn.fetch.assert_not_awaited()
        self.conn.fetchval.assert_not_awaited()
