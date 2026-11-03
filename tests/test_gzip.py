"""Responses over 1 KB are gzipped when the client accepts gzip (func_app_gzip_add); small, already encoded and non-gzip requests pass unchanged."""
import gzip
import unittest
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import Response
from fastapi.responses import StreamingResponse
from starlette.testclient import TestClient

from function import func_app_gzip_add

ROWS = [{"id": i, "title": f"row {i}", "note": "the same text again"} for i in range(200)]


def app_with_gzip():
    app = FastAPI()
    func_app_gzip_add(app=app)
    app.get("/big")(lambda: {"status": 1, "message": ROWS})
    app.get("/small")(lambda: {"status": 1, "message": "ok"})
    app.get("/cached")(lambda: Response(content=gzip.compress(b'{"status":1}' * 200), media_type="application/json", headers={"content-encoding": "gzip"}))
    for media_type in ("image/png", "application/pdf", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "video/mp4"):
        app.get(f"/file/{media_type}")(lambda media_type=media_type: Response(content=b"x" * 5000, media_type=media_type))
    app.get("/svg")(lambda: Response(content=b"<svg>" + b"<path/>" * 500 + b"</svg>", media_type="image/svg+xml"))
    app.get("/csv")(lambda: StreamingResponse(iter(["id,title\n", *[f"{i},row {i}\n" for i in range(2000)]]), media_type="text/csv"))
    return TestClient(app)


class GzipTests(unittest.TestCase):
    def setUp(self):
        self.client = app_with_gzip()

    def test_big_json_is_gzipped_only_when_the_client_accepts_it(self):
        zipped = self.client.get("/big", headers={"Accept-Encoding": "gzip"})
        self.assertEqual(zipped.headers["content-encoding"], "gzip")
        self.assertIn("accept-encoding", zipped.headers["vary"].lower())
        self.assertEqual(zipped.json()["message"], ROWS)    # the client unpacks it
        plain = self.client.get("/big", headers={"Accept-Encoding": "identity"})
        self.assertNotIn("content-encoding", plain.headers)
        self.assertEqual(plain.json()["message"], ROWS)

    def test_small_responses_stay_plain(self):
        self.assertNotIn("content-encoding", self.client.get("/small", headers={"Accept-Encoding": "gzip"}).headers)

    def test_an_already_gzipped_cache_hit_is_not_compressed_twice(self):
        response = self.client.get("/cached", headers={"Accept-Encoding": "gzip"})
        self.assertEqual(response.headers["content-encoding"], "gzip")
        self.assertEqual(response.content, b'{"status":1}' * 200)

    def test_files_that_are_compressed_already_pass_through_but_svg_text_is_gzipped(self):
        for media_type in ("image/png", "application/pdf", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "video/mp4"):
            with self.subTest(media_type=media_type):
                response = self.client.get(f"/file/{media_type}", headers={"Accept-Encoding": "gzip"})
                self.assertNotIn("content-encoding", response.headers)
                self.assertEqual(response.content, b"x" * 5000)
        self.assertEqual(self.client.get("/svg", headers={"Accept-Encoding": "gzip"}).headers["content-encoding"], "gzip")

    def test_streamed_csv_is_gzipped_and_complete(self):
        response = self.client.get("/csv", headers={"Accept-Encoding": "gzip"})
        self.assertEqual(response.headers["content-encoding"], "gzip")
        self.assertEqual(response.text.count("\n"), 2001)

    def test_main_adds_gzip_outside_atoms_middleware_and_inside_cors(self):
        text = (Path(__file__).resolve().parent.parent / "main.py").read_text()
        self.assertLess(text.index("app.add_middleware(middleware)"), text.index("func_app_gzip_add(app=app)"))
        self.assertLess(text.index("func_app_gzip_add(app=app)"), text.index("func_app_cors_add(app=app"))


if __name__ == "__main__":
    unittest.main()
