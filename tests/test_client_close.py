"""func_client_close closes each client with its registry close, the project's first; None and close-less clients are skipped, and one failing to close does not stop the others."""
import unittest
from unittest.mock import AsyncMock
from unittest.mock import MagicMock

from function.clients import func_client_close


class ClientCloseTests(unittest.IsolatedAsyncioTestCase):
    async def test_sync_and_async_closes_run_in_reverse_order(self):
        order = []
        registry = {
            "client_a": (None, lambda c: order.append("a")),
            "client_b": (None, AsyncMock(side_effect=lambda c: order.append("b"))),
            "client_c": (None, None),
            "client_d": (None, lambda c: order.append("d")),
        }
        await func_client_close(registry=registry, clients={"client_a": object(), "client_b": object(), "client_c": object(), "client_d": None})
        self.assertEqual(order, ["b", "a"])

    async def test_one_failing_close_does_not_stop_the_others(self):
        closed = MagicMock()
        registry = {"client_ok": (None, closed), "client_bad": (None, MagicMock(side_effect=RuntimeError("boom")))}
        await func_client_close(registry=registry, clients={"client_ok": "ok", "client_bad": "bad"})
        closed.assert_called_once_with("ok")


if __name__ == "__main__":
    unittest.main()
