"""func_app_route_lookup_add must answer every request exactly as FastAPI's normal route matching does."""
import unittest

from unittest.mock import patch

from fastapi import APIRouter
from fastapi import Depends
from fastapi import FastAPI
from fastapi import HTTPException
from fastapi import Request
from fastapi.routing import APIRoute
from fastapi import WebSocket
from fastapi.responses import PlainTextResponse
from fastapi.testclient import TestClient
from starlette.staticfiles import StaticFiles

from function import func_app_route_lookup_add
from function import func_endpoint_json_wrap


def build_app():
    first, second = APIRouter(), APIRouter()
    first.add_api_route("/info", lambda: {"route": "info"}, methods=["GET"])
    first.add_api_route("/item/{item_id}", lambda item_id: {"route": "param", "id": item_id}, methods=["GET"])
    first.add_api_route("/form", lambda: {"route": "form-post"}, methods=["POST"])
    second.add_api_route("/item/fixed", lambda: {"route": "fixed"}, methods=["GET"])    # shadowed: /item/{item_id} comes first and wins
    second.add_api_route("/form", lambda: {"route": "form-get"}, methods=["GET"])
    second.add_api_route("/text", lambda: PlainTextResponse("plain"), methods=["GET"])
    @second.websocket("/socket")
    async def socket(websocket: WebSocket):
        await websocket.accept()
        await websocket.send_text("hello")
        await websocket.close()
    app = FastAPI()
    app.include_router(first)
    app.include_router(second)
    app.mount("/static", StaticFiles(directory="static"), name="static")
    return app


CASES = [("GET", "/info"), ("GET", "/item/5"), ("GET", "/item/fixed"), ("POST", "/form"), ("GET", "/form"), ("PUT", "/form"), ("GET", "/text"), ("HEAD", "/info"),
         ("GET", "/info/"), ("GET", "/no-such-path"), ("GET", "/static/api.html"), ("GET", "/static/no-such.png")]


class RouteLookupTests(unittest.TestCase):
    def responses(self, app):
        client = TestClient(app)
        return [(r.status_code, r.content, r.headers.get("content-type"), r.headers.get("allow"), r.headers.get("location")) for r in (client.request(m, p, follow_redirects=False) for m, p in CASES)]

    def test_every_response_matches_normal_matching(self):
        expected = self.responses(build_app())
        app = build_app()
        self.assertEqual(func_app_route_lookup_add(app=app), 4)    # /info, POST /form, GET /form, /text; never the param or the shadowed route
        for (method, path), want, got in zip(CASES, expected, self.responses(app), strict=True):
            with self.subTest(request=f"{method} {path}"): self.assertEqual(got, want)

    def test_websocket_and_scope_route_still_work(self):
        app = build_app()
        func_app_route_lookup_add(app=app)
        seen = {}
        @app.middleware("http")
        async def capture(request, call_next):
            response = await call_next(request)
            seen["route"] = request.scope.get("route")
            return response
        client = TestClient(app)
        with client.websocket_connect("/socket") as ws: self.assertEqual(ws.receive_text(), "hello")
        client.get("/info")
        self.assertEqual(getattr(seen["route"], "path", None), "/info")

    def test_router_level_middleware_keeps_normal_matching(self):
        app = build_app()
        app.router.middleware_stack = lambda scope, receive, send: app.router.app(scope, receive, send)
        self.assertEqual(func_app_route_lookup_add(app=app), 0)


def build_atom_app():
    """Routes written the Atom way (async, request only, wrapped), plus ones that need FastAPI's own handling."""
    router = APIRouter()
    async def read(*, request: Request): return {"status": 1, "message": dict(request.query_params), "route": request.scope["route"].path}
    async def create(*, request: Request): return {"status": 1, "message": await request.json()}
    async def fail(*, request: Request): raise HTTPException(status_code=418, detail="teapot")
    async def text(*, request: Request): return PlainTextResponse("plain", headers={"x-route": "text"})
    async def typed(*, request: Request, limit: int = 5): return {"limit": limit}
    def sync_route(*, request: Request): return {"route": "sync"}
    async def with_dependency(*, request: Request, user: str = Depends(lambda: "dep")): return {"user": user}
    for path, endpoint, methods in [("/read", read, ["GET"]), ("/create", create, ["POST"]), ("/fail", fail, ["GET"]), ("/text", text, ["GET"]), ("/typed", typed, ["GET"]), ("/sync", sync_route, ["GET"]), ("/dep", with_dependency, ["GET"])]:
        router.add_api_route(path, endpoint, methods=methods)
    router.add_api_route("/router-dep", read, methods=["GET"], dependencies=[Depends(lambda: None)])
    for route in router.routes: route.endpoint = func_endpoint_json_wrap(endpoint=route.endpoint, status_code=route.status_code)
    app = FastAPI()
    app.include_router(router)
    return app


ATOM_CASES = [("GET", "/read?a=1&b=x", None), ("POST", "/create", {"k": [1, 2]}), ("POST", "/create", None), ("GET", "/fail", None), ("GET", "/text", None), ("GET", "/typed?limit=7", None), ("GET", "/typed?limit=x", None), ("GET", "/sync", None), ("GET", "/dep", None), ("GET", "/router-dep", None)]


class DirectCallTests(unittest.TestCase):
    """Request-only async routes skip FastAPI's dependency solving; responses stay identical and other routes keep route.handle."""
    def responses(self, app):
        client = TestClient(app, raise_server_exceptions=False)
        return [(r.status_code, r.content, r.headers.get("content-type"), r.headers.get("x-route")) for r in (client.request(m, p, json=body) for m, p, body in ATOM_CASES)]

    def test_responses_match_and_only_request_only_routes_skip_handle(self):
        expected = self.responses(build_atom_app())
        app = build_atom_app()
        self.assertEqual(func_app_route_lookup_add(app=app), 8)
        handled = []
        original = APIRoute.handle
        async def spy(route, scope, receive, send):
            handled.append(route.path)
            return await original(route, scope, receive, send)
        with patch.object(APIRoute, "handle", spy): got = self.responses(app)
        for (method, path, _), want, have in zip(ATOM_CASES, expected, got, strict=True):
            with self.subTest(request=f"{method} {path}"): self.assertEqual(have, want)
        self.assertEqual(sorted(set(handled)), ["/dep", "/router-dep", "/sync", "/typed"])


if __name__ == "__main__":
    unittest.main()
