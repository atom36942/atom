"""Route keys ip_allow and token_verify: callers that can't sign (some device and IoT clouds) are checked by IP and a shared token."""
import unittest
from types import SimpleNamespace
from fastapi import FastAPI
import config
from function import func_check_api_config
from function import func_check_database_config
from function import func_middleware_check_ip_allow
from function import func_middleware_check_token_verify


class IpAllowTests(unittest.TestCase):
    def test_listed_addresses_and_ranges_pass(self):
        for client_ip in ("203.0.113.9", "198.51.100.7", "2001:db8::5"):
            with self.subTest(client_ip=client_ip): func_middleware_check_ip_allow(client_ip=client_ip, ip_allow=["203.0.113.0/24", "198.51.100.7", "2001:db8::/32"])

    def test_other_missing_or_invalid_addresses_get_403(self):
        for client_ip in ("203.0.114.1", None, "", "testclient"):
            with self.subTest(client_ip=client_ip), self.assertRaisesRegex(Exception, "caller ip not allowed") as raised:
                func_middleware_check_ip_allow(client_ip=client_ip, ip_allow=["203.0.113.0/24"])
            self.assertEqual(raised.exception.status_code, 403)


class TokenVerifyTests(unittest.TestCase):
    def request(self, headers=None, query=None):
        return SimpleNamespace(headers=headers or {}, query_params=query or {})

    def test_header_token(self):
        verify = {"secret": "config_webhook_token_devices"}
        func_middleware_check_token_verify(request=self.request(headers={"x-webhook-token": "s3cret"}), token_verify=verify, secret="s3cret")
        for headers in ({}, {"x-webhook-token": "wrong"}, {"x-other": "s3cret"}):
            with self.subTest(headers=headers), self.assertRaisesRegex(Exception, "invalid token") as raised:
                func_middleware_check_token_verify(request=self.request(headers=headers), token_verify=verify, secret="s3cret")
            self.assertEqual(raised.exception.status_code, 403)

    def test_query_token_with_its_own_name(self):
        verify = {"secret": "config_webhook_token_devices", "in": "query", "name": "push_token"}
        func_middleware_check_token_verify(request=self.request(query={"push_token": "s3cret"}), token_verify=verify, secret="s3cret")
        with self.assertRaisesRegex(Exception, "invalid token"):
            func_middleware_check_token_verify(request=self.request(query={"token": "s3cret"}), token_verify=verify, secret="s3cret")

    def test_unset_secret_is_a_server_error_not_an_open_route(self):
        with self.assertRaisesRegex(Exception, "token secret not set: config_webhook_token_devices") as raised:
            func_middleware_check_token_verify(request=self.request(headers={"x-webhook-token": ""}), token_verify={"secret": "config_webhook_token_devices"}, secret=None)
        self.assertEqual(raised.exception.status_code, 500)


class CallerConfigCheckTests(unittest.TestCase):
    def app(self, cfg):
        app = FastAPI(openapi_url=None, docs_url=None, redoc_url=None)
        app.post("/device/push")(lambda: None)
        app.state.config_api = {"/device/push": {"id": 200, "auth": [], **cfg}}
        app.state.config_uvicorn_workers = 1
        app.state.config_webhook_verify_scheme = config.config_webhook_verify_scheme
        return app

    def test_valid_entries_pass(self):
        for cfg in ({"ip_allow": ["203.0.113.0/24", "2001:db8::1"]}, {"token_verify": {"secret": "config_webhook_token_devices"}},
                    {"token_verify": {"secret": "config_webhook_token_devices", "in": "query", "name": "token"}}, {"ip_allow": ["10.0.0.1"], "token_verify": {"secret": "config_x", "in": "header", "name": "x-push-token"}}):
            with self.subTest(cfg=cfg): func_check_api_config(app=self.app(cfg))

    def test_invalid_entries_stop_startup(self):
        for cfg, message in (({"ip_allow": []}, "invalid ip_allow"), ({"ip_allow": "10.0.0.1"}, "invalid ip_allow"), ({"ip_allow": ["10.0.0.300"]}, "invalid ip_allow entry"),
                             ({"token_verify": {"in": "header"}}, "invalid token_verify"), ({"token_verify": {"secret": "s3cret"}}, "secret must name a config_ setting"),
                             ({"token_verify": {"secret": "config_x", "in": "body"}}, "in must be header or query"), ({"token_verify": {"secret": "config_x", "name": "bad name"}}, "invalid name"),
                             ({"token_verify": {"secret": "config_x", "in": "query", "name": "key"}}, "must contain 'token'"), ({"token_verify": {"secret": "config_x", "extra": 1}}, "invalid token_verify")):
            with self.subTest(cfg=cfg), self.assertRaisesRegex(Exception, message): func_check_api_config(app=self.app(cfg))


class BufferIntervalConfigCheckTests(unittest.TestCase):
    def state(self, **settings):
        return SimpleNamespace(config_postgres_url_dict={"master": "postgresql://x", "telemetry": "postgresql://y"}, config_postgres_pool_min_size=1, config_postgres_pool_max_size=5, **settings)

    def test_an_interval_per_database(self):
        func_check_database_config(app_state=self.state(config_postgres_buffer_flush_auto_sec_telemetry=2))

    def test_an_unknown_database_or_bad_value_stops_startup(self):
        with self.assertRaisesRegex(Exception, r"config_postgres_buffer_flush_auto_sec_telemtry: no database named telemtry"):
            func_check_database_config(app_state=self.state(config_postgres_buffer_flush_auto_sec_telemtry=2))
        with self.assertRaisesRegex(Exception, "invalid config_postgres_buffer_flush_auto_sec_telemetry: minimum 1"):
            func_check_database_config(app_state=self.state(config_postgres_buffer_flush_auto_sec_telemetry=0))


if __name__ == "__main__":
    unittest.main()
