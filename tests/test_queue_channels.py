"""Queue channels: the routes send on names func_consumer_channels knows, and each consumer script listens through its own broker."""
import re
import unittest
from pathlib import Path
from unittest.mock import AsyncMock
from unittest.mock import patch

from function import func_consumer_channels
from function import func_consumer_run
from function import func_consumer_object_update

ROOT = Path(__file__).resolve().parent.parent


class QueueChannelTests(unittest.TestCase):
    def test_every_channel_a_route_sends_on_has_a_consumer(self):
        sent = set(re.findall(r'channel="(\w+)"', (ROOT / "router" / "my.py").read_text()))
        self.assertEqual(sent, {"channel_object_create", "channel_object_update"})
        self.assertEqual(sorted(sent - set(func_consumer_channels())), [])

    def test_channel_names_start_with_channel(self):
        self.assertEqual([name for name in func_consumer_channels() if not name.startswith("channel_")], [])

    def test_unknown_channel_stops_before_connecting(self):
        with patch("function.queues.func_run_broker") as run_broker, self.assertRaisesRegex(Exception, "unknown channel: func_postgres_create"):
            func_consumer_run(queue="redis", channel="func_postgres_create", broker_settings={}, postgres_url="postgresql://x", config_buffer_rows_max=1)
        run_broker.assert_not_called()

    def test_each_broker_script_runs_its_own_broker(self):
        for queue in ("redis", "rabbitmq", "kafka", "celery"):
            text = (ROOT / "script" / f"consumer_{queue}.py").read_text()
            with self.subTest(queue=queue):
                self.assertIn(f'queue="{queue}"', text)
                self.assertEqual(re.findall(r'os\.getenv\("(config_(?:redis|rabbitmq|kafka|celery)_\w+)"\)', text), re.findall(r'"(config_\w+)": ', text), "reads only the broker keys it passes")


class QueueChannelDispatchTests(unittest.IsolatedAsyncioTestCase):
    async def test_update_message_reaches_func_postgres_update_with_its_owner(self):
        context = {"client_postgres_dict": {"master": object()}, "cache_postgres_schema_dict": {"master": {}}, "client_password_hasher": None, "cache_column_regex": {"master": {"post": {"title": ["^.{1,9}$", "short title"]}}}}
        with patch("function.queues.func_postgres_update", new=AsyncMock(return_value="ok")) as update:
            result = await func_consumer_object_update(payload={"table": "post", "obj_list": [{"id": 1}], "created_by_id": 7}, context=context)
        self.assertEqual(result, "ok")
        self.assertEqual((update.await_args.kwargs["table"], update.await_args.kwargs["created_by_id"], update.await_args.kwargs["ownership_column"]), ("post", 7, "created_by_id"))
        self.assertEqual(update.await_args.kwargs["column_regex"], {"title": ["^.{1,9}$", "short title"]}, "the job's table's format rules")


class QueueValueTests(unittest.TestCase):
    def test_postgres_is_not_a_queue_value_on_the_object_routes(self):
        """A single create or update queued on Postgres only adds writes: ?queue= takes the brokers, the Postgres queue is for a project's own jobs."""
        import config
        self.assertNotIn("postgres", config.config_queue_services)


if __name__ == "__main__":
    unittest.main()


class QueueChannelConnectionTests(unittest.IsolatedAsyncioTestCase):
    def context(self):
        import asyncio
        return {"client_postgres_dict": {"master": "master-pool"}, "cache_postgres_schema_dict": {"master": {}}, "postgres_url_dict": {"master": "postgresql://m", "telemetry": "postgresql://t"},
                "lock_postgres_open": asyncio.Lock(), "client_password_hasher": None, "cache_column_regex": {}, "buffer_postgres_create": {}, "config_buffer_rows_max": 10, "config_postgres_table_rule": {"telemetry": {"reading": {"buffer_limit": 500}}}}

    async def test_a_job_writes_to_the_database_its_request_used(self):
        from function import func_consumer_object_create
        context = self.context()
        with patch("function.queues.func_client_postgres", new=AsyncMock(return_value="telemetry-pool")) as open_pool, patch("function.queues.func_postgres_schema_read", new=AsyncMock(return_value={"reading": {}})), patch("function.queues.func_postgres_create", new=AsyncMock(return_value="created")) as create:
            for _ in range(2): await func_consumer_object_create(payload={"table": "reading", "obj_list": [{"value": 1}], "connection": "telemetry"}, context=context)
            await func_consumer_object_create(payload={"table": "post", "obj_list": [{"title": "x"}]}, context=context)
        open_pool.assert_awaited_once_with(dsn="postgresql://t", min_size=1, max_size=5)    # opened on the first job, reused after
        self.assertEqual([(c.kwargs["client_postgres"], c.kwargs["connection"]) for c in create.await_args_list], [("telemetry-pool", "telemetry"), ("telemetry-pool", "telemetry"), ("master-pool", "master")])

    async def test_an_unknown_database_fails_the_job(self):
        from function import func_consumer_object_create
        with self.assertRaisesRegex(Exception, "connection 'gone' not found: set config_postgres_url_gone"):
            await func_consumer_object_create(payload={"table": "reading", "obj_list": [{"value": 1}], "connection": "gone"}, context=self.context())
