"""The SFTP client checks the server's key by default (known_hosts), so a server pretending to be it is refused; turning the check off is explicit."""
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock
from unittest.mock import patch

from function.clients import func_client_sftp


class SftpClientTests(unittest.IsolatedAsyncioTestCase):
    async def known_hosts_passed(self, **kwargs):
        connect = AsyncMock(return_value="conn")
        with patch.dict(sys.modules, {"asyncssh": SimpleNamespace(connect=connect)}):
            await func_client_sftp(host="sftp.example.test", port=22, username="u", password="p", **kwargs)    # noqa: S106 - test value
        return connect.await_args.kwargs["known_hosts"]

    async def test_the_server_key_is_checked_by_default(self):
        self.assertEqual(await self.known_hosts_passed(), ())

    async def test_a_known_hosts_file_can_be_named(self):
        self.assertEqual(await self.known_hosts_passed(known_hosts_path="secret/known_hosts"), "secret/known_hosts")

    async def test_turning_the_check_off_is_explicit(self):
        self.assertIsNone(await self.known_hosts_passed(is_host_verify=False))

    async def test_no_host_no_connection(self):
        self.assertIsNone(await func_client_sftp(host=None, port=None, username=None, password=None))


if __name__ == "__main__":
    unittest.main()
