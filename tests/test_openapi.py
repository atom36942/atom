"""/openapi.json (used by static/api.html) must match every route's param_specs.

The spec is built by parsing route source, so a parsing problem would silently
drop a route's fields from api.html. These checks compare it to the code itself,
so adding or changing routes needs no snapshot update.
"""
import ast
import inspect
import io
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from fastapi.routing import APIRoute

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEST_ENV = {"config_token_secret_key": "atom-openapi-test-secret-key-at-least-32-bytes"}


def param_reads(endpoint, app_state):
    """(mode, specs) for each func_request_param_read call in a route, evaluated like the app does."""
    tree = ast.parse(inspect.getsource(endpoint))
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and getattr(node.func, "attr", None) == "func_request_param_read":
            kwargs = {k.arg: k.value for k in node.keywords}
            yield ast.literal_eval(kwargs["mode"]), eval(ast.unparse(kwargs["param_specs"]), {"app_state": app_state})


class OpenApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # config.py reads .env from the working directory and startup resets ./tmp, so boot from a temp dir with test-only env
        cls.workdir = tempfile.TemporaryDirectory()
        cls.previous_cwd = os.getcwd()
        os.chdir(cls.workdir.name)
        cls.env = patch.dict(os.environ, TEST_ENV, clear=True)
        cls.env.start()
        sys.path.insert(0, REPO_ROOT)
        for module in ("main", "config", "config_extend"): sys.modules.pop(module, None)
        from fastapi.testclient import TestClient
        cls.startup_log = io.StringIO()
        with redirect_stdout(cls.startup_log):
            import main
            cls.app = main.app
            cls.client = TestClient(main.app)
            cls.client.__enter__()
        cls.paths = cls.client.get("/openapi.json").json()["paths"]

    @classmethod
    def tearDownClass(cls):
        try: cls.client.__exit__(None, None, None)
        finally:
            os.chdir(cls.previous_cwd)
            cls.env.stop()
            sys.path.remove(REPO_ROOT)
            for module in ("main", "config", "config_extend"): sys.modules.pop(module, None)
            cls.workdir.cleanup()

    def routes(self):
        return [(route, method.lower()) for route in self.app.routes if isinstance(route, APIRoute) for method in route.methods]

    def test_spec_generation_logs_no_skipped_routes(self):
        self.assertNotIn("⚠️ openapi", self.startup_log.getvalue())

    def test_every_route_is_documented(self):
        for route, method in self.routes():
            with self.subTest(path=route.path, method=method):
                self.assertIn(method, self.paths.get(route.path, {}))

    def test_every_param_spec_is_documented_with_required_and_options(self):
        checked = 0
        for route, method in self.routes():
            op = self.paths[route.path][method]
            for mode, specs in param_reads(route.endpoint, self.app.state):
                for spec in specs or []:    # param_specs=None reads the raw body, nothing to document
                    with self.subTest(path=route.path, mode=mode, param=spec["name"]):
                        required, allowed = bool(spec.get("required", False)), spec.get("allowed")
                        if mode in ("query", "header"):
                            documented = [p for p in op["parameters"] if p["name"] == spec["name"] and p["in"] == mode]
                            self.assertEqual(len(documented), 1)
                            self.assertEqual(documented[0]["required"], required)
                            if isinstance(allowed, (list, tuple)): self.assertEqual(documented[0]["schema"]["enum"], list(allowed))
                        else:
                            media = "application/json" if mode == "body" else "multipart/form-data"
                            schema = op["requestBody"]["content"][media]["schema"]
                            self.assertIn(spec["name"], schema["properties"])
                            self.assertEqual(spec["name"] in schema["required"], required)
                        checked += 1
        self.assertGreater(checked, 200)    # guards against the walk itself silently finding nothing

    def test_postgres_param_is_documented_only_on_flagged_routes(self):
        for route, method in self.routes():
            with self.subTest(path=route.path):
                names = [p["name"] for p in self.paths[route.path][method]["parameters"]]
                self.assertEqual("postgres" in names, bool(self.app.state.config_api.get(route.path, {}).get("is_postgres_param")))


if __name__ == "__main__":
    unittest.main()
