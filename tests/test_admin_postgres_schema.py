"""GET /admin/postgres-schema returns Atom's schema cache for the request's database (master, or ?connection=<name>) and never queries the database."""
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock

from fastapi import FastAPI
from starlette.requests import Request

from function import func_middleware_postgres_select
from function import func_request_param_read
from router.admin import func_api_admin_postgres_schema

SCHEMA = {
    "master": {"users": {"id": {"datatype": "bigint", "is_primary": True}}},
    "analytics": {"events": {"id": {"datatype": "bigint", "is_primary": True}}},
}


def request_for(query: str, connection: str | None) -> Request:
    """A request as the middleware leaves it: the pool and schema cache of the chosen database on request.state."""
    app = FastAPI()
    app.state.func_request_param_read = func_request_param_read
    app.state.func_postgres_schema_read = AsyncMock(side_effect=AssertionError("the route must not read the catalog"))
    pools = {"master": SimpleNamespace(name="master"), "analytics": SimpleNamespace(name="analytics")}
    request = Request({"type": "http", "method": "GET", "path": "/admin/postgres-schema", "query_string": query.encode(), "headers": [], "app": app})
    request.state.client_postgres, request.state.cache_postgres_schema = func_middleware_postgres_select(client_postgres_dict=pools, cache_postgres_schema_dict=SCHEMA, is_connection_param=True, connection=connection)
    return request


class AdminPostgresSchemaTests(unittest.IsolatedAsyncioTestCase):
    async def test_without_connection_it_returns_the_master_cache(self):
        res = await func_api_admin_postgres_schema(request=request_for("", None))
        self.assertEqual(res, {"status": 1, "message": SCHEMA["master"]})

    async def test_connection_returns_that_database_cache(self):
        res = await func_api_admin_postgres_schema(request=request_for("connection=analytics", "analytics"))
        self.assertEqual(res["message"], SCHEMA["analytics"])

    async def test_any_other_query_parameter_is_refused(self):
        with self.assertRaisesRegex(Exception, "unknown parameters"):
            await func_api_admin_postgres_schema(request=request_for("postgres=analytics", None))


if __name__ == "__main__":
    unittest.main()
