"""Queue jobs are done at least once on every broker: a job counts as done only after its function returns, a failed job is retried up to retry_max times and then kept in <channel>_failed, and a consumer that is killed mid-job loses nothing. Real Redis (ATOM_TEST_REDIS_URL) and RabbitMQ (ATOM_TEST_RABBITMQ_URL), each consumer in its own process; Kafka and Celery with fakes."""
import asyncio
import os
import secrets
import signal
import subprocess
import sys
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock
from unittest.mock import MagicMock
from unittest.mock import patch

import orjson

from function.queues import func_queue_celery_job_finish
from function.queues import func_queue_kafka_job_finish
from function.queues import func_queue_redis_job_finish
from function.queues import func_queue_redis_lock_keep
from function.queues import func_queue_redis_lock_release
from function.queues import func_queue_retry_wait_sec
from function.queues import func_run_broker
from function.queues import func_queue_redis_recover
from tests.support import service_setting

ROOT = Path(__file__).resolve().parents[1]
REDIS_URL = service_setting("ATOM_TEST_REDIS_URL")
RABBITMQ_URL = service_setting("ATOM_TEST_RABBITMQ_URL")
WAIT_SEC = 20
# a consumer process: job "fail" always raises, job "slow" waits until the file SLOW_GO exists (so the test can kill it mid-job)
CONSUMER = """
import asyncio, os, sys
from pathlib import Path
from function.queues import func_run_broker
queue, channel, url_key, url, done_file = sys.argv[1:6]
async def setup(): return (None,)
async def execute(payload, client):
    with open(done_file + ".started", "a") as file: file.write(payload["job"] + "\\n")
    if payload["job"] == "fail": raise ValueError("job failed on purpose")
    while payload["job"] == "slow" and not Path(os.environ["SLOW_GO"]).exists(): await asyncio.sleep(0.1)
    with open(done_file, "a") as file: file.write(payload["job"] + "\\n")
func_run_broker(queue=queue, channel=channel, broker_settings={url_key: url}, setup_callback=setup, execute_callback=execute, concurrency=2, retry_max=1, retry_wait_sec=0.1)
"""


def wait_until(check, message):
    deadline = time.monotonic() + WAIT_SEC
    while time.monotonic() < deadline:
        if check(): return
        time.sleep(0.2)
    raise AssertionError(f"waited {WAIT_SEC} s: {message}")


class ConsumerProcess:
    """Starts and kills a consumer for one test; done jobs are written one per line to a file under tmp/."""
    def __init__(self, test, *, queue, channel, url_key, url):
        folder = ROOT / "tmp" / "test_queue_delivery"
        folder.mkdir(parents=True, exist_ok=True)
        self.done_file, self.slow_go = folder / f"{channel}.done", folder / f"{channel}.go"
        self.args = [sys.executable, "-c", CONSUMER, queue, channel, url_key, url, str(self.done_file)]
        self.process = None
        test.addCleanup(self.cleanup)

    def start(self):
        self.process = subprocess.Popen(self.args, cwd=ROOT, env={**os.environ, "SLOW_GO": str(self.slow_go)}, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)    # noqa: S603 - fixed command

    def kill(self):
        self.process.kill()
        self.process.wait()

    def stop(self):
        """SIGTERM, as a deploy or scale-down sends it."""
        self.process.send_signal(signal.SIGTERM)

    def started(self):
        path = Path(f"{self.done_file}.started")
        return path.read_text().split() if path.exists() else []

    def done(self):
        return sorted(self.done_file.read_text().split()) if self.done_file.exists() else []

    def cleanup(self):
        if self.process and self.process.poll() is None: self.kill()
        for path in (self.done_file, self.slow_go, Path(f"{self.done_file}.started")): path.unlink(missing_ok=True)


