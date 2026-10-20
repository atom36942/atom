"""Atom's static/ and the project's static_extend/ are served together at /static."""
import os
import tempfile
import unittest

from fastapi import FastAPI
from fastapi.testclient import TestClient

from function import func_app_static_add


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
