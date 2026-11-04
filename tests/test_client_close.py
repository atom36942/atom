"""func_client_close closes the clients a real Starlette State holds (its values are not in dir()), and a plain dict of clients from a failed startup."""
import unittest
from unittest.mock import AsyncMock
from unittest.mock import MagicMock

from starlette.datastructures import State

from function.clients import func_client_close


class ClientCloseTests(unittest.IsolatedAsyncioTestCase):
    async def test_clients_on_a_real_state_are_closed(self):
        state = State()
        state.client_http = MagicMock(aclose=AsyncMock())
        pool = MagicMock(close=AsyncMock())
        state.client_postgres_dict = {"master": pool}
        state.config_x = 1
        await func_client_close(app_state=state)
        state.client_http.aclose.assert_awaited_once()
        pool.close.assert_awaited_once()

    async def test_clients_from_a_failed_startup_are_closed(self):
        client_http = MagicMock(aclose=AsyncMock())
        await func_client_close(clients={"client_http": client_http, "client_postgres_dict": {}})
        client_http.aclose.assert_awaited_once()


if __name__ == "__main__":
    unittest.main()