@unittest.skipUnless(REDIS_URL, "set ATOM_TEST_REDIS_URL (environment or .env) to run Redis tests")
class RedisDeliveryTests(unittest.TestCase):
    def setUp(self):
        import redis
        self.redis = redis.Redis.from_url(REDIS_URL)
        self.channel = f"atom_test_{secrets.token_hex(4)}"
        self.addCleanup(self.redis.close)
        self.addCleanup(lambda: self.redis.delete(*[f"{self.channel}{suffix}" for suffix in ("", "_processing", "_failed", "_consumer")]))

    def push(self, *jobs):
        for job in jobs: self.redis.lpush(self.channel, orjson.dumps({"payload": {"job": job}, "attempt": 0}))

    def failed(self):
        return [orjson.loads(item) for item in self.redis.lrange(f"{self.channel}_failed", 0, -1)]

    def test_retry_then_failed_queue_and_a_killed_consumer_loses_nothing(self):
        consumer = ConsumerProcess(self, queue="redis", channel=self.channel, url_key="config_redis_url_queue", url=REDIS_URL)
        self.push("ok", "fail", "slow")
        consumer.start()
        wait_until(lambda: consumer.done() == ["ok"] and len(self.failed()) == 1 and self.redis.llen(f"{self.channel}_processing") == 1, "ok done, fail in _failed, slow running")
        failed = self.failed()[0]
        self.assertEqual((failed["payload"], failed["attempt"]), ({"job": "fail"}, 2), "run once, retried once (retry_max=1), then kept")
        self.assertIn("ValueError: job failed on purpose", failed["error"])
        consumer.kill()    # mid-job: "slow" is still running
        self.assertEqual(self.redis.llen(f"{self.channel}_processing"), 1, "the unfinished job is still in Redis")
        self.redis.delete(f"{self.channel}_consumer")    # a killed consumer's lock would otherwise hold its restart for up to 60 s
        consumer.slow_go.touch()
        consumer.start()
        wait_until(lambda: consumer.done() == ["ok", "slow"], "the restarted consumer finishes the job the killed one left")
        self.assertEqual((self.redis.llen(self.channel), self.redis.llen(f"{self.channel}_processing")), (0, 0))

    def test_sigterm_finishes_the_running_job_then_exits_and_frees_the_channel(self):
        consumer = ConsumerProcess(self, queue="redis", channel=self.channel, url_key="config_redis_url_queue", url=REDIS_URL)
        consumer.start()
        self.push("slow")
        wait_until(lambda: consumer.started() == ["slow"], "the slow job is running")
        consumer.stop()
        time.sleep(1.5)
        self.assertIsNone(consumer.process.poll(), "it waits for the running job")
        self.push("ok")
        consumer.slow_go.touch()
        self.assertEqual(consumer.process.wait(timeout=WAIT_SEC), 0)
        self.assertEqual(consumer.done(), ["slow"], "the running job finished; the new one was not taken")
        self.assertEqual((self.redis.llen(self.channel), self.redis.llen(f"{self.channel}_processing"), self.redis.exists(f"{self.channel}_consumer")), (1, 0, 0), "the new job waits in Redis and the channel is free for a restart")

    def test_a_second_consumer_waits_while_one_runs(self):
        first = ConsumerProcess(self, queue="redis", channel=self.channel, url_key="config_redis_url_queue", url=REDIS_URL)
        second = ConsumerProcess(self, queue="redis", channel=self.channel, url_key="config_redis_url_queue", url=REDIS_URL)
        first.start()
        wait_until(lambda: self.redis.exists(f"{self.channel}_consumer"), "the first consumer holds the channel")
        second.start()
        time.sleep(1)
        self.assertIsNone(second.process.poll(), "the second one keeps running, as a standby")
        self.push("ok")
        wait_until(lambda: first.done() == ["ok"], "the job runs once, in the first consumer")

    def test_finish_and_recover(self):
        import redis.asyncio as redis_async
        async def run():
            client = redis_async.Redis.from_url(REDIS_URL)
            try:
                processing = f"{self.channel}_processing"
                for job in (b'{"payload":{"job":1},"attempt":0}', b'{"payload":{"job":2},"attempt":0}', b"not json"): await client.lpush(processing, job)
                outcomes = [await func_queue_redis_job_finish(client=client, channel=self.channel, raw=b'{"payload":{"job":1},"attempt":0}', error=None, retry_max=3),
                            await func_queue_redis_job_finish(client=client, channel=self.channel, raw=b"not json", error=ValueError("bad"), retry_max=3)]
                recovered = await func_queue_redis_recover(client=client, channel=self.channel)
                return outcomes, recovered, await client.lrange(self.channel, 0, -1), await client.llen(f"{self.channel}_failed")
            finally: await client.aclose()
        outcomes, recovered, queued, failed = asyncio.run(run())
        self.assertEqual(outcomes, ["done", "failed"], "an unreadable job goes straight to _failed")
        self.assertEqual((recovered, queued, failed), (1, [b'{"payload":{"job":2},"attempt":0}'], 1))

    def test_the_lock_is_kept_and_released_only_by_its_owner(self):
        import redis.asyncio as redis_async
        key = f"{self.channel}_consumer"
        async def run():
            client = redis_async.Redis.from_url(REDIS_URL)
            try:
                await client.set(key, "mine", ex=60)
                kept = await func_queue_redis_lock_keep(client=client, key=key, token="mine", ttl_sec=90)
                ttl = await client.ttl(key)
                await client.set(key, "standby", ex=60)    # this consumer stalled, the lock expired and a standby took it
                kept_after = await func_queue_redis_lock_keep(client=client, key=key, token="mine", ttl_sec=90)
                released = await func_queue_redis_lock_release(client=client, key=key, token="mine")
                return kept, ttl, kept_after, released, await client.get(key), await client.ttl(key)
            finally: await client.aclose()
        kept, ttl, kept_after, released, owner, owner_ttl = asyncio.run(run())
        self.assertEqual((kept, ttl > 60), (True, True), "the owner extends it")
        self.assertEqual((kept_after, released), (False, False), "the old owner can neither extend nor delete the new owner's lock")
        self.assertEqual((owner, owner_ttl <= 60), (b"standby", True))

    def test_a_retry_waits_before_the_job_goes_back(self):
        import redis.asyncio as redis_async
        raw = b'{"payload":{"job":1},"attempt":1}'
        async def run():
            client = redis_async.Redis.from_url(REDIS_URL)
            try:
                await client.lpush(f"{self.channel}_processing", raw)
                with patch("function.queues.asyncio.sleep", new=AsyncMock()) as sleep:
                    outcome = await func_queue_redis_job_finish(client=client, channel=self.channel, raw=raw, error=ValueError("db down"), retry_max=3, retry_wait_sec=2)
                return outcome, sleep.await_args.args[0], await client.lrange(self.channel, 0, -1)
            finally: await client.aclose()
        outcome, waited, queued = asyncio.run(run())
        self.assertEqual((outcome, waited), ("retry", 4), "second retry waits 4 s")
        self.assertEqual(queued, [b'{"payload":{"job":1},"attempt":2}'])


