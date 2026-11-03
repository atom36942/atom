"""Pages are served with every local link stamped ?v=<fingerprint of the file>, and stamped files are cached for a year: a changed file gets a new address, so browsers never keep an old copy."""
import os
import re
import tempfile
import time
import unittest

from fastapi import FastAPI
from fastapi import Request
from fastapi.testclient import TestClient

from function import func_app_page_response
from function import func_app_static_add

PAGE = """<link rel="stylesheet" href="/static/app/css/app.css">
<script src="/static/app/js/app.js?v=2&mode=x"></script>
<script src='/static/app/js/missing.js'></script>
<script src="https://cdn.example.com/lib.js"></script>
<img src="/static/app/logo.png" alt="">"""


class PageVersionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.cwd = os.getcwd()
        os.chdir(self.temp.name)    # func_app_page_html looks in static/ and static_extend/ under the working directory, as the app does
        self.addCleanup(os.chdir, self.cwd)
        os.makedirs("static")
        for name, content in (("app/index.html", PAGE), ("app/css/app.css", "body{}"), ("app/js/app.js", "let a = 1"), ("app/logo.png", "png")):
            self.write(name, content)
        app = FastAPI()
        app.state.cache_static_version = {}
        func_app_static_add(app=app)
        @app.get("/page/app")
        async def page(request: Request):    # what router/index.py does
            return await func_app_page_response(request=request, path="static_extend/app/index.html", cache_static_version=app.state.cache_static_version)
        self.client = TestClient(app)

    def write(self, name, content):
        path = os.path.join("static_extend", name)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as file: file.write(content)

    def links(self):
        return dict(re.findall(r'(?:src|href)=["\']/static/([^"\'?]+)\??([^"\']*)["\']', self.client.get("/page/app").text))

    def test_local_links_get_the_file_fingerprint_and_others_stay(self):
        html = self.client.get("/page/app").text
        links = self.links()
        self.assertRegex(links["app/css/app.css"], r"^v=[0-9a-f]{10}$")
        self.assertRegex(links["app/js/app.js"], r"^mode=x&v=[0-9a-f]{10}$", "an old ?v= is replaced, other parameters kept")
        self.assertRegex(links["app/logo.png"], r"^v=[0-9a-f]{10}$")
        self.assertIn("src='/static/app/js/missing.js'", html, "a link to a missing file is left as it is")
        self.assertIn('src="https://cdn.example.com/lib.js"', html)

    def test_a_changed_file_gets_a_new_address(self):
        before = self.links()
        time.sleep(0.01)
        self.write("app/js/app.js", "let a = 2")
        after = self.links()
        self.assertNotEqual(after["app/js/app.js"], before["app/js/app.js"])
        self.assertEqual(after["app/css/app.css"], before["app/css/app.css"])

    def test_stamped_files_are_kept_a_year_and_the_page_and_plain_files_revalidate(self):
        page = self.client.get("/page/app")
        self.assertEqual(page.headers["cache-control"], "no-cache")
        self.assertEqual(self.client.get("/page/app", headers={"if-none-match": page.headers["etag"]}).status_code, 304)
        css = self.client.get(f"/static/app/css/app.css?{self.links()['app/css/app.css']}")
        self.assertEqual((css.status_code, css.text, css.headers["cache-control"]), (200, "body{}", "public, max-age=31536000, immutable"))
        self.assertEqual(self.client.get("/static/app/css/app.css").headers["cache-control"], "no-cache")


if __name__ == "__main__":
    unittest.main()
