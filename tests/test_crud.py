"""CRUD contracts with actual builders/serializers and a mocked database."""
import asyncio
import csv
import io
import pathlib
import unittest
from datetime import date
from unittest.mock import AsyncMock
from unittest.mock import patch
import orjson
from function import func_csv_cell
from function import func_postgres_create
from function import func_postgres_read
from function import func_csv_stream
from function import func_export_limit
from function import func_postgres_update
from function import func_postgres_delete
from function import func_postgres_where_build
from tests.support import database


class CrudTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.pool, self.conn = database()
        self.schema = {"product": {name: {"datatype": dtype, "is_nullable": "NO" if name == "id" else "YES"} for name, dtype in
                       [("id", "bigint"), ("name", "text"), ("created_by_id", "bigint"), ("password", "text")]}}
        self.common = dict(client_postgres=self.pool, client_password_hasher=None, cache_postgres_schema=self.schema, table="product")
        self.write_args = self.common | dict(client_postgres_conn=None, config_column_regex={})

    async def create(self, **changes):
        return await func_postgres_create(**(self.write_args | dict(buffer_postgres={}, buffer_limit=10,
            mode="now", obj_list=[{"name": "item", "created_by_id": 7}]) | changes))

    async def read(self, **changes):
        return await func_postgres_read(**(self.common | dict( config_sql_read_limit_max=100,
            config_sql_read_relation_fetch_limit_max=100, filter=[], limit=10,
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

    async def test_create_of_one_statement_sends_no_transaction(self):
        self.conn.fetch.return_value = [{"id": i} for i in range(1, 11)]
        await self.create(obj_list=[{"name": f"n{i}", "created_by_id": 7} for i in range(10)])
        self.conn.transaction.assert_not_called()    # one INSERT is all-or-nothing by itself: no BEGIN, SAVEPOINT or COMMIT round trips
        self.assertEqual(self.conn.fetch.await_count, 1)

    async def test_create_database_failure_raises_and_releases_the_connection(self):
        self.conn.fetch.side_effect = RuntimeError("database write failed")
        with self.assertRaisesRegex(RuntimeError, "database write failed"):
            await self.create()
        self.pool.acquire.return_value.__aexit__.assert_awaited_once()

    async def test_create_over_one_statement_runs_in_one_transaction_that_rolls_back(self):
        self.conn.fetch.side_effect = [[{"id": 1}] * 5000, RuntimeError("database write failed")]
        with self.assertRaisesRegex(RuntimeError, "database write failed"):
            await self.create(obj_list=[{"name": "n", "created_by_id": 7} for _ in range(5001)])
        self.conn.transaction.assert_called_once()
        self.assertIs(self.conn.transaction.return_value.__aexit__.await_args.args[0], RuntimeError)

    async def test_buffered_create_does_not_write_until_flush(self):
        buffer = {}
        self.assertEqual(await self.create(mode="buffer", buffer_postgres=buffer), "buffered")
        self.conn.fetch.assert_not_awaited()
        self.conn.fetch.return_value = [{"id": 42}]
        self.assertEqual(await self.create(mode="flush", buffer_postgres=buffer), "flushed")
        self.conn.fetch.assert_awaited_once()
        self.assertTrue(all(not values for values in buffer.values()))

    async def test_full_buffer_rejects_user_rows_with_503_and_keeps_pending(self):
        buffer = {}
        for i in range(5):
            await self.create(mode="buffer", buffer_postgres=buffer, buffer_rows_max=5, obj_list=[{"name": f"row-{i}", "created_by_id": 7}])
        with self.assertRaisesRegex(Exception, "buffer full, retry later") as raised:
            await self.create(mode="buffer", buffer_postgres=buffer, buffer_rows_max=5, obj_list=[{"name": "row-5", "created_by_id": 7}])
        self.assertEqual(raised.exception.status_code, 503)
        self.assertEqual([r["name"] for rows in buffer.values() for r in rows], [f"row-{i}" for i in range(5)])
        self.conn.fetch.assert_not_awaited()

    async def test_full_log_buffer_drops_the_oldest_rows_and_counts_them(self):
        buffer, runtime_error_count = {}, {}
        for i in range(8):
            await self.create(mode="buffer", buffer_postgres=buffer, buffer_rows_max=5, buffer_full_mode="drop_oldest", runtime_error_count=runtime_error_count, obj_list=[{"name": f"row-{i}", "created_by_id": 7}])
        self.assertEqual([r["name"] for rows in buffer.values() for r in rows], [f"row-{i}" for i in range(3, 8)])
        self.assertEqual(runtime_error_count, {"buffer_dropped": 3})

    async def test_buffer_without_cap_keeps_every_row(self):
        buffer = {}
        for i in range(8):
            await self.create(mode="buffer", buffer_postgres=buffer, obj_list=[{"name": f"row-{i}", "created_by_id": 7}])
        self.assertEqual(sum(len(rows) for rows in buffer.values()), 8)

    async def test_failed_buffer_flush_retains_pending_rows(self):
        buffer = {}
        await self.create(mode="buffer", buffer_postgres=buffer)
        self.conn.fetch.side_effect = RuntimeError("database unavailable")
        with self.assertRaisesRegex(RuntimeError, "database unavailable"):
            await self.create(mode="flush", buffer_postgres=buffer)
        self.assertEqual(sum(map(len, buffer.values())), 1)

    async def test_concurrent_buffered_writers_insert_every_row_exactly_once(self):
        buffer, inserted = {}, []
        async def fetch(sql, *args):
            await asyncio.sleep(0.005)    # other requests keep buffering while this insert waits
            inserted.extend([r["name"] for r in orjson.loads(args[0])] if "jsonb_to_recordset" in sql else [args[0]])
            return []
        self.conn.fetch.side_effect = fetch
        await asyncio.gather(*(self.create(mode="buffer", buffer_postgres=buffer, obj_list=[{"name": f"row-{i}", "created_by_id": 7}]) for i in range(300)))
        await self.create(mode="flush", buffer_postgres=buffer)
        self.assertEqual(sorted(inserted), sorted(f"row-{i}" for i in range(300)))

    async def test_failed_buffered_insert_puts_rows_back_ahead_of_new_ones(self):
        buffer = {}
        self.conn.fetch.side_effect = RuntimeError("database unavailable")
        await self.create(mode="buffer", buffer_postgres=buffer, buffer_limit=2, obj_list=[{"name": "row-0", "created_by_id": 7}])
        with self.assertRaisesRegex(RuntimeError, "database unavailable"):
            await self.create(mode="buffer", buffer_postgres=buffer, buffer_limit=2, obj_list=[{"name": "row-1", "created_by_id": 7}])
        with self.assertRaisesRegex(RuntimeError, "database unavailable"):
            await self.create(mode="buffer", buffer_postgres=buffer, buffer_limit=2, obj_list=[{"name": "row-2", "created_by_id": 7}])
        self.assertEqual([r["name"] for rows in buffer.values() for r in rows], ["row-0", "row-1", "row-2"])

    async def test_trusted_create_skips_value_checks_but_not_identifier_checks(self):
        regex = {"name": ["^[0-9]+$", "invalid name"]}
        self.assertEqual(await self.create(mode="buffer", is_trusted=True, config_column_regex=regex, obj_list=[{"name": "abc", "extra": 1}]), "buffered")
        for changes, message in [({"obj_list": [{'bad"col': 1}]}, "invalid identifier"), ({"table": "bad;table"}, "invalid identifier"), ({"table": "spatial_ref_sys"}, "system table protected")]:
            with self.subTest(changes=changes), self.assertRaisesRegex(Exception, message):
                await self.create(mode="now", is_trusted=True, **changes)

    def test_no_route_passes_is_trusted(self):
        root = pathlib.Path(__file__).resolve().parent.parent
        for folder in ("router", "router_extend"):
            for path in (root / folder).glob("*.py"):
                self.assertNotIn("is_trusted", path.read_text(), f"{path.name}: request data must never skip validation")

    async def test_csv_stream_writes_bom_header_and_rows_as_stored_in_chunks(self):
        async def rows():
            for i in range(10000): yield (i, f"=n{i}")
        chunks = [chunk async for chunk in func_csv_stream(rows=rows(), columns=["id", "name"])]
        self.assertTrue(chunks[0].startswith("\ufeffid,name"))
        self.assertGreater(len(chunks), 2, "sent in pieces, not one string")
        lines = list(csv.reader(io.StringIO("".join(chunks)[1:])))
        self.assertEqual((lines[1], lines[-1], len(lines)), (["0", "'=n0"], ["9999", "'=n9999"], 10001))    # values as stored; only formula text is guarded

    def test_export_limit_is_the_users_choice_up_to_the_setting(self):
        self.assertEqual(func_export_limit(config_export_limit=1000000, limit=None), 1000000)
        self.assertEqual(func_export_limit(config_export_limit=1000000, limit=500), 500)
        for limit in (0, 1000001):
            with self.subTest(limit=limit), self.assertRaises(Exception) as caught: func_export_limit(config_export_limit=1000000, limit=limit)
            self.assertEqual((caught.exception.status_code, str(caught.exception)), (400, "Rows must be between 1 and 1,000,000."))

    def test_csv_cells_are_readable_and_formula_safe(self):
        self.assertEqual([func_csv_cell(v) for v in (None, 5, -5, "plain", "-1+1", "=SUM(A1)", "@x", {"a": 1}, [1, 2], date(2026, 1, 2))],
                         ["", 5, -5, "plain", "'-1+1", "'=SUM(A1)", "'@x", '{"a":1}', "[1,2]", "2026-01-02"])

    async def test_read_binds_filters_and_limit_and_removes_password(self):
        self.conn.fetch.return_value = [{"id": 3, "name": "item", "password": "private"}]
        result = await self.read(filter=[{"created_by_id": "eq,7"}], limit=10)
        sql, *values = self.conn.fetch.await_args.args
        self.assertEqual(values, [7, 11])
        self.assertIn('"created_by_id" = $1', sql)
        self.assertIn('ORDER BY "id" DESC LIMIT $2', sql)
        self.assertNotIn("OFFSET", sql)
        self.assertEqual(result, {"obj_list": [{"id": 3, "name": "item"}], "after": None})

    async def test_read_returns_the_cursor_of_the_next_page_from_the_extra_row(self):
        self.conn.fetch.return_value = [{"id": 9, "name": "c"}, {"id": 8, "name": "b"}, {"id": 7, "name": "a"}]
        result = await self.read(limit=2)
        self.assertEqual(result, {"obj_list": [{"id": 9, "name": "c"}, {"id": 8, "name": "b"}], "after": '["8"]'})
        result = await self.read(limit=2, order="name asc", column="name")
        self.assertEqual(result, {"obj_list": [{"name": "c"}, {"name": "b"}], "after": '["b","8"]'})    # id is read for the cursor, then removed
        self.assertIn('SELECT "name","id" FROM', self.conn.fetch.await_args.args[0])

    async def test_read_after_continues_from_that_row_without_offset(self):
        self.conn.fetch.return_value = []
        for order, condition, sort in (("id desc", '"id" < $2::text::bigint', '"id" DESC'), ("id asc", '"id" > $2::text::bigint', '"id" ASC'),
                                       ("name desc", '("name" <= $2::text::text AND ("name" < $2::text::text OR "id" < $3::text::bigint))', '"name" DESC, "id" DESC')):
            with self.subTest(order=order):
                after = '["50"]' if order.startswith("id") else '["m","50"]'
                await self.read(filter=[{"created_by_id": "eq,7"}], order=order, after=after)
                sql, *values = self.conn.fetch.await_args.args
                self.assertIn(f'WHERE ("created_by_id" = $1) AND {condition} ORDER BY {sort} LIMIT', sql)
                self.assertEqual(values, [7, *(["50"] if order.startswith("id") else ["m", "50"]), 11])
                self.assertNotIn("OFFSET", sql)

    async def test_read_refuses_a_cursor_of_another_list_or_order(self):
        for changes in ({"after": '["50"]', "order": "name asc"}, {"after": "50"}, {"after": "not json"}, {"after": '[true]'}, {"order": "password desc"}, {"order": "missing asc"}):
            with self.subTest(changes=changes), self.assertRaisesRegex(Exception, "start from the first page|restricted from reading|not found"):
                await self.read(**changes)
        self.conn.fetch.assert_not_awaited()

    async def test_read_invalid_limit_and_restricted_column_never_query(self):
        for changes in ({"limit": 0}, {"limit": 101}, {"column": "password"}):
            with self.subTest(changes=changes), self.assertRaisesRegex(Exception, "restricted from reading|exceeds maximum allowed|must be greater than 0"):
                await self.read(**changes)
        self.conn.fetch.assert_not_awaited()

    async def test_filter_values_stay_outside_sql(self):
        value = "x' OR 1=1 --"
        sql, values = await func_postgres_where_build(**self.common, filter=[{"name": "eq," + value}])
        self.assertNotIn(value, sql)
        self.assertEqual(values, [value])

    async def test_filter_rejects_unknown_and_restricted_columns(self):
        for column in ("missing", "password"):
            with self.subTest(column=column), self.assertRaisesRegex(Exception, "filtering on column 'password' is blocked|invalid filter column"):
                await func_postgres_where_build(**self.common, filter=[{column: "eq,hello"}])

    async def test_update_includes_owner_in_query_and_returns_updated_ids(self):
        self.conn.fetch.return_value = [{"id": 3}]
        self.assertEqual(await self.update(), [3])
        sql, *values = self.conn.fetch.await_args.args
        self.assertIn('FROM unnest($1::bigint[], $2::text[]) AS v("id", "name") WHERE t."id" = v."id" AND t."created_by_id" = $3', sql)
        self.assertEqual(values, [[3], ["new"], 7])
        self.conn.fetch.return_value = []
        self.assertEqual(await self.update(), [])

    async def test_update_sends_each_column_as_one_array_and_a_repeated_id_keeps_its_first_values(self):
        self.conn.fetch.return_value = []
        await self.update(obj_list=[{"id": 3, "name": "a"}, {"id": 4, "name": None}, {"id": 3, "name": "later"}], created_by_id=None)
        sql, *values = self.conn.fetch.await_args.args
        self.assertEqual(values, [[3, 4], ["a", None]])
        self.assertNotIn("created_by_id", sql)
        self.assertEqual(self.conn.fetch.await_count, 1)

    async def test_update_of_json_or_unknown_types_keeps_case(self):
        for datatype in ("jsonb", "text[]", "geography(Point,4326)"):
            schema = {"product": self.schema["product"] | {"name": {"datatype": datatype}}}
            self.conn.fetch.return_value = []
            with self.subTest(datatype=datatype), patch("function.postgres_crud.func_postgres_serialize", new=AsyncMock(side_effect=lambda **kwargs: kwargs["obj_list"])):
                await self.update(cache_postgres_schema=schema)
                sql, *values = self.conn.fetch.await_args.args
                self.assertIn('"name" = CASE WHEN "id"=$1::bigint THEN $2', sql)
                self.assertIn('AND "created_by_id"=$4', sql)
                self.assertEqual(values, [3, "new", 3, 7])

    async def test_update_and_delete_of_one_statement_send_no_transaction(self):
        self.conn.fetch.return_value = [{"id": 3}]
        await self.update(obj_list=[{"id": i, "name": "n"} for i in range(1, 1001)])
        self.conn.fetchval.return_value = 2
        await self.delete(ids=list(range(1, 5001)))
        self.conn.transaction.assert_not_called()    # one UPDATE and one DELETE are all-or-nothing by themselves
        self.assertEqual((self.conn.fetch.await_count, self.conn.fetchval.await_count), (1, 1))

    async def test_update_and_delete_over_one_statement_share_one_transaction(self):
        self.conn.fetch.return_value = []
        await self.update(obj_list=[{"id": i, "name": "n"} for i in range(1, 5002)])
        self.conn.fetchval.return_value = 0
        await self.delete(ids=list(range(1, 5002)))
        self.assertEqual(self.conn.transaction.call_count, 2)
        self.assertEqual((self.conn.fetch.await_count, self.conn.fetchval.await_count), (2, 2))

    async def test_update_invalid_batches_never_write(self):
        for objects in ([{"name": "no id"}], [{"id": 3}], [{"id": 3, "name": "a"}, {"id": 4, "created_by_id": 7}]):
            with self.subTest(objects=objects), self.assertRaisesRegex(Exception, "missing required field: 'id'|object keys mismatch|update field required"):
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
