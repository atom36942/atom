"""Webhooks end to end: admin create, send in the caller's transaction, signed delivery, retry, failure, skips.

Same real-app boot as test_http.py (support.app_start), against a throwaway database. Deliveries go to an
httpx.MockTransport, and the URL check is patched where a test needs a local URL, so nothing leaves the machine.
"""
import asyncio
import unittest
from unittest.mock import AsyncMock
from unittest.mock import patch

import asyncpg
import httpx
import orjson

import function.webhook as webhook
from tests.integration.support import app_login
from tests.integration.support import app_start
from tests.integration.support import app_stop
from tests.integration.support import create_database
from tests.integration.support import drop_database
from tests.integration.support import fetch
from tests.integration.support import requires_postgres

URL = "https://partner.test/hook"
SECRET = webhook.func_webhook_secret_create()    # made per run: no secret-shaped string in the repo


@requires_postgres
class WebhookTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db_name, cls.url = create_database()
        cls.handle = app_start(env={"config_postgres_url_master": cls.url})
        cls.app, cls.client = cls.handle["app"], cls.handle["client"]
        cls.admin = {"Authorization": "Bearer " + app_login(cls.client, path="/auth/login-username-password", body={"username": "admin", "password": "root-test-password"})}
        cls.alice = {"Authorization": "Bearer " + app_login(cls.client, path="/auth/signup-username-password", body={"role": 5, "username": "alice", "password": "alice-pass"})}

    @classmethod
    def tearDownClass(cls):
        try: app_stop(cls.handle)
        finally: drop_database(cls.db_name)

    def setUp(self):
        fetch(self.url, "DELETE FROM queue_job WHERE channel = 'channel_webhook'")
        fetch(self.url, "DELETE FROM webhook")
        self.requests = []
        self.answer = 200

    def message(self, response, status=200):
        self.assertEqual(response.status_code, status, response.text)
        return response.json()["message"]

    def webhook_add(self, events, is_active=True, url=URL):
        return fetch(self.url, "INSERT INTO webhook (created_by_id, url, events, secret, is_active) VALUES (1, $1, $2, $3, $4) RETURNING id", url, events, SECRET, is_active)[0]["id"]

    def jobs(self):
        return fetch(self.url, "SELECT payload, status, attempt, error FROM queue_job WHERE channel = 'channel_webhook' ORDER BY id")

    def run_async(self, steps):
        async def run():
            pool = await asyncpg.create_pool(self.url, min_size=1, max_size=3)
            def receive(request):
                self.requests.append(request)
                return httpx.Response(self.answer)
            http = httpx.AsyncClient(transport=httpx.MockTransport(receive))
            try: return await steps(pool, http)
            finally:
                await http.aclose()
                await pool.close()
        return asyncio.run(run())

    def take(self, pool, http, retry_max=3):
        async def run(payload):
            try: await webhook.func_webhook_deliver(client_postgres=pool, client_http=http, payload=payload, timeout_sec=5)
            except Exception as e: return e
        return webhook.func_queue_postgres_job_take(client_postgres=pool, channel="channel_webhook", run=run, retry_max=retry_max, retry_wait_sec=60)

    def test_admin_creates_a_webhook_and_sees_its_secret_once(self):
        with patch.object(webhook, "func_webhook_url_check", AsyncMock(return_value=URL)):
            created = self.message(self.client.post("/admin/webhook-create", json={"url": URL, "events": ["shipment.delivered", "shipment.delivered"]}, headers=self.admin))
        self.assertTrue(created["secret"].startswith("whsec_"))
        self.assertEqual((created["events"], created["is_active"]), (["shipment.delivered"], True))
        [row] = self.message(self.client.get("/admin/object-read", params={"table": "webhook"}, headers=self.admin))["obj_list"]
        self.assertNotIn("secret", row)
        self.assertIn("https", self.message(self.client.post("/admin/webhook-create", json={"url": "http://partner.test/hook", "events": ["a"]}, headers=self.admin), 400))
        self.assertIn("invalid webhook event", self.message(self.client.post("/admin/webhook-create", json={"url": URL, "events": ["Bad Event"]}, headers=self.admin), 400))
        self.assertEqual(self.client.post("/admin/webhook-create", json={"url": URL, "events": ["a"]}, headers=self.alice).status_code, 403)
        self.assertEqual(self.client.post("/my/object-create", params={"table": "webhook"}, json={"url": URL, "events": ["a"], "secret": "x"}, headers=self.alice).status_code, 400)

    def test_send_queues_one_delivery_per_active_subscriber_and_delivers_it_signed(self):
        self.webhook_add(["shipment.delivered", "shipment.created"])
        self.webhook_add(["shipment.created"])
        self.webhook_add(["shipment.delivered"], is_active=False)
        async def steps(pool, http):
            queued = await webhook.func_webhook_send(client_postgres=pool, event="shipment.delivered", data={"shipment_id": 881})
            with patch.object(webhook, "func_webhook_url_check", AsyncMock(return_value=URL)): outcome = await self.take(pool, http)
            return queued, outcome
        self.assertEqual(self.run_async(steps), (1, "done"))
        self.assertEqual(self.jobs(), [])
        [request] = self.requests
        self.assertEqual(str(request.url), URL)
        body = orjson.loads(request.content)
        self.assertEqual((body["type"], body["data"]), ("shipment.delivered", {"shipment_id": 881}))
        self.assertTrue(request.headers["webhook-id"].startswith("msg_"))
        expected = webhook.func_webhook_sign(secret=SECRET, message_id=request.headers["webhook-id"], timestamp=int(request.headers["webhook-timestamp"]), body=request.content)
        self.assertEqual(request.headers["webhook-signature"], expected)

    def test_a_failing_receiver_is_retried_then_kept_as_failed_with_its_error(self):
        self.webhook_add(["task.closed"])
        self.answer = 500
        async def steps(pool, http):
            await webhook.func_webhook_send(client_postgres=pool, event="task.closed", data={})
            with patch.object(webhook, "func_webhook_url_check", AsyncMock(return_value=URL)):
                first = await self.take(pool, http, retry_max=1)
                await pool.execute("UPDATE queue_job SET run_at = now() WHERE channel = 'channel_webhook'")
                second = await self.take(pool, http, retry_max=1)
            return first, second
        self.assertEqual(self.run_async(steps), ("retry", "failed"))
        [job] = self.jobs()
        self.assertEqual((job["status"], job["attempt"], job["error"]), (2, 2, "Exception: webhook answered 500"))
        self.assertEqual(len({r.headers["webhook-id"] for r in self.requests}), 1)    # a retry keeps its id, so the receiver can drop a duplicate

    def test_rollback_queues_nothing(self):
        self.webhook_add(["task.closed"])
        async def steps(pool, http):
            async with pool.acquire() as conn:
                try:
                    async with conn.transaction():
                        self.assertEqual(await webhook.func_webhook_send(client_postgres=conn, event="task.closed", data={}), 1)
                        raise RuntimeError("the change failed")
                except RuntimeError: pass
        self.run_async(steps)
        self.assertEqual(self.jobs(), [])

    def test_a_webhook_turned_off_after_sending_is_skipped_and_a_private_url_is_refused(self):
        off = self.webhook_add(["a"])
        self.webhook_add(["b"], url="https://127.0.0.1/hook")
        async def steps(pool, http):
            await webhook.func_webhook_send(client_postgres=pool, event="a", data={})
            await pool.execute("UPDATE webhook SET is_active = false WHERE id = $1", off)
            skipped = await self.take(pool, http)
            await webhook.func_webhook_send(client_postgres=pool, event="b", data={})
            refused = await self.take(pool, http)
            return skipped, refused
        self.assertEqual(self.run_async(steps), ("done", "retry"))
        self.assertEqual(self.requests, [])
        self.assertIn("not public", self.jobs()[0]["error"])


if __name__ == "__main__":
    unittest.main()
