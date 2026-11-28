"""The client registry: Atom's entries plus the project's func_extend_client, opened at once; a failure closes the ones that opened and stops startup; project names are checked."""
import asyncio
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock

import config
from function.clients import func_client_registry
from function.clients import func_client_registry_build
from function.clients import func_client_registry_open


def app_state(**extra):
    values = {k: v for k, v in vars(config).items() if k.startswith("config_")}
    values.update({f"config_{db}_url_dict": {} for db in ("postgres", "redis", "mssql", "clickhouse")})    # no database: nothing to connect to
    return SimpleNamespace(**values, **extra)


class ClientRegistryTests(unittest.IsolatedAsyncioTestCase):
    async def test_atom_clients_with_empty_settings_open_as_none(self):
        clients = await func_client_registry_open(registry=func_client_registry(app_state=app_state()))
        self.assertIsNotNone(clients["client_password_hasher"])
        self.assertEqual(clients["client_postgres_dict"], {})
        for name in ("client_s3", "client_openai", "client_anthropic", "client_sftp", "client_azure_blob", "client_rabbitmq_producer"): self.assertIsNone(clients[name])
        await clients["client_http"].aclose()

    async def test_project_entries_are_added_and_opened(self):
        async def stripe_open(): return "stripe"
        state = app_state(func_extend_client=lambda *, app_state: {"client_stripe": (stripe_open, None), "client_graph": (lambda: None, None)})
        registry = func_client_registry_build(app_state=state)
        clients = await func_client_registry_open(registry={name: registry[name] for name in ("client_stripe", "client_graph")})
        self.assertEqual(clients, {"client_stripe": "stripe", "client_graph": None})

    def test_project_names_are_checked(self):
        for bad, message in (({"stripe": (lambda: None, None)}, "must start with client_"), ({"client_http": (lambda: None, None)}, "is Atom's client"), ({"client_x": "no"}, "must be \\(open, close\\)")):
            with self.subTest(bad=bad), self.assertRaisesRegex(Exception, message):
                func_client_registry_build(app_state=app_state(func_extend_client=lambda *, app_state, bad=bad: bad))

    async def test_one_failure_closes_the_opened_and_raises_its_error(self):
        close = MagicMock()
        async def slow():
            await asyncio.sleep(0.01)
            return "slow"
        def fail(): raise ConnectionError("down")
        registry = {"client_ok": (lambda: "ok", close), "client_slow": (slow, close), "client_bad": (fail, close)}
        with self.assertRaisesRegex(ConnectionError, "down"):
            await func_client_registry_open(registry=registry)
        self.assertEqual(sorted(call.args[0] for call in close.call_args_list), ["ok", "slow"])

    async def test_several_failures_name_each(self):
        def fail(): raise ConnectionError("down")
        with self.assertRaisesRegex(Exception, "client_a: down; client_b: down"):
            await func_client_registry_open(registry={"client_a": (fail, None), "client_b": (fail, None)})


if __name__ == "__main__":
    unittest.main()
