"""/pgweb runs any SQL, so every way of reaching it from outside this machine's own page must be refused."""
import unittest

from fastapi import FastAPI
from fastapi import Request
from fastapi.testclient import TestClient

from function import func_pgweb_request_check


def client(is_enabled=True):
    app = FastAPI(openapi_url=None, docs_url=None, redoc_url=None)
    @app.exception_handler(Exception)
    async def handler(request, exc):
        from fastapi.responses import JSONResponse
        return JSONResponse({"message": str(exc)}, status_code=getattr(exc, "status_code", 500))
    @app.post("/pgweb")
    async def pgweb(request: Request):
        func_pgweb_request_check(request=request, config_is_pgweb_enabled=is_enabled)
        return {"status": 1}
    return TestClient(app, raise_server_exceptions=False)


JSON = {"Content-Type": "application/json"}


class PgwebAccessTests(unittest.TestCase):
    def post(self, headers, is_enabled=True):
        return client(is_enabled).post("/pgweb", content=b'{"action":"info"}', headers=headers)

    def test_own_page_on_localhost_is_allowed(self):
        self.assertEqual(self.post(JSON).status_code, 200)
        self.assertEqual(self.post(JSON | {"Origin": "http://testserver"}).status_code, 200)

    def test_disabled_by_default_flag(self):
        response = self.post(JSON, is_enabled=False)
        self.assertEqual(response.status_code, 404)
        self.assertIn("config_is_pgweb_enabled", response.json()["message"])

    def test_proxy_and_tunnel_headers_are_refused(self):
        for header in ("X-Forwarded-For", "Forwarded", "X-Real-IP", "CF-Connecting-IP", "X-Forwarded-Host"):
            with self.subTest(header=header):
                self.assertEqual(self.post(JSON | {header: "203.0.113.9"}).status_code, 403)

    def test_other_websites_are_refused(self):
        response = self.post(JSON | {"Origin": "https://evil.example"})
        self.assertEqual(response.status_code, 403)
        self.assertIn("own page", response.json()["message"])

    def test_cross_site_simple_content_types_are_refused(self):
        for content_type in ("text/plain", "application/x-www-form-urlencoded", "multipart/form-data; boundary=x", ""):
            with self.subTest(content_type=content_type):
                self.assertEqual(self.post({"Content-Type": content_type}).status_code, 415)


if __name__ == "__main__":
    unittest.main()
