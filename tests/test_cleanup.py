"""Periodic tasks start and stop, and retention settings are checked, without database access."""
import asyncio
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock

from function.background import func_app_tasks_start
from function.background import func_app_tasks_stop
from function.background import func_async_tasks_cancel
from function.checks import func_check_runtime_config


class CleanupTests(unittest.IsolatedAsyncioTestCase):
    async def test_shutdown_includes_the_schedule_task(self):
        state = SimpleNamespace(runtime_task_schedule=object(), func_async_tasks_cancel=AsyncMock())
        await func_app_tasks_stop(app_state=state)
        self.assertIn(state.runtime_task_schedule, state.func_async_tasks_cancel.call_args.kwargs['task_list'])


    async def test_tasks_start_respects_read_only_and_stop_cancels_them(self):
        async def forever(**kwargs): await asyncio.Event().wait()
        names = ("runtime_task_postgres_buffer_flush", "runtime_task_schedule", "runtime_task_webhook", "runtime_task_memory_history", "runtime_task_inmemory_cache_cleanup")
        for is_read_only, expected in ((False, names), (True, ("runtime_task_memory_history", "runtime_task_inmemory_cache_cleanup"))):
            with self.subTest(is_read_only=is_read_only):
                state = SimpleNamespace(config_is_read_only=is_read_only, client_postgres_dict={"master": object()}, client_postgres_log_api=object(), runtime_error_count={},
                    buffer_postgres_create={}, buffer_postgres_log_api={}, cache_api_response={}, cache_api_response_bytes={"total": 0}, cache_ratelimiter={}, cache_token={},
                    config_postgres_buffer_flush_auto_sec=1, config_schedule_timezone="UTC",
                    client_http=object(), config_webhook_is_active=True, func_webhook_deliver_periodic_task=forever,
                    func_postgres_buffer_flush_periodic_task=forever, func_schedule_periodic_task=forever, func_inmemory_cache_cleanup_periodic_task=forever, func_memory_history_periodic_task=forever,
                    func_schedule_read=lambda **kwargs: {"postgres_cleanup": {}}, func_schedule_timezone=lambda **kwargs: None, func_async_tasks_cancel=func_async_tasks_cancel)
                func_app_tasks_start(app_state=state)
                self.assertEqual(tuple(name for name in names if hasattr(state, name)), expected)
                tasks = [getattr(state, name) for name in expected]
                await func_app_tasks_stop(app_state=state)
                self.assertTrue(all(task.cancelled() for task in tasks))

class RetentionConfigTests(unittest.TestCase):
    def state(self, retention):
        return SimpleNamespace(config_query_runner_read_limit=10, config_export_limit=10,
            config_sql_read_limit_default=10, config_sql_read_limit_max=10, config_sql_read_relation_fetch_limit_max=10,
            config_postgres_buffer_flush_auto_sec=60, config_uvicorn_workers=1, config_request_body_max_kb=10240, config_request_form_max_kb=102400, config_api_cache_inmemory_max_kb=102400,
            config_retention_day_table_otp=retention, config_retention_day_table_log_api=retention, config_retention_day_user_soft_deleted=retention, config_retention_day_table_script_run=retention, config_otp_expiry_sec=600,
            config_column_users_private_read=["id", "username"], config_postgres_schema_master={"table": {"users": [{"name": "id"}, {"name": "username"}, {"name": "password"}]}})

    def test_retention_validation(self):
        for value in (None, 1, 30):
            func_check_runtime_config(app_state=self.state(value))
        for value in (0, -1, True, 1.5, '1', 36501):
            with self.subTest(value=value), self.assertRaises(ValueError):
                func_check_runtime_config(app_state=self.state(value))
        state = self.state(1)
        state.config_otp_expiry_sec = 86400
        with self.assertRaises(ValueError):
            func_check_runtime_config(app_state=state)

    def test_users_private_read_columns_are_checked(self):
        for value, message in (([], "non-empty list"), ("id", "non-empty list"), (["id", "password"], "never readable"), (["id", "mobile"], "no users column 'mobile'")):
            state = self.state(1)
            state.config_column_users_private_read = value
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, message):
                func_check_runtime_config(app_state=state)

    def test_removed_config_sql_stops_startup_and_cache_limits_are_checked(self):
        state = self.state(1)
        state.config_sql = {}
        with self.assertRaisesRegex(ValueError, "config_sql was removed in Atom 9.0.0"):
            func_check_runtime_config(app_state=state)
        for value in (-1, True, 1.5, "10"):
            state = self.state(1)
            state.config_cache_row_limit_users_role = value
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, "config_cache_row_limit_users_role must be an integer"):
                func_check_runtime_config(app_state=state)
        state = self.state(1)
        state.config_cache_row_limit_users_role = 0
        func_check_runtime_config(app_state=state)

    def test_old_retention_names_stop_startup(self):
        state = self.state(1)
        state.config_otp_retention_day = 1
        with self.assertRaisesRegex(ValueError, "config_otp_retention_day was renamed to config_retention_day_table_otp"):
            func_check_runtime_config(app_state=state)
        for old_key, new_key in (("config_retention_day_otp", "config_retention_day_table_otp"), ("config_retention_day_users_delete", "config_retention_day_user_soft_deleted")):
            state = self.state(1)
            setattr(state, old_key, 1)
            with self.assertRaisesRegex(ValueError, f"{old_key} was renamed to {new_key}"):
                func_check_runtime_config(app_state=state)

