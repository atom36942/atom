"""Webhook signing in the Standard Webhooks format, event names, the URL check (no network: IP literals only) and incoming signature verification."""
import base64
import hashlib
import hmac
import unittest

import config

from function import func_webhook_event_check
from function import func_webhook_secret_create
from function import func_webhook_sign
from function import func_webhook_url_check
from function import func_webhook_verify
from function import func_webhook_verify_scheme_check


SPEC_SECRET = "whsec_" + "MfKQ9r8GKYqrTwjUPD8ILPZIo2LaLaSw"    # the Standard Webhooks spec's public test vector, split so secret scanners don't take it for a live key


class WebhookSignTests(unittest.TestCase):
    def test_signature_matches_the_standard_webhooks_test_vector(self):
        signature = func_webhook_sign(secret=SPEC_SECRET, message_id="msg_p5jXN8AQM9LWM0D4loKWxJek", timestamp=1614265330, body=b'{"test": 2432232314}')
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


class WebhookVerifyTests(unittest.TestCase):
    """Each preset in config_webhook_verify_scheme against a signature made independently with hmac (or the provider's published example)."""
    @staticmethod
    def hmac_of(secret, signed, encoding):
        digest = hmac.new(secret, signed, hashlib.sha256).digest()
        return digest.hex() if encoding == "hex" else base64.b64encode(digest).decode()

    def verify(self, scheme, secret, headers, body=b'{"a":1}', now=1700000000):
        return func_webhook_verify(scheme=config.config_webhook_verify_scheme[scheme], secret=secret, headers=headers, body=body, tolerance_sec=300, now=now)

    def test_standard_webhooks_spec_example(self):
        headers = {"webhook-id": "msg_p5jXN8AQM9LWM0D4loKWxJek", "webhook-timestamp": "1614265330", "webhook-signature": "v1,bad v1,g0hM9SsE+OTPJTGt/tmIKtSyZlE3uFJELVlNIOLJ1OE="}
        self.assertEqual(self.verify("standard", SPEC_SECRET, headers, body=b'{"test": 2432232314}', now=1614265330), {"id": "msg_p5jXN8AQM9LWM0D4loKWxJek", "timestamp": 1614265330})

    def test_github_docs_example(self):
        headers = {"X-Hub-Signature-256": "sha256=757107ea0eb2509fc211221cce984b8a37570b6d7586c22c46f4379c8b043e17"}
        self.assertEqual(self.verify("github", "It's a Secret to Everybody", headers, body=b"Hello, World!"), {"id": None, "timestamp": None})

    def test_stripe_shopify_razorpay(self):
        body, secret = b'{"id":"evt_1"}', "s3cret"
        stripe = {"Stripe-Signature": f"t=1700000000,v1={self.hmac_of(secret.encode(), b'1700000000.' + body, 'hex')},v0=ignored"}
        self.assertEqual(self.verify("stripe", secret, stripe, body=body)["timestamp"], 1700000000)
        self.verify("shopify", secret, {"X-Shopify-Hmac-Sha256": self.hmac_of(secret.encode(), body, "base64")}, body=body)
        self.verify("razorpay", secret, {"X-Razorpay-Signature": self.hmac_of(secret.encode(), body, "hex")}, body=body)

    def test_refusals_are_401(self):
        body, secret = b'{"id":"evt_1"}', "s3cret"
        good = {"Stripe-Signature": f"t=1700000000,v1={self.hmac_of(secret.encode(), b'1700000000.' + body, 'hex')}"}
        for label, kwargs, message in (
            ("wrong secret", {"scheme": "stripe", "secret": "other", "headers": good, "body": body}, "does not match"),
            ("changed body", {"scheme": "stripe", "secret": secret, "headers": good, "body": body + b" "}, "does not match"),
            ("old timestamp", {"scheme": "stripe", "secret": secret, "headers": good, "body": body, "now": 1700000301}, "too old"),
            ("no header", {"scheme": "stripe", "secret": secret, "headers": {}, "body": body}, "Stripe-Signature header missing"),
            ("no timestamp", {"scheme": "stripe", "secret": secret, "headers": {"Stripe-Signature": "v1=abc"}, "body": body}, "timestamp missing"),
            ("prefix missing", {"scheme": "github", "secret": secret, "headers": {"X-Hub-Signature-256": self.hmac_of(secret.encode(), body, "hex")}, "body": body}, "does not match"),
        ):
            with self.subTest(label), self.assertRaisesRegex(Exception, message) as caught: self.verify(**kwargs)
            self.assertEqual(caught.exception.status_code, 401)

    def test_scheme_check(self):
        for name, scheme in config.config_webhook_verify_scheme.items(): func_webhook_verify_scheme_check(name=name, scheme=scheme)
        base = {"header": "X-Sig", "encoding": "hex", "signed": "{body}"}
        for change, message in (({"encoding": "b64"}, "encoding must be hex or base64"), ({"signed": "{body}.{timestamp}"}, "must end with"), ({"signed": "{timestamp}.{body}"}, "needs timestamp"),
                                ({"signed": "{nonce}.{body}"}, "only {id}"), ({"colour": 1}, "unknown field colour"), ({"timestamp": {"query": "t"}}, "timestamp must be"),
                                ({"timestamp": {"key": "t"}}, "needs key"), ({"header": ""}, "header must"), ({"secret_encoding": "hex"}, "secret_encoding")):
            with self.subTest(change=change), self.assertRaisesRegex(Exception, message): func_webhook_verify_scheme_check(name="x", scheme={**base, **change})
