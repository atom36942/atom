"""Regression cases for the SQL, storage, and credential-handling audit."""
import io
from contextlib import redirect_stderr
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

import asyncpg
import httpx
from starlette.datastructures import QueryParams
from function import (
    func_postgres_query_runner_read, func_mssql_query_runner_read,
    func_mssql_query_runner_read_export, func_clickhouse_query_runner_read,
    func_clickhouse_query_runner_read_export, func_postgres_relation,
    func_blob_upload_file, func_blob_preview_urls_get, func_blob_upload_url,
    func_middleware_log_query_params, func_middleware_api_response_error,
    func_middleware_check_role,
)
from tests.support import database


class SecurityTests(unittest.IsolatedAsyncioTestCase):
    async def test_mssql_read_and_export_reject_batches_and_permission_changes(self):
        client = MagicMock()
        for sql in ("SELECT 1; GRANT CONTROL TO public", "SELECT 1 GRANT CONTROL TO public",
                    "SELECT 1 REVOKE SELECT TO public", "SELECT 1 DENY SELECT TO public",
                    "SELECT 1; WAITFOR DELAY '00:01:00'", "SELECT * FROM OPENROWSET('provider','secret','query')"):
            for runner, limit in ((func_mssql_query_runner_read, "config_query_runner_read_limit"),
                                  (func_mssql_query_runner_read_export, "config_query_runner_export_limit")):
                with self.subTest(sql=sql, runner=runner.__name__), self.assertRaises(Exception):
                    await runner(client_mssql=client, sql=sql, **{limit: 10})
        client.acquire.assert_not_called()

    async def test_postgres_read_uses_readonly_transaction_and_bounded_query(self):
        pool, conn = database()
        statement = MagicMock()
        statement.fetch = AsyncMock(return_value=[{"id": 1}])
        conn.prepare = AsyncMock(return_value=statement)
        self.assertEqual(await func_postgres_query_runner_read(client_postgres=pool,
                         config_query_runner_read_limit=10, sql="SELECT id FROM product"), [{"id": 1}])
        conn.transaction.assert_called_once_with(readonly=True)
        self.assertIn("LIMIT $1", conn.prepare.await_args.args[0])
        statement.fetch.assert_awaited_once_with(10, timeout=30)
        self.assertIn("statement_timeout", conn.execute.await_args.args[0])

    async def test_clickhouse_read_and_export_request_readonly_timeout(self):
        client = MagicMock()
        client.query = AsyncMock(return_value=SimpleNamespace(column_names=["id"], result_rows=[(1,)]))
        self.assertEqual(await func_clickhouse_query_runner_read(client_clickhouse=client,
                         config_query_runner_read_limit=10, sql="SELECT id FROM product"), [{"id": 1}])
        self.assertEqual(client.query.await_args.kwargs["settings"], {"readonly": 1, "max_execution_time": 30})
        stream = MagicMock()
        stream.__aiter__.return_value = [b"id\n1\n"]
        client.raw_stream = AsyncMock(return_value=stream)
        output = await func_clickhouse_query_runner_read_export(client_clickhouse=client,
                        config_query_runner_export_limit=20, sql="SELECT id FROM product")
        self.assertEqual([chunk async for chunk in output], [b"id\n1\n"])
        self.assertEqual(client.raw_stream.await_args.kwargs["settings"], {"readonly": 1, "max_execution_time": 30})

    async def test_relations_cannot_join_on_secrets_or_bypass_wildcard_block(self):
        client = MagicMock()
        for relation, blocked in [("id,users,password,count,*", []),
                                  ("password,users,id,count,*", []), ("id,users,id,count,*", ["*"])]:
            with self.subTest(relation=relation, blocked=blocked), self.assertRaisesRegex(Exception, "restricted|disabled"):
                await func_postgres_relation(client_postgres=client, obj_list=[{"id": 1, "password": "secret"}],
                    relation=[relation], config_sql_read_relation_fetch_limit_max=10, blocked_tables=blocked)
        client.fetch.assert_not_called()

    def storage_state(self):
        return SimpleNamespace(client_postgres=object(), client_s3=SimpleNamespace(put_object=AsyncMock()),
            client_azure_blob=None, config_blob_limit_upload=2, config_blob_limit_size_kb=1,
            config_aws_s3_region_name="ap-south-1",
            func_postgres_create=AsyncMock(), client_password_hasher=None, func_postgres_serialize=None,
            func_regex_check=None, cache_postgres_schema={}, cache_postgres_buffer_create={},
            config_column_regex={}, config_buffer_limit_default=10)

    async def test_oversized_upload_reads_only_limit_plus_one_and_does_not_upload(self):
        state = self.storage_state()
        file = SimpleNamespace(filename="file.txt", read=AsyncMock(return_value=b"x" * 1025))
        with self.assertRaisesRegex(Exception, "file size exceeds"):
            await func_blob_upload_file(app_state=state, service="s3", container="bucket", files=[file], user_id=7)
        file.read.assert_awaited_once_with(1025)
        state.client_s3.put_object.assert_not_awaited()
        state.func_postgres_create.assert_not_awaited()

    async def test_upload_cannot_inject_path_segments_through_extension(self):
        state = self.storage_state()
        file = SimpleNamespace(filename="name.txt/../../other", read=AsyncMock(return_value=b"file"))
        result = await func_blob_upload_file(app_state=state, service="s3", container="bucket", files=[file], user_id=7)
        key = state.client_s3.put_object.await_args.kwargs["Key"]
        self.assertRegex(key, r"^user_7/[a-f0-9]{32}\.bin$")
        expected_url = f"https://bucket.s3.ap-south-1.amazonaws.com/{key}"
        self.assertEqual(result[file.filename], expected_url)
        self.assertEqual(state.func_postgres_create.await_args.kwargs["obj_list"][0]["file_url"], expected_url)

    async def test_private_previews_reject_other_users_before_signing(self):
        client = SimpleNamespace(generate_presigned_url=AsyncMock(return_value="signed"))
        args = dict(client_s3=client, client_azure_blob=MagicMock(), config_azure_account_name="account",
                    config_azure_account_key="dummy", config_blob_expire_sec_preview=60, user_id=7)
        for service, url in [("s3", "https://bucket.s3.amazonaws.com/user_8/file.bin"),
                             ("s3", "https://bucket.s3.amazonaws.com/user_70/file.bin"),
                             ("azure", "https://account.blob.core.windows.net/container/user_8/file.bin")]:
            with self.subTest(service=service, url=url), patch("azure.storage.blob.generate_blob_sas") as sign:
                with self.assertRaisesRegex(Exception, "only for own files"):
                    await func_blob_preview_urls_get(**args, service=service, urls=[url])
                sign.assert_not_called()
        client.generate_presigned_url.assert_not_awaited()
        url = "https://bucket.s3.amazonaws.com/user_7/file.bin"
        self.assertEqual(await func_blob_preview_urls_get(**args, service="s3", urls=[url]), ["signed"])
        client.generate_presigned_url.assert_awaited_once()

    async def test_container_sas_checks_current_admin_role_before_signing(self):
        from router.admin import func_api_admin_blob_container_sas
        pool, conn = database()
        conn.fetch.return_value = [{"role": 5}]
        state = SimpleNamespace(client_postgres=pool, func_middleware_check_role=func_middleware_check_role)
        request = SimpleNamespace(app=SimpleNamespace(state=state), state=SimpleNamespace(user={"id": 7, "role": 1}))
        with patch("router.admin.generate_container_sas") as sign:
            with self.assertRaisesRegex(Exception, "access denied"):
                await func_api_admin_blob_container_sas(request=request)
            sign.assert_not_called()
        self.assertEqual(conn.fetch.await_args.args[1:], (7,))

    async def test_preview_lists_preserve_order_and_duplicates_for_both_services(self):
        keys = ["user_7/b.pdf", "user_7/a.pdf", "user_7/b.pdf"]
        client = SimpleNamespace(generate_presigned_url=AsyncMock(
            side_effect=lambda **kwargs: "signed/" + kwargs["Params"]["Key"]))
        args = dict(client_s3=client, client_azure_blob=MagicMock(), config_azure_account_name="account",
                    config_azure_account_key="dummy", config_blob_expire_sec_preview=60, user_id=7)
        result = await func_blob_preview_urls_get(**args, service="s3",
                    urls=["https://bucket.s3.ap-south-1.amazonaws.com/" + key for key in keys])
        self.assertEqual(result, ["signed/" + key for key in keys])
        self.assertEqual(client.generate_presigned_url.await_count, 3)
        with patch("azure.storage.blob.generate_blob_sas", return_value="signature") as sign:
            urls = ["https://account.blob.core.windows.net/container/" + key for key in keys]
            self.assertEqual(await func_blob_preview_urls_get(**args, service="azure", urls=urls),
                             [url + "?signature" for url in urls])
            self.assertEqual(sign.call_count, 3)

    async def test_invalid_preview_entry_fails_whole_batch_before_signing(self):
        client = SimpleNamespace(generate_presigned_url=AsyncMock(return_value="signed"))
        args = dict(client_s3=client, client_azure_blob=MagicMock(), config_azure_account_name="account",
                    config_azure_account_key="dummy", config_blob_expire_sec_preview=60, user_id=7)
        for service, valid in [("s3", "https://bucket.s3.amazonaws.com/user_7/file"),
                               ("azure", "https://account.blob.core.windows.net/container/user_7/file")]:
            for invalid in ("", None, 123, "not-a-url", "https://s3.amazonaws.com/", valid.replace("user_7", "user_8")):
                with self.subTest(service=service, invalid=invalid), patch("azure.storage.blob.generate_blob_sas") as sign:
                    with self.assertRaises(Exception):
                        await func_blob_preview_urls_get(**args, service=service, urls=[valid, invalid])
                    sign.assert_not_called()
        client.generate_presigned_url.assert_not_awaited()

    async def test_preview_signer_failure_returns_no_partial_list(self):
        client = SimpleNamespace(generate_presigned_url=AsyncMock(side_effect=["signed", RuntimeError("signing failed")]))
        with self.assertRaisesRegex(RuntimeError, "signing failed"):
            await func_blob_preview_urls_get(client_s3=client, client_azure_blob=None,
                config_azure_account_name=None, config_azure_account_key=None, config_blob_expire_sec_preview=60,
                service="s3", user_id=7, urls=["https://bucket.s3.amazonaws.com/user_7/a", "https://bucket.s3.amazonaws.com/user_7/b"])

    async def test_preview_route_passes_authenticated_owner(self):
        from router.my import func_api_my_blob_preview_urls
        state = SimpleNamespace(func_request_param_read=AsyncMock(return_value={"service": "s3", "urls": ["file"]}),
            func_blob_preview_urls_get=AsyncMock(return_value=["signed"]), client_s3=None, client_azure_blob=None,
            config_blob_services=["s3"], config_azure_account_name=None, config_azure_account_key=None,
            config_blob_expire_sec_preview=60)
        request = SimpleNamespace(app=SimpleNamespace(state=state), state=SimpleNamespace(user={"id": 7}))
        response = await func_api_my_blob_preview_urls(request=request)
        self.assertEqual(response, {"status": 1, "message": ["signed"]})
        self.assertEqual(state.func_blob_preview_urls_get.await_args.kwargs["user_id"], 7)

    async def test_admin_preview_allows_other_users_files_for_both_services(self):
        from router.admin import func_api_admin_blob_preview_urls
        pool, conn = database()
        conn.fetch.return_value = [{"role": 1}]
        client = SimpleNamespace(generate_presigned_url=AsyncMock(return_value="signed-s3"))
        state = SimpleNamespace(client_postgres=pool, func_middleware_check_role=func_middleware_check_role,
            func_request_param_read=AsyncMock(), func_blob_preview_urls_get=func_blob_preview_urls_get,
            client_s3=client, client_azure_blob=MagicMock(), config_blob_services=["s3", "azure"],
            config_azure_account_name="account", config_azure_account_key="dummy", config_blob_expire_sec_preview=60)
        request = SimpleNamespace(app=SimpleNamespace(state=state), state=SimpleNamespace(user={"id": 1, "role": 1}))
        for service, url, expected in [
            ("s3", "https://bucket.s3.ap-south-1.amazonaws.com/user_8/file", "signed-s3"),
            ("azure", "https://account.blob.core.windows.net/container/user_8/file",
             "https://account.blob.core.windows.net/container/user_8/file?signature"),
        ]:
            with self.subTest(service=service), patch("azure.storage.blob.generate_blob_sas", return_value="signature"):
                state.func_request_param_read.return_value = {"service": service, "urls": [url, url]}
                result = await func_api_admin_blob_preview_urls(request=request)
                self.assertEqual(result, {"status": 1, "message": [expected, expected]})
        self.assertEqual(conn.fetch.await_args.args[1:], (1,))

    async def test_admin_preview_rejects_nonadmin_stale_and_missing_users(self):
        from router.admin import func_api_admin_blob_preview_urls
        pool, conn = database()
        state = SimpleNamespace(client_postgres=pool, func_middleware_check_role=func_middleware_check_role,
                                func_blob_preview_urls_get=AsyncMock(), func_request_param_read=AsyncMock())
        for user, rows in [({"id": 7, "role": 5}, [{"role": 5}]),
                           ({"id": 7, "role": 1}, [{"role": 5}]),
                           ({"id": 7, "role": 1}, []), ({}, [])]:
            conn.fetch.return_value = rows
            request = SimpleNamespace(app=SimpleNamespace(state=state), state=SimpleNamespace(user=user))
            with self.subTest(user=user, rows=rows), self.assertRaises(Exception):
                await func_api_admin_blob_preview_urls(request=request)
        state.func_blob_preview_urls_get.assert_not_awaited()
        state.func_request_param_read.assert_not_awaited()

    def test_preview_route_is_registered_only_in_my_router(self):
        from router.my import router as my_router
        from router.private import router as private_router
        routes = [route for route in my_router.routes if route.path == "/my/blob-preview-urls"]
        self.assertEqual(len(routes), 1)
        self.assertIn("POST", routes[0].methods)
        self.assertFalse(any("blob-preview-urls" in route.path for route in private_router.routes))

    async def test_s3_upload_signing_is_awaited_and_size_bounded(self):
        state = self.storage_state()
        state.client_s3.generate_presigned_post = AsyncMock(return_value={"url": "upload", "fields": {"key": "file"}})
        state.config_blob_expire_sec_upload = 60
        state.config_aws_s3_region_name = "test-region"
        result = await func_blob_upload_url(app_state=state, service="s3", container="bucket", count=1, user_id=7)
        self.assertEqual(result[0]["upload_url"], "upload")
        self.assertIn(["content-length-range", 1, 1024], state.client_s3.generate_presigned_post.await_args.kwargs["Conditions"])

    async def test_presigned_upload_count_must_be_positive(self):
        state = self.storage_state()
        for count in (0, -1, True):
            with self.subTest(count=count), self.assertRaisesRegex(Exception, "positive integer"):
                await func_blob_upload_url(app_state=state, service="s3", container="bucket", count=count, user_id=7)
        state.func_postgres_create.assert_not_awaited()

    def test_query_log_redacts_repeated_and_encoded_sensitive_keys(self):
        params = QueryParams("table=product&limit=10&otp=123456&OTP=999999&access_token=private&password=secret&api%5Fkey=hidden&dsn=credentials&filter=private")
        output = QueryParams(func_middleware_log_query_params(query_params=params))
        self.assertEqual(output["table"], "product")
        self.assertEqual(output["limit"], "10")
        for key in ("otp", "OTP", "access_token", "password", "api_key", "dsn", "filter"):
            self.assertEqual(output[key], "[REDACTED]")

    async def test_error_responses_and_console_do_not_echo_database_or_url_secrets(self):
        for error in (asyncpg.PostgresError("query detail password=secret-value"),
                      httpx.ConnectError("https://service.test/?token=secret-value"),
                      Exception("connection postgres://user:secret-value@host/db failed password=secret-value")):
            with self.subTest(error_type=type(error).__name__), redirect_stderr(io.StringIO()) as stderr:
                message, response = await func_middleware_api_response_error(exception=error, is_traceback=True, sentry_dsn=None)
                self.assertNotIn("secret-value", message)
                self.assertNotIn(b"secret-value", response.body)
                self.assertNotIn("secret-value", stderr.getvalue())
