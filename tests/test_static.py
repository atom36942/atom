"""Atom's static/ and the project's static_extend/ are served together at /static."""
import os
import tempfile
import unittest

from fastapi import FastAPI, Response
from fastapi.responses import FileResponse
from fastapi.testclient import TestClient

from function import func_app_static_add, func_app_static_page_list, func_app_static_page_path


class StaticTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.atom, self.project = os.path.join(self.temp.name, "static"), os.path.join(self.temp.name, "static_extend")
        os.makedirs(self.atom)
        self.write(self.atom, "api.html", "atom page")

    def write(self, directory, name, content):
        os.makedirs(directory, exist_ok=True)
        with open(os.path.join(directory, name), "w") as file: file.write(content)

    def client(self):
        app = FastAPI()
        func_app_static_add(app=app, directories=(self.atom, self.project))
        @app.get("/page/{name}")
        def page(name: str):    # what router/index.py does with the same helper
            path = func_app_static_page_path(name=name, directories=(self.atom, self.project))
            return FileResponse(path) if path else Response(status_code=404)
        return TestClient(app)

    def test_both_folders_are_served_at_static(self):
        self.write(self.project, "pulse.html", "project page")
        client = self.client()
        self.assertEqual(client.get("/static/api.html").text, "atom page")
        self.assertEqual(client.get("/static/pulse.html").text, "project page")
        self.assertEqual(client.get("/static/missing.html").status_code, 404)

    def test_missing_static_extend_is_fine(self):
        self.assertEqual(self.client().get("/static/api.html").text, "atom page")

    def test_same_file_in_both_folders_stops_startup(self):
        self.write(self.project, "api.html", "project copy")
        with self.assertRaisesRegex(Exception, "api.html clashes with"):
            self.client()

    def test_page_list_has_html_files_and_folders_with_index_html_only(self):
        self.write(self.atom, "home.html", "")
        self.write(self.atom, "data.csv", "a,b")
        self.write(os.path.join(self.atom, "report"), "index.html", "")
        self.write(os.path.join(self.atom, "assets"), "app.js", "")    # a folder without index.html is not an app
        self.write(self.project, "PULSE.html", "")
        pages = func_app_static_page_list(directories=(self.atom, self.project))
        self.assertEqual(pages, [
            {"name": "Api", "url": "/page/api", "folder": "static"},
            {"name": "Home", "url": "/page/home", "folder": "static"},    # every page is listed, the home page too
            {"name": "Pulse", "url": "/static/PULSE.html", "folder": "static_extend"},    # not a lowercase name, so it keeps its /static URL; the name is capitalized the same way for every app
            {"name": "Report", "url": "/page/report", "folder": "static"},
        ])

    def test_page_list_without_folders_is_empty(self):
        self.assertEqual(func_app_static_page_list(directories=(os.path.join(self.temp.name, "none"),)), [])

    def test_every_listed_page_is_served(self):
        self.write(os.path.join(self.project, "report"), "index.html", "")
        client = self.client()
        for page in func_app_static_page_list(directories=(self.atom, self.project)):
            with self.subTest(page=page["url"]): self.assertEqual(client.get(page["url"]).status_code, 200)

    def test_page_by_name_serves_the_file_or_the_folder_index(self):
        self.write(os.path.join(self.project, "cdd"), "index.html", "cdd app")
        client = self.client()
        self.assertEqual(client.get("/page/api").text, "atom page")
        self.assertEqual(client.get("/page/cdd").text, "cdd app")
        self.assertEqual(client.get("/page/cdd?tab=overview").text, "cdd app")    # the query is the page's own; the server ignores it
        for name in ("missing", "API", "cdd/overview", "..", ".env", "cdd.html"):
            with self.subTest(name=name): self.assertEqual(client.get(f"/page/{name}").status_code, 404)

    def test_page_path_rejects_unsafe_names(self):
        for name in ("", "../static/api", "api.html", "a/b", "Api", None):
            with self.subTest(name=name): self.assertIsNone(func_app_static_page_path(name=name, directories=(self.atom, self.project)))
