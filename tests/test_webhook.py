"""Webhook signing in the Standard Webhooks format, event names and the URL check (no network: IP literals only)."""
import base64
import unittest

from function import func_webhook_event_check
from function import func_webhook_secret_create
from function import func_webhook_sign
from function import func_webhook_url_check


class WebhookSignTests(unittest.TestCase):
    def test_signature_matches_the_standard_webhooks_test_vector(self):
        signature = func_webhook_sign(secret="whsec_MfKQ9r8GKYqrTwjUPD8ILPZIo2LaLaSw", message_id="msg_p5jXN8AQM9LWM0D4loKWxJek", timestamp=1614265330, body=b'{"test": 2432232314}')
        self.assertEqual(signature, "v1,g0hM9SsE+OTPJTGt/tmIKtSyZlE3uFJELVlNIOLJ1OE=")

    def test_a_new_secret_is_32_random_bytes_after_whsec(self):
        first, second = func_webhook_secret_create(), func_webhook_secret_create()
        self.assertTrue(first.startswith("whsec_"))
        self.assertEqual(len(base64.b64decode(first.removeprefix("whsec_"))), 32)
        self.assertNotEqual(first, second)

    def test_event_names(self):
        for event in ("shipment.delivered", "task-closed", "invoice_sla.breached"): func_webhook_event_check(event=event)
        for event in ("", "Shipment.Delivered", "a b", "x" * 101, None):
            with self.subTest(event=event), self.assertRaisesRegex(Exception, "invalid webhook event"): func_webhook_event_check(event=event)


class WebhookUrlTests(unittest.IsolatedAsyncioTestCase):
    async def test_only_https_to_a_public_address(self):
        self.assertEqual(await func_webhook_url_check(url="https://93.184.215.14/hook"), "https://93.184.215.14/hook")
        for url, message in (("http://93.184.215.14/hook", "must be https"), ("ftp://x/", "must be https"), ("", "must be https"),
                             ("https://127.0.0.1/", "not public"), ("https://10.1.2.3/", "not public"), ("https://192.168.0.5:8443/", "not public"),
                             ("https://169.254.169.254/latest/meta-data", "not public"), ("https://[::1]/", "not public"), ("https://0.0.0.0/", "not public")):
            with self.subTest(url=url), self.assertRaisesRegex(Exception, message): await func_webhook_url_check(url=url)


if __name__ == "__main__":
    unittest.main()
