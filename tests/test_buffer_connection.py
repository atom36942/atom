"""Buffered creates on any database: rows keep their database, each flush writes only its own database's rows, conflict and RETURNING rules."""
import unittest
from types import SimpleNamespace
import asyncio
from function import func_postgres_buffer_flush_all
from function import func_postgres_buffer_flush_interval
from function import func_postgres_buffer_key
from function import func_postgres_buffer_key_read
from function import func_postgres_create
from function import func_monitor_background
from tests.support import database

SCHEMA = {"product": {name: {"datatype": dtype} for name, dtype in [("id", "bigint"), ("name", "text"), ("created_by_id", "bigint")]},
          "reading": {name: {"datatype": dtype} for name, dtype in [("time", "timestamp with time zone"), ("device", "text"), ("value", "double precision")]}}


class BufferConnectionTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.master_pool, self.master_conn = database()
        self.other_pool, self.other_conn = database()

    async def create(self, **changes):
        args = dict(client_postgres=self.master_pool, client_postgres_conn=None, client_password_hasher=None, cache_postgres_schema=SCHEMA, buffer_postgres={}, column_regex={}, buffer_limit=10, mode="now", table="product", obj_list=[{"name": "item", "created_by_id": 7}])
        return await func_postgres_create(**(args | changes))

    def test_buffer_key_round_trip(self):
        key = func_postgres_buffer_key(connection="telemetry", table="reading", columns=["value", "device"], on_conflict="nothing")
        self.assertEqual(key, "telemetry|reading|device,value|nothing")
        self.assertEqual(func_postgres_buffer_key_read(key=key), {"connection": "telemetry", "table": "reading", "on_conflict": "nothing"})
        self.assertIsNone(func_postgres_buffer_key_read(key=func_postgres_buffer_key(connection="master", table="product", columns=["name"], on_conflict=None))["on_conflict"])

    async def test_buffered_rows_keep_their_database_and_flush_only_through_it(self):
        buffer = {}
        await self.create(mode="buffer", buffer_postgres=buffer)
        await self.create(mode="buffer", buffer_postgres=buffer, connection="telemetry", table="reading", obj_list=[{"device": "a1", "value": 1.5}])
        self.assertEqual(sorted(func_postgres_buffer_key_read(key=key)["connection"] for key in buffer), ["master", "telemetry"])
        self.assertEqual(await self.create(mode="flush", buffer_postgres=buffer, client_postgres=self.other_pool, connection="telemetry"), "flushed")
        self.other_conn.fetch.assert_awaited_once()
        self.assertIn('INSERT INTO "reading"', self.other_conn.fetch.await_args.args[0])
        self.master_conn.fetch.assert_not_awaited()
        self.assertEqual([func_postgres_buffer_key_read(key=key)["connection"] for key in buffer], ["master"])    # master's rows wait for master's flush

    async def test_insert_without_id_column_has_no_returning(self):
        self.assertEqual(await self.create(table="reading", obj_list=[{"device": "a1", "value": 1.5}]), "created")
        self.assertNotIn("RETURNING", self.master_conn.fetch.await_args.args[0])
        self.master_conn.fetch.return_value = [{"id": 5}]
        self.assertEqual(await self.create(), [5])
        self.assertIn("RETURNING id", self.master_conn.fetch.await_args.args[0])

    async def test_on_conflict_nothing_skips_duplicates_in_single_bulk_and_buffered_inserts(self):
        await self.create(table="reading", obj_list=[{"device": "a1", "value": 1.5}], on_conflict="nothing")
        self.assertIn("ON CONFLICT DO NOTHING", self.master_conn.fetch.await_args.args[0])
        await self.create(table="reading", obj_list=[{"device": "a1", "value": 1.5}, {"device": "a2", "value": 2.5}], on_conflict="nothing")
        self.assertIn("ON CONFLICT DO NOTHING", self.master_conn.fetch.await_args.args[0])
        buffer = {}
        await self.create(mode="buffer", buffer_postgres=buffer, table="reading", obj_list=[{"device": "a1", "value": 1.5}], on_conflict="nothing")
        await self.create(mode="buffer", buffer_postgres=buffer, table="reading", obj_list=[{"device": "a1", "value": 1.5}])
        self.assertEqual(len(buffer), 2, "rows with and without the conflict rule are never inserted together")
        self.master_conn.fetch.reset_mock()
        await self.create(mode="flush", buffer_postgres=buffer)
        self.assertEqual(sorted("ON CONFLICT DO NOTHING" in call.args[0] for call in self.master_conn.fetch.await_args_list), [False, True])

    async def test_invalid_on_conflict_and_connection_are_refused(self):
        for changes, message in [({"on_conflict": "update"}, "invalid on_conflict"), ({"connection": "bad name"}, "invalid connection")]:
            with self.subTest(changes=changes), self.assertRaisesRegex(Exception, message): await self.create(**changes)

    async def test_failed_key_keeps_its_rows_and_the_other_keys_are_still_flushed(self):
        buffer = {}
        await self.create(mode="buffer", buffer_postgres=buffer)
        await self.create(mode="buffer", buffer_postgres=buffer, table="reading", obj_list=[{"device": "a1", "value": 1.5}])
        async def fetch(sql, *args):
            if '"product"' in sql: raise RuntimeError("product insert failed")
            return []
        self.master_conn.fetch.side_effect = fetch
        with self.assertRaisesRegex(RuntimeError, "product insert failed"): await self.create(mode="flush", buffer_postgres=buffer)
        self.assertEqual([func_postgres_buffer_key_read(key=key)["table"] for key in buffer], ["product"])


