"""orjson route responses must match FastAPI's default JSON output byte for byte."""
import asyncio
import dataclasses
import enum
import ipaddress
import pathlib
import unittest
import uuid
from datetime import date
from datetime import datetime
from datetime import time
from datetime import timedelta
from datetime import timezone
from datetime import UTC
from decimal import Decimal

import asyncpg
from fastapi import APIRouter
from fastapi import FastAPI
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient
from pydantic import BaseModel
from starlette.responses import PlainTextResponse

from function import func_endpoint_json_wrap
from function import func_response_json


class Color(enum.Enum):
    RED = "red"


@dataclasses.dataclass
class Point:
    x: int
    y: int


class Item(BaseModel):
    name: str
    created_at: datetime


IST = timezone(timedelta(hours=5, minutes=30))
CASES = {
    "scalars": {"status": 1, "message": "ok", "none": None, "flag": True, "float": 1.5, "unicode": "नमस्ते ✓ \"q\" \\ \n"},
    "datetimes": [datetime(2026, 9, 29, 8, 30, 10, 144902, tzinfo=UTC), datetime(2026, 1, 1, tzinfo=IST), datetime(2026, 1, 1, 9, 5), date(2026, 2, 3), time(4, 5, 6, 7), time(4, 5, tzinfo=UTC), timedelta(days=1, seconds=3)],
    "datetime_edges": [datetime(2026, 1, 2, 3, 4, 5, 999999), datetime(1, 1, 1), datetime(2026, 1, 2, 3, 4, 5, tzinfo=timezone(-timedelta(hours=3, minutes=30))), datetime(2026, 1, 2, 3, 4, 5, 6, tzinfo=timezone(timedelta(hours=14)))],
    "date_keys": {date(2026, 1, 2): "date", datetime(2026, 1, 2, 3, 4, 5, tzinfo=UTC): "datetime", time(1, 2): "time"},
    "decimals": [Decimal("10"), Decimal("1.25"), Decimal("1E+2"), Decimal("-0.001")],
    "types": [uuid.UUID("12345678-1234-5678-1234-567812345678"), {1, 2}, frozenset({3}), (4, 5), b"bytes", Color.RED, Point(1, 2), ipaddress.ip_address("10.0.0.1"), pathlib.PurePosixPath("/tmp/a")],
    "model": Item(name="a", created_at=datetime(2026, 1, 1, tzinfo=UTC)),
    "keys": {1: "int", None: "none", False: "bool", 2.5: "float", "nested": {"list": [[1, {"deep": Decimal("2.5")}]]}},
    "big_int": {"value": 2 ** 70, "decimal": Decimal("123456789012345678901234567890")},
    "list_top": [{"id": 1}, {"id": 2}],
    "empty": {},
}


class ResponseJsonTests(unittest.TestCase):
    def test_body_matches_fastapi_default_for_every_type(self):
        for name, content in CASES.items():
            with self.subTest(case=name):
                expected = JSONResponse(content=jsonable_encoder(content))
                actual = func_response_json(content=content)
                self.assertEqual(actual.body, expected.body)
                self.assertEqual(actual.headers["content-type"], expected.headers["content-type"])
                self.assertEqual(actual.status_code, 200)

    def test_unsupported_value_fails_like_fastapi(self):
        content = {"range": asyncpg.Range(1, 5)}
        with self.assertRaises(Exception) as fastapi_error: JSONResponse(content=jsonable_encoder(content))
        with self.assertRaises(Exception) as atom_error: func_response_json(content=content)
        self.assertIs(type(atom_error.exception), type(fastapi_error.exception))

    def test_wrapper_passes_responses_through_and_keeps_signature(self):
        async def endpoint(*, request): return PlainTextResponse("raw")
        wrapped = func_endpoint_json_wrap(endpoint=endpoint, status_code=None)
        self.assertEqual(asyncio.run(wrapped(request=None)).body, b"raw")
        self.assertIs(func_endpoint_json_wrap(endpoint=wrapped, status_code=None), wrapped)
        self.assertEqual(wrapped.__wrapped__, endpoint)

    def test_loaded_routes_return_orjson_bodies(self):
        app = FastAPI(openapi_url=None, docs_url=None, redoc_url=None)
        router = APIRouter()
        @router.get("/a")
        async def route_async(): return {"when": datetime(2026, 1, 1, tzinfo=UTC), "n": Decimal("2.50")}
        @router.get("/s", status_code=201)
        def route_sync(): return [1, {2}]
        app.include_router(router)
        expected = {path: TestClient(app).get(path) for path in ("/a", "/s")}
        app2 = FastAPI(openapi_url=None, docs_url=None, redoc_url=None)
        module_router = APIRouter()
        module_router.routes.extend(router.routes)
        for route in module_router.routes: route.endpoint = func_endpoint_json_wrap(endpoint=route.endpoint, status_code=route.status_code)
        app2.include_router(module_router)
        for path, response in expected.items():
            with self.subTest(path=path):
                actual = TestClient(app2).get(path)
                self.assertEqual((actual.status_code, actual.content), (response.status_code, response.content))


if __name__ == "__main__":
    unittest.main()
