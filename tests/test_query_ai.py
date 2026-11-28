"""func_postgres_query_ai and func_clickhouse_query_ai return only the SQL by default, and with execute run it through the read runner and add its rows."""
import unittest
from unittest.mock import AsyncMock
from unittest.mock import patch
from function import query_runners
from function.query_runners import func_clickhouse_query_ai
from function.query_runners import func_postgres_query_ai

PG_SCHEMA = {"users": {"id": {"schema_name": "public", "relation_type": "table", "data_type": "bigint", "btree_indexes": ["users_pkey"], "is_primary": True, "is_unique_constraint": False, "is_unique_index": True}}}
CH_SCHEMA = {"default.events": {"id": "UInt64"}}
AI = {"sql": "SELECT id FROM users", "message": "ok", "warnings": []}

class QueryAiTests(unittest.IsolatedAsyncioTestCase):
    async def postgres(self, execute):
        runner = AsyncMock(return_value=[{"id": 1}])
        with patch.object(query_runners, "func_anthropic_json", AsyncMock(return_value=AI)), patch.object(query_runners, "func_postgres_query_runner_read", runner):
            res = await func_postgres_query_ai(client_postgres=object(), client_gemini=None, client_openai=None, client_anthropic=object(), cache_postgres_schema=PG_SCHEMA, config_query_runner_read_limit=100, ai="claude", question="ids", execute=execute)
        return res, runner

    async def test_postgres_default_returns_sql_only(self):
        res, runner = await self.postgres(False)
        self.assertEqual(res["sql"], "SELECT id FROM users\nLIMIT 10;")
        self.assertNotIn("rows", res)
        runner.assert_not_awaited()

    async def test_postgres_execute_runs_read_runner(self):
        res, runner = await self.postgres(True)
        self.assertEqual(res["rows"], [{"id": 1}])
        self.assertEqual(runner.await_args.kwargs["sql"], "SELECT id FROM users\nLIMIT 10;")
        self.assertEqual(runner.await_args.kwargs["config_query_runner_read_limit"], 100)

    async def test_clickhouse_execute_runs_read_runner(self):
        runner = AsyncMock(return_value=[{"id": 2}])
        with patch.object(query_runners, "func_anthropic_json", AsyncMock(return_value={"sql": "SELECT id FROM events", "message": "ok", "warnings": []})), patch.object(query_runners, "func_clickhouse_query_runner_read", runner):
            res = await func_clickhouse_query_ai(client_clickhouse=object(), client_gemini=None, client_openai=None, client_anthropic=object(), cache_clickhouse_schema=CH_SCHEMA, config_query_runner_read_limit=100, ai="claude", question="ids", execute=True)
        self.assertEqual(res["rows"], [{"id": 2}])
        runner.assert_awaited_once()

    async def test_gemini_and_openai_are_awaited_on_their_async_clients(self):
        """No thread: Gemini through client.aio, OpenAI through AsyncOpenAI."""
        import json
        from types import SimpleNamespace
        from unittest.mock import MagicMock
        gemini = MagicMock()
        gemini.aio.models.generate_content = AsyncMock(return_value=SimpleNamespace(text=json.dumps(AI)))
        openai = MagicMock()
        openai.responses.create = AsyncMock(return_value=SimpleNamespace(output_text=json.dumps(AI)))
        for ai, client in (("gemini", gemini.aio.models.generate_content), ("openai", openai.responses.create)):
            with self.subTest(ai=ai), patch.object(query_runners.asyncio, "to_thread", side_effect=AssertionError("thread used")):
                res = await func_postgres_query_ai(client_postgres=object(), client_gemini=gemini, client_openai=openai, client_anthropic=None, cache_postgres_schema=PG_SCHEMA, config_query_runner_read_limit=100, ai=ai, question="ids")
                self.assertEqual(res["sql"], "SELECT id FROM users\nLIMIT 10;")
                client.assert_awaited()
        gemini.models.generate_content.assert_not_called()

if __name__ == "__main__": unittest.main()
