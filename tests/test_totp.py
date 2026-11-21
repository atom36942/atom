"""2FA (TOTP) building blocks: RFC 6238 codes, clock drift, secret encryption, the otpauth link, recovery codes and the mfa token."""
import time
import unittest

import jwt

from function import func_mfa_token_decode
from function import func_mfa_token_encode
from function import func_totp_code
from function import func_totp_decrypt
from function import func_totp_encrypt
from function import func_totp_key
from function import func_totp_match
from function import func_totp_recovery_create
from function import func_totp_recovery_hash
from function import func_totp_uri

RFC_SECRET = b"12345678901234567890"    # RFC 6238 Appendix B, SHA-1
KEY = func_totp_key(config_totp_encryption_key="k" * 32)
JWT_KEY = "atom-test-secret-key-at-least-32-bytes"


class TotpCodeTests(unittest.TestCase):
    def test_rfc_6238_test_vectors(self):
        for at, code in ((59, "287082"), (1111111109, "081804"), (1111111111, "050471"), (1234567890, "005924"), (2000000000, "279037"), (20000000000, "353130")):
            with self.subTest(at=at): self.assertEqual(func_totp_code(secret=RFC_SECRET, step=at // 30), code)

    def test_one_step_of_drift_each_way_and_no_more(self):
        now = 1234567890
        for offset, expected in ((-30, now // 30 - 1), (0, now // 30), (30, now // 30 + 1)):
            with self.subTest(offset=offset): self.assertEqual(func_totp_match(secret=RFC_SECRET, code=func_totp_code(secret=RFC_SECRET, step=(now + offset) // 30), now=now), expected)
        self.assertIsNone(func_totp_match(secret=RFC_SECRET, code=func_totp_code(secret=RFC_SECRET, step=now // 30 + 2), now=now))
        self.assertIsNone(func_totp_match(secret=RFC_SECRET, code="000000", now=now))


class TotpSecretTests(unittest.TestCase):
    def test_encrypted_secret_reads_back_only_with_its_key_and_user(self):
        value = func_totp_encrypt(key=KEY, user_id=42, secret=RFC_SECRET)
        self.assertNotIn("1234567890", value)
        self.assertEqual(func_totp_decrypt(key=KEY, user_id=42, value=value), RFC_SECRET)
        for label, kwargs in (("other user", {"key": KEY, "user_id": 43}), ("other key", {"key": func_totp_key(config_totp_encryption_key="x" * 32), "user_id": 42})):
            with self.subTest(label), self.assertRaisesRegex(Exception, "cannot be read"): func_totp_decrypt(value=value, **kwargs)

    def test_key_is_required_and_long(self):
        with self.assertRaisesRegex(Exception, "2FA not configured"): func_totp_key(config_totp_encryption_key=None)
        with self.assertRaisesRegex(Exception, "32 characters"): func_totp_key(config_totp_encryption_key="short")

    def test_otpauth_link_uses_the_defaults_every_app_reads(self):
        self.assertEqual(func_totp_uri(secret=RFC_SECRET, issuer="pulse", username="ravi@x.com"), "otpauth://totp/pulse:ravi@x.com?secret=GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQ&issuer=pulse&algorithm=SHA1&digits=6&period=30")

    def test_recovery_codes(self):
        codes, hashes = func_totp_recovery_create(key=KEY)
        self.assertEqual((len(codes), len(set(codes))), (10, 10))
        self.assertRegex(codes[0], r"^[A-HJ-NP-Z2-9]{5}-[A-HJ-NP-Z2-9]{5}$")
        self.assertEqual(func_totp_recovery_hash(key=KEY, code=codes[0].lower().replace("-", " ")), hashes[0])    # case, dash and spaces don't matter
        self.assertNotEqual(func_totp_recovery_hash(key=func_totp_key(config_totp_encryption_key="x" * 32), code=codes[0]), hashes[0])


class MfaTokenTests(unittest.TestCase):
    def test_round_trip_and_refusals(self):
        self.assertEqual(func_mfa_token_decode(mfa_token=func_mfa_token_encode(user_id=42, config_token_secret_key=JWT_KEY), config_token_secret_key=JWT_KEY), 42)
        access = jwt.encode({"exp": int(time.time()) + 60, "data": '{"id": 42}', "type": "access"}, JWT_KEY)
        expired = jwt.encode({"exp": 1, "data": '{"id": 42}', "type": "mfa"}, JWT_KEY)
        for label, token in (("an access token", access), ("expired", expired), ("garbage", "x"), ("other key", func_mfa_token_encode(user_id=42, config_token_secret_key="y" * 40))):
            with self.subTest(label), self.assertRaisesRegex(Exception, "mfa token invalid or expired"): func_mfa_token_decode(mfa_token=token, config_token_secret_key=JWT_KEY)


if __name__ == "__main__":
    unittest.main()
