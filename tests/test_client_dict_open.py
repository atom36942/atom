"""Named clients open at once; a failure closes the ones that opened, so nothing is left open; and the Postgres query time limit reaches asyncpg only when set."""
import unittest
from unittest.mock import AsyncMock
from unittest.mock import MagicMock
from unittest.mock import patch

from function.clients import func_client_dict_open
from function.clients import func_client_postgres


class ClientDictOpenTests(unittest.IsolatedAsyncioTestCase):
    async def test_a_failure_closes_the_open_ones(self):
        opened = {"master": MagicMock(close=AsyncMock()), "replica": MagicMock(close=AsyncMock())}
        async def client_open(*, name, url):
            if name == "analytics": raise ConnectionError("analytics is down")
            return opened[name]
        with self.assertRaisesRegex(ConnectionError, "analytics is down"):
            await func_client_dict_open(url_dict={"master": "postgresql://a", "replica": "postgresql://b", "analytics": "postgresql://c"}, client_open=client_open, client_close=lambda c: c.close())
        for pool in opened.values(): pool.close.assert_awaited_once()

    async def test_empty_urls_are_skipped(self):
        client_open = AsyncMock(return_value="client")
        result = await func_client_dict_open(url_dict={"master": "postgresql://a", "spare": ""}, client_open=client_open, client_close=None)
        self.assertEqual(result, {"master": "client"})

    async def test_query_timeout_reaches_asyncpg_only_when_set(self):
        with patch("function.clients._FairPool", new=AsyncMock()) as create_pool:
            await func_client_postgres(dsn="postgresql://a", query_timeout_sec=30)
            self.assertEqual(create_pool.await_args.kwargs["command_timeout"], 30)
            await func_client_postgres(dsn="postgresql://a")
            self.assertNotIn("command_timeout", create_pool.await_args.kwargs)


if __name__ == "__main__":
    unittest.main()
