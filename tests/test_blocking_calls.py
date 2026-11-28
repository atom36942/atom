"""Service calls never hold the event loop: SES, SNS, S3, Azure email and SMS are awaited on async clients (no thread); Celery, which has no async client, runs in a thread."""
import asyncio
import time
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock
from unittest.mock import patch

from function import messaging
from function.messaging import func_email_send
from function.messaging import func_otp_send_email
from function.messaging import func_otp_send_mobile
from function.queues import func_producer
from function.storage import func_blob_container_ops


def slow(result=None):
    """A blocking SDK method: sleeps like a network call, freezing the event loop if called on it."""
    def call(*args, **kwargs):
        time.sleep(0.2)
        return result
    return call


def slow_async(result=None):
    """An async SDK method: waits like a network call without holding the event loop."""
    async def call(*args, **kwargs):
        await asyncio.sleep(0.2)
        return result
    return AsyncMock(side_effect=call)


class Pages:
    """An aiobotocore paginator: async iteration over list_objects_v2 pages."""
    def __init__(self, pages): self.pages = pages
    def paginate(self, **kwargs): return self
    def __aiter__(self): return self._iter()
    async def _iter(self):
        for page in self.pages:
            await asyncio.sleep(0)
            yield page


class BlockingCallTests(unittest.IsolatedAsyncioTestCase):
    async def timed(self, coroutine):
        """Start the SDK call, then time a 50 ms sleep running next to it."""
        task = asyncio.create_task(coroutine)
        started = time.perf_counter()
        await asyncio.sleep(0.05)
        elapsed = time.perf_counter() - started
        await task
        return elapsed

    async def test_service_calls_do_not_block_the_event_loop(self):
        ses = SimpleNamespace(send_email=slow_async({"MessageId": "m1"}))
        sns = SimpleNamespace(publish=slow_async())
        poller = SimpleNamespace(result=slow_async({"id": "e1", "status": "Succeeded"}))
        azure_email = SimpleNamespace(begin_send=AsyncMock(return_value=poller))
        azure_sms = SimpleNamespace(send=slow_async())
        state = SimpleNamespace(client_ses=ses, client_sns=sns, client_azure_email=azure_email, client_azure_sms=azure_sms, client_http=None, config_azure_sms_from_number="+100")
        s3 = SimpleNamespace(get_paginator=lambda name: Pages([{"Contents": [{"Key": "a"}, {"Key": "b"}]}, {}]), delete_objects=slow_async({}))
        celery = SimpleNamespace(send_task=slow(SimpleNamespace(id="t1")))
        calls = {
            "ses otp": func_otp_send_email(app_state=state, service="ses", sender="a@b.c", email="d@e.f", otp=123456),
            "sns otp": func_otp_send_mobile(app_state=state, service="sns", mobile="+911234567890", otp=123456),
            "azure email otp": func_otp_send_email(app_state=state, service="azure", sender="a@b.c", email="d@e.f", otp=123456),
            "azure sms otp": func_otp_send_mobile(app_state=state, service="azure", mobile="+911234567890", otp=123456),
            "ses email": func_email_send(app_state=state, service="ses", sender="a@b.c", to=["d@e.f"], subject="s", text="t"),
            "azure email": func_email_send(app_state=state, service="azure", sender="a@b.c", to=["d@e.f"], subject="s", text="t"),
            "s3 empty bucket": func_blob_container_ops(client_s3=s3, client_azure_blob=None, config_aws_s3_region_name="ap-south-1", service="s3", container="c", mode="empty"),
            "celery enqueue": func_producer(queue="celery", client_celery_producer=celery, client_kafka_producer=None, client_rabbitmq_producer=None, client_redis_producer=None, channel="jobs", payload={}),
        }
        for name, coroutine in calls.items():
            with self.subTest(call=name):
                # a 50 ms timer finishes in about 50 ms only if the 200 ms call is not holding the event loop
                self.assertLess(await self.timed(coroutine), 0.15)

    async def test_messaging_uses_no_thread(self):
        state = SimpleNamespace(client_ses=SimpleNamespace(send_email=AsyncMock(return_value={"MessageId": "m1"})), client_sns=SimpleNamespace(publish=AsyncMock()))
        with patch.object(messaging.asyncio, "to_thread", side_effect=AssertionError("thread used")):
            await func_otp_send_email(app_state=state, service="ses", sender="a@b.c", email="d@e.f", otp=1)
            await func_otp_send_mobile(app_state=state, service="sns", mobile="+911234567890", otp=1)

    async def test_s3_empty_deletes_every_page(self):
        delete = AsyncMock(return_value={})
        s3 = SimpleNamespace(get_paginator=lambda name: Pages([{"Contents": [{"Key": "a"}]}, {"Contents": [{"Key": "b"}, {"Key": "c"}]}, {}]), delete_objects=delete)
        res = await func_blob_container_ops(client_s3=s3, client_azure_blob=None, config_aws_s3_region_name="x", service="s3", container="c", mode="empty")
        self.assertEqual(res["deleted_count"], 3)
        self.assertEqual(delete.await_count, 2)
        delete.return_value = {"Errors": [{"Key": "a"}]}
        with self.assertRaisesRegex(Exception, "S3 delete failed"):
            await func_blob_container_ops(client_s3=SimpleNamespace(get_paginator=lambda name: Pages([{"Contents": [{"Key": "a"}]}]), delete_objects=delete), client_azure_blob=None, config_aws_s3_region_name="x", service="s3", container="c", mode="empty")


if __name__ == "__main__":
    unittest.main()
