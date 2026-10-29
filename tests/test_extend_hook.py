"""func_extend and func_extend_shutdown from function_extend/ are optional and may be sync or async."""
from types import SimpleNamespace
import unittest

from function import func_app_extend_run


class ExtendHookTests(unittest.IsolatedAsyncioTestCase):
    async def test_missing_hook_returns_none(self):
        self.assertIsNone(await func_app_extend_run(app_state=SimpleNamespace(), name="func_extend"))

    async def test_sync_and_async_hooks_receive_app_state(self):
        async def async_hook(*, app_state): return {"client": app_state.config_key}
        def sync_hook(*, app_state): return [app_state.config_key]
        app_state = SimpleNamespace(config_key="k", func_extend=async_hook, func_extend_shutdown=sync_hook)
        self.assertEqual(await func_app_extend_run(app_state=app_state, name="func_extend"), {"client": "k"})
        self.assertEqual(await func_app_extend_run(app_state=app_state, name="func_extend_shutdown"), ["k"])

    async def test_hook_error_propagates(self):
        async def failing(*, app_state): raise RuntimeError("bad client")
        with self.assertRaisesRegex(RuntimeError, "bad client"):
            await func_app_extend_run(app_state=SimpleNamespace(func_extend=failing), name="func_extend")