@unittest.skipUnless(RABBITMQ_URL, "set ATOM_TEST_RABBITMQ_URL (environment or .env) to run RabbitMQ tests")
class RabbitmqDeliveryTests(unittest.TestCase):
    def setUp(self):
        self.channel = f"atom_test_{secrets.token_hex(4)}"
        self.addCleanup(lambda: self.rabbitmq(self.queues_delete))

    def rabbitmq(self, action, *args):
        async def run():
            import aio_pika
            connection = await aio_pika.connect(RABBITMQ_URL)
            try: return await action(await connection.channel(), *args)
            finally: await connection.close()
        return asyncio.run(run())

    async def publish(self, channel, *jobs):
        import aio_pika
        await channel.declare_queue(self.channel, durable=True)
        for job in jobs: await channel.default_exchange.publish(aio_pika.Message(body=orjson.dumps({"job": job}), delivery_mode=aio_pika.DeliveryMode.PERSISTENT), routing_key=self.channel)

    async def failed(self, channel):
        queue = await channel.declare_queue(f"{self.channel}_failed", durable=True)
        message = await queue.get(fail=False)
        if message: await message.ack()
        return message and (orjson.loads(message.body), message.headers)

    async def counts(self, channel):
        return [(await channel.declare_queue(name, durable=True)).declaration_result.message_count for name in (self.channel, f"{self.channel}_failed")]

    async def queues_delete(self, channel):
        for name in (self.channel, f"{self.channel}_failed"): await channel.queue_delete(name)

    def test_retry_then_failed_queue_and_a_killed_consumer_loses_nothing(self):
        consumer = ConsumerProcess(self, queue="rabbitmq", channel=self.channel, url_key="config_rabbitmq_url", url=RABBITMQ_URL)
        self.rabbitmq(self.publish, "ok", "fail", "slow")
        consumer.start()
        wait_until(lambda: consumer.done() == ["ok"] and self.rabbitmq(self.counts)[1] == 1, "ok done, fail in _failed")
        body, headers = self.rabbitmq(self.failed)
        self.assertEqual((body, headers["x-attempt"]), ({"job": "fail"}, 2), "run once, retried once (retry_max=1), then kept")
        self.assertIn("ValueError: job failed on purpose", headers["x-error"])
        consumer.kill()    # mid-job: "slow" was taken but never acknowledged
        consumer.slow_go.touch()
        consumer.start()
        wait_until(lambda: consumer.done() == ["ok", "slow"], "RabbitMQ gives the unacknowledged job to the restarted consumer")
        self.assertEqual(self.rabbitmq(self.counts), [0, 0])

    def test_sigterm_finishes_the_running_job_then_exits(self):
        consumer = ConsumerProcess(self, queue="rabbitmq", channel=self.channel, url_key="config_rabbitmq_url", url=RABBITMQ_URL)
        self.rabbitmq(self.publish, "slow")
        consumer.start()
        wait_until(lambda: consumer.started() == ["slow"], "the slow job is running")
        consumer.stop()
        time.sleep(1.5)
        self.assertIsNone(consumer.process.poll(), "it waits for the running job")
        consumer.slow_go.touch()
        self.assertEqual(consumer.process.wait(timeout=WAIT_SEC), 0)
        self.assertEqual(consumer.done(), ["slow"])
        self.assertEqual(self.rabbitmq(self.counts), [0, 0], "acknowledged before it exited: nothing runs twice")