class BufferFlushAllTests(unittest.IsolatedAsyncioTestCase):
    def app_state(self, pools, **settings):
        state = SimpleNamespace(client_postgres_dict=pools, cache_postgres_schema_dict=dict.fromkeys(pools, SCHEMA), buffer_postgres_create={}, buffer_postgres_log_api={},
                                runtime_lock_postgres_buffer_flush=asyncio.Lock(), runtime_error_count={}, config_postgres_buffer_flush_auto_sec=60,
                                func_postgres_create=func_postgres_create, func_postgres_buffer_key_read=func_postgres_buffer_key_read, func_postgres_buffer_flush_all=func_postgres_buffer_flush_all)
        for key, value in settings.items(): setattr(state, key, value)
        return state

    async def buffer(self, state, connection, table="product", obj_list=None):
        await func_postgres_create(client_postgres=state.client_postgres_dict.get(connection) or object(), client_postgres_conn=None, client_password_hasher=None, cache_postgres_schema=SCHEMA, buffer_postgres=state.buffer_postgres_create, column_regex={}, buffer_limit=10, mode="buffer", table=table, obj_list=obj_list or [{"name": "item", "created_by_id": 7}], connection=connection)

    async def test_each_database_is_flushed_through_its_own_pool(self):
        (master_pool, master_conn), (other_pool, other_conn) = database(), database()
        state = self.app_state({"master": master_pool, "telemetry": other_pool})
        await self.buffer(state, "master")
        await self.buffer(state, "telemetry", table="reading", obj_list=[{"device": "a1", "value": 1.5}])
        await func_postgres_buffer_flush_all(app_state=state)
        self.assertIn('"product"', master_conn.fetch.await_args.args[0])
        self.assertIn('"reading"', other_conn.fetch.await_args.args[0])
        self.assertEqual(state.buffer_postgres_create, {})

    async def test_connections_limits_the_flush(self):
        (master_pool, master_conn), (other_pool, other_conn) = database(), database()
        state = self.app_state({"master": master_pool, "telemetry": other_pool})
        await self.buffer(state, "master")
        await self.buffer(state, "telemetry", table="reading", obj_list=[{"device": "a1", "value": 1.5}])
        await func_postgres_buffer_flush_all(app_state=state, connections={"telemetry"})
        master_conn.fetch.assert_not_awaited()
        other_conn.fetch.assert_awaited_once()

    async def test_database_without_pool_keeps_rows_counts_error_and_others_still_flush(self):
        (master_pool, master_conn) = database()
        state = self.app_state({"master": master_pool})
        await self.buffer(state, "gone", table="reading", obj_list=[{"device": "a1", "value": 1.5}])
        await self.buffer(state, "master")
        await func_postgres_buffer_flush_all(app_state=state)
        master_conn.fetch.assert_awaited_once()
        self.assertEqual([func_postgres_buffer_key_read(key=key)["connection"] for key in state.buffer_postgres_create], ["gone"])
        self.assertEqual(state.runtime_error_count, {"buffer_flush": 1})

    async def test_log_buffer_is_flushed_to_its_own_database(self):
        (master_pool, master_conn), (log_pool, log_conn) = database(), database()
        state = self.app_state({"master": master_pool, "logs": log_pool})
        await func_postgres_create(client_postgres=log_pool, client_postgres_conn=None, client_password_hasher=None, cache_postgres_schema=SCHEMA, buffer_postgres=state.buffer_postgres_log_api, column_regex={}, buffer_limit=10, mode="buffer", table="product", obj_list=[{"name": "log"}], is_trusted=True, connection="logs")
        await func_postgres_buffer_flush_all(app_state=state)
        log_conn.fetch.assert_awaited_once()
        master_conn.fetch.assert_not_awaited()

    def test_flush_interval_per_database(self):
        state = self.app_state({"master": None, "telemetry": None}, config_postgres_buffer_flush_auto_sec_telemetry=2)
        self.assertEqual(func_postgres_buffer_flush_interval(app_state=state, connection="telemetry"), 2)
        self.assertEqual(func_postgres_buffer_flush_interval(app_state=state, connection="master"), 60)

    async def test_monitor_lists_each_buffer_with_its_database(self):
        state = self.app_state({"master": database()[0]})
        await self.buffer(state, "telemetry", table="reading", obj_list=[{"device": "a1", "value": 1.5}])
        report = func_monitor_background(app_state=state)
        self.assertEqual([(b["buffer"], b["connection"], b["table"], b["rows"]) for b in report["buffers"]], [("create", "telemetry", "reading", 1)])


if __name__ == "__main__":
    unittest.main()
