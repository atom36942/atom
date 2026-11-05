"""Startup opens named clients one at a time, so a failure partway leaves the ones already open in the dict, where the startup cleanup closes them; and the Postgres query time limit reaches asyncpg only when set."""
import unittest
from unittest.mock import AsyncMock
from unittest.mock import MagicMock
from unittest.mock import patch

from function.clients import func_client_close
from function.clients import func_client_dict_open
from function.clients import func_client_postgres


class ClientDictOpenTests(unittest.IsolatedAsyncioTestCase):
    async def test_a_failure_partway_keeps_and_closes_the_open_ones(self):
        opened = {"master": MagicMock(close=AsyncMock()), "replica": MagicMock(close=AsyncMock())}
        async def client_open(*, name, url):
            if name == "analytics": raise ConnectionError("analytics is down")
            return opened[name]
        client_postgres_dict = {}
        with self.assertRaises(ConnectionError):
            await func_client_dict_open(client_dict=client_postgres_dict, url_dict={"master": "postgresql://a", "replica": "postgresql://b", "analytics": "postgresql://c"}, client_open=client_open)
        self.assertEqual(list(client_postgres_dict), ["master", "replica"])
        await func_client_close(clients={"client_postgres_dict": client_postgres_dict})
        for pool in opened.values(): pool.close.assert_awaited_once()

    async def test_empty_urls_are_skipped(self):
        client_open = AsyncMock(return_value="client")
        result = await func_client_dict_open(client_dict={}, url_dict={"master": "postgresql://a", "spare": ""}, client_open=client_open)
        self.assertEqual(result, {"master": "client"})

    async def test_query_timeout_reaches_asyncpg_only_when_set(self):
        with patch("function.clients.asyncpg.create_pool", new=AsyncMock()) as create_pool:
            await func_client_postgres(dsn="postgresql://a", query_timeout_sec=30)
            self.assertEqual(create_pool.await_args.kwargs["command_timeout"], 30)
            await func_client_postgres(dsn="postgresql://a")
            self.assertNotIn("command_timeout", create_pool.await_args.kwargs)


class MainStartupTests(unittest.TestCase):
    def test_main_binds_each_client_dict_before_opening(self):
        """The startup cleanup reads locals(): a dict comprehension would bind nothing until every client opened."""
        from pathlib import Path
        source = (Path(__file__).resolve().parents[1] / "main.py").read_text()
        self.assertIn("client_postgres_dict, client_mssql_dict, client_clickhouse_dict = {}, {}, {}", source)
        self.assertNotIn("client_postgres_dict = {name: await", source)


if __name__ == "__main__":
    unittest.main()