@unittest.skipUnless(REDIS_URL, "set ATOM_TEST_REDIS_URL (environment or .env) to run Redis tests")
class CeleryWorkerTests(unittest.TestCase):
    """A real Celery worker, with Redis as its broker: it runs jobs at all (the prefork pool failed every task on Python 3.14), retries a failed one after 1 s and then keeps it."""
    def test_retry_then_failed_queue(self):
        import redis
        from celery import Celery
        client = redis.Redis.from_url(REDIS_URL)
        channel = f"atom_test_{secrets.token_hex(4)}"
        self.addCleanup(client.close)
        self.addCleanup(lambda: [client.delete(key) for key in client.scan_iter(f"*{channel}*")])
        consumer = ConsumerProcess(self, queue="celery", channel=channel, url_key="config_celery_url", url=REDIS_URL)
        consumer.start()
        app = Celery("atom", broker=REDIS_URL)
        for job in ("ok", "fail"): app.send_task(channel, kwargs={"job": job}, queue=channel)
        wait_until(lambda: consumer.done() == ["ok"] and client.llen(f"{channel}_failed") == 1, "ok done, fail kept after its retry")
        headers = orjson.loads(client.lindex(f"{channel}_failed", 0))["headers"]
        self.assertEqual(headers["x-attempt"], 2)
        self.assertEqual(headers["x-error"], "ValueError: job failed on purpose")

