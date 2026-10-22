"""Synchronous SDK calls (SES, SNS, S3 resource, Celery) must run in a thread so other requests keep being served meanwhile."""
import asyncio
import time
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock

from function.messaging import func_otp_send_email, func_otp_send_mobile
from function.queues import func_producer
from function.storage import func_blob_container_ops


def slow(result=None):
    """A blocking SDK method: sleeps like a network call, freezing the event loop if called on it."""
    def call(*args, **kwargs):
        time.sleep(0.2)
        return result
    return call


class BlockingCallTests(unittest.IsolatedAsyncioTestCase):
    async def timed(self, coroutine):
        """Start the SDK call, then time a 50 ms sleep running next to it."""
        task = asyncio.create_task(coroutine)
        started = time.perf_counter()
        await asyncio.sleep(0.05)
        elapsed = time.perf_counter() - started
        await task
        return elapsed

    async def test_ses_sns_s3_and_celery_do_not_block_the_event_loop(self):
        ses = SimpleNamespace(send_email=slow({"MessageId": "m1"}))
        sns = SimpleNamespace(publish=slow())
        state = SimpleNamespace(client_ses=ses, client_sns=sns)
        bucket = MagicMock()
        bucket.objects.all.return_value.delete = slow([])
        s3_resource = SimpleNamespace(Bucket=lambda name: bucket)
        celery = SimpleNamespace(send_task=slow(SimpleNamespace(id="t1")))
        calls = {
            "ses otp": func_otp_send_email(app_state=state, service="ses", sender="a@b.c", email="d@e.f", otp=123456),
            "sns otp": func_otp_send_mobile(app_state=state, service="sns", mobile="+911234567890", otp=123456),
            "s3 empty bucket": func_blob_container_ops(client_s3=None, client_s3_resource=s3_resource, client_azure_blob=None, config_aws_s3_region_name="ap-south-1", service="s3", container="c", mode="empty"),
            "celery enqueue": func_producer(queue="celery", client_celery_producer=celery, client_kafka_producer=None, client_rabbitmq_producer=None, client_redis_producer=None, channel="jobs", payload={}),
        }
        for name, coroutine in calls.items():
            with self.subTest(call=name):
                # a 50 ms timer finishes in about 50 ms only if the 200 ms call is not holding the event loop
                self.assertLess(await self.timed(coroutine), 0.15)


if __name__ == "__main__":
    unittest.main()
