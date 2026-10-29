"""func_app_route_lookup_add must answer every request exactly as FastAPI's normal route matching does."""
import unittest

from fastapi import APIRouter
from fastapi import FastAPI
from fastapi import WebSocket
from fastapi.responses import PlainTextResponse
from fastapi.testclient import TestClient
from starlette.staticfiles import StaticFiles

from function import func_app_route_lookup_add


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


if __name__ == "__main__":
    unittest.main()