class KafkaDeliveryTests(unittest.TestCase):
    """No Kafka server here: aiokafka is replaced by fakes that record what the consumer does, in order."""
    def test_a_batch_is_committed_only_after_every_job_is_finished(self):
        events = []
        def message(job, attempt=None): return SimpleNamespace(value=orjson.dumps({"job": job}), headers=((("x-attempt", attempt),) if attempt else ()))
        batch = {"partition-0": [message("ok"), message("fail"), message("fail", b"1")]}
        consumer = MagicMock(start=AsyncMock(), stop=AsyncMock(), commit=AsyncMock(side_effect=lambda: events.append("commit")), getmany=AsyncMock(side_effect=[batch, RuntimeError("stop the test")]))
        producer = MagicMock(start=AsyncMock(), stop=AsyncMock(), send_and_wait=AsyncMock(side_effect=lambda topic, value, headers: events.append((topic, dict(headers)))))
        fake = SimpleNamespace(AIOKafkaConsumer=MagicMock(return_value=consumer), AIOKafkaProducer=MagicMock(return_value=producer))
        async def setup(): return (None,)
        async def execute(payload, client):
            events.append(payload["job"])
            if payload["job"] == "fail": raise ValueError("job failed on purpose")
        with patch.dict(sys.modules, {"aiokafka": fake}), self.assertRaises(SystemExit):
            func_run_broker(queue="kafka", channel="jobs", broker_settings={"config_kafka_url": "kafka:9092"}, setup_callback=setup, execute_callback=execute, retry_max=1, retry_wait_sec=0)
        self.assertEqual(fake.AIOKafkaConsumer.call_args.kwargs["enable_auto_commit"], False)
        self.assertEqual(events[-1], "commit", "committed last, once")
        self.assertEqual(events.count("commit"), 1)
        sent = [event for event in events if isinstance(event, tuple)]
        self.assertEqual(sorted(topic for topic, _ in sent), ["jobs", "jobs_failed"], "first failure retried, second failure kept")
        self.assertEqual(dict(sent)["jobs_failed"]["x-attempt"], b"2")
        self.assertIn(b"ValueError: job failed on purpose", dict(sent)["jobs_failed"]["x-error"])

    def test_finish_done_sends_nothing(self):
        producer = MagicMock(send_and_wait=AsyncMock())
        outcome = asyncio.run(func_queue_kafka_job_finish(producer=producer, channel="jobs", message=SimpleNamespace(value=b"{}", headers=()), error=None, retry_max=3))
        self.assertEqual(outcome, "done")
        producer.send_and_wait.assert_not_awaited()


class CeleryDeliveryTests(unittest.TestCase):
    def task(self, retries):
        class Retry(Exception): pass
        return SimpleNamespace(request=SimpleNamespace(retries=retries), retry=MagicMock(return_value=Retry())), Retry

    def test_a_failed_job_is_retried_with_backoff(self):
        app = MagicMock()
        task, retry = self.task(retries=1)
        with self.assertRaises(retry): func_queue_celery_job_finish(app=app, task=task, channel="jobs", payload={"job": 1}, error=ValueError("x"), retry_max=3)
        self.assertEqual(task.retry.call_args.kwargs["countdown"], 4, "second retry: 2 s, then doubled")
        app.send_task.assert_not_called()

    def test_after_the_last_retry_it_goes_to_the_failed_queue(self):
        app = MagicMock()
        task, _ = self.task(retries=3)
        self.assertEqual(func_queue_celery_job_finish(app=app, task=task, channel="jobs", payload={"job": 1}, error=ValueError("x"), retry_max=3), "failed")
        self.assertEqual(app.send_task.call_args.kwargs["queue"], "jobs_failed")
        self.assertEqual(app.send_task.call_args.kwargs["kwargs"], {"job": 1})
        self.assertEqual(app.send_task.call_args.kwargs["headers"], {"x-attempt": 4, "x-error": "ValueError: x"})

class RetryWaitTests(unittest.TestCase):
    def test_the_wait_doubles_each_retry(self):
        self.assertEqual([func_queue_retry_wait_sec(attempt=attempt, retry_wait_sec=2) for attempt in (1, 2, 3)], [2, 4, 8])
        self.assertEqual(func_queue_retry_wait_sec(attempt=3, retry_wait_sec=0), 0)


if __name__ == "__main__":
    unittest.main()
