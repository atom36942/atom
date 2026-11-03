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
            func_consumer_run(queue="redis", channel="func_postgres_create", broker_settings={}, postgres_url="postgresql://x", config_column_regex={}, config_table={}, config_buffer_limit_default=1, config_buffer_rows_max=1)
        run_broker.assert_not_called()

    def test_each_broker_script_runs_its_own_broker(self):
        for queue in ("redis", "rabbitmq", "kafka", "celery"):
            text = (ROOT / "script" / f"consumer_{queue}.py").read_text()
            with self.subTest(queue=queue):
                self.assertIn(f'queue="{queue}"', text)
                self.assertEqual(re.findall(r'os\.getenv\("(config_(?:redis|rabbitmq|kafka|celery)_\w+)"\)', text), re.findall(r'"(config_\w+)": ', text), "reads only the broker keys it passes")


class QueueChannelDispatchTests(unittest.IsolatedAsyncioTestCase):
    async def test_update_message_reaches_func_postgres_update_with_its_owner(self):
        context = {"client_postgres": object(), "client_password_hasher": None, "cache_postgres_schema": {}, "config_column_regex": {}}
        with patch("function.queues.func_postgres_update", new=AsyncMock(return_value="ok")) as update:
            result = await func_consumer_object_update(payload={"table": "post", "obj_list": [{"id": 1}], "created_by_id": 7}, context=context)
        self.assertEqual(result, "ok")
        self.assertEqual((update.await_args.kwargs["table"], update.await_args.kwargs["created_by_id"], update.await_args.kwargs["ownership_column"]), ("post", 7, "created_by_id"))


if __name__ == "__main__":
    unittest.main()
