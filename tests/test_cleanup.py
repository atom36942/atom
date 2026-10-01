"""Cleanup orchestration tests without database access."""
import asyncio
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from function.background import func_cleanup_periodic_task, func_app_tasks_stop
from function.checks import func_check_runtime_config


class CleanupTests(unittest.IsolatedAsyncioTestCase):
    def setup_pool(self, locked=True):
        conn = SimpleNamespace(fetchval=AsyncMock(side_effect=[locked, 'cutoff']), execute=AsyncMock())
        pool = MagicMock()
        pool.acquire.return_value.__aenter__ = AsyncMock(return_value=conn)
        pool.acquire.return_value.__aexit__ = AsyncMock(return_value=False)
        return pool, conn

    async def test_disabled_never_acquires_or_sleeps(self):
        pool, _ = self.setup_pool()
        with patch('function.background.asyncio.sleep', new_callable=AsyncMock) as sleep:
            await func_cleanup_periodic_task(client_postgres=pool, retention_day=None, cleanup=AsyncMock(), lock_id=1)
        pool.acquire.assert_not_called()
        sleep.assert_not_called()

    async def test_other_worker_holds_lock(self):
        pool, conn = self.setup_pool(False)
        cleanup = AsyncMock()
        with patch('function.background.asyncio.sleep', AsyncMock(side_effect=[None, asyncio.CancelledError()])):
            await func_cleanup_periodic_task(client_postgres=pool, retention_day=1, cleanup=cleanup, lock_id=1)
        cleanup.assert_not_called()
        conn.execute.assert_not_called()

    async def test_batches_share_cutoff_and_release_lock(self):
        pool, conn = self.setup_pool()
        cleanup = AsyncMock(side_effect=[5000, 1])
        with patch('function.background.asyncio.sleep', AsyncMock(side_effect=[None, None, asyncio.CancelledError()])):
            await func_cleanup_periodic_task(client_postgres=pool, retention_day=1, cleanup=cleanup, lock_id=1)
        self.assertEqual(cleanup.await_count, 2)
        self.assertTrue(all(c.kwargs['cutoff'] == 'cutoff' for c in cleanup.await_args_list))
        conn.execute.assert_awaited_once_with('SELECT pg_advisory_unlock(1096044365, $1)', 1, timeout=5)

    async def test_error_and_cancellation_release_lock(self):
        for error in (RuntimeError('failed'), asyncio.CancelledError()):
            pool, conn = self.setup_pool()
            cleanup = AsyncMock(side_effect=error)
            with patch('function.background.asyncio.sleep', AsyncMock(side_effect=[None, asyncio.CancelledError()])), patch('builtins.print'):
                await func_cleanup_periodic_task(client_postgres=pool, retention_day=30, cleanup=cleanup, lock_id=2)
            conn.execute.assert_awaited_once()

    async def test_shutdown_includes_cleanup_tasks(self):
        state = SimpleNamespace(otp_cleanup_task=object(), log_api_cleanup_task=object(), func_async_tasks_cancel=AsyncMock())
        await func_app_tasks_stop(app_state=state)
        tasks = state.func_async_tasks_cancel.call_args.kwargs['task_list']
        self.assertIn(state.otp_cleanup_task, tasks)
        self.assertIn(state.log_api_cleanup_task, tasks)


class RetentionConfigTests(unittest.TestCase):
    def state(self, retention):
        return SimpleNamespace(config_query_runner_read_limit=10, config_query_runner_export_limit=10,
            config_sql_read_limit_default=10, config_sql_read_limit_max=10, config_sql_read_relation_fetch_limit_max=10,
            config_postgres_buffer_flush_auto_sec=60, config_inmemory_cache_cleanup_auto_sec=300,
            config_otp_retention_day=retention, config_log_api_retention_day=retention, config_otp_expiry_sec=600)

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
