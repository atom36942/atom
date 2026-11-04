"""Queue jobs are done at least once: a job counts as done only after its function returns, a failed job is retried up to retry_max times and then kept in <channel>_failed, and a consumer that is killed mid-job loses nothing. Real Redis (ATOM_TEST_REDIS_URL) and RabbitMQ (ATOM_TEST_RABBITMQ_URL), each consumer in its own process."""
import asyncio
import os
import secrets
import subprocess
import sys
import time
import unittest
from pathlib import Path

import orjson

from function.queues import func_queue_redis_job_finish
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
    if payload["job"] == "fail": raise ValueError("job failed on purpose")
    while payload["job"] == "slow" and not Path(os.environ["SLOW_GO"]).exists(): await asyncio.sleep(0.1)
    with open(done_file, "a") as file: file.write(payload["job"] + "\\n")
func_run_broker(queue=queue, channel=channel, broker_settings={url_key: url}, setup_callback=setup, execute_callback=execute, concurrency=2, retry_max=1)
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

    def done(self):
        return sorted(self.done_file.read_text().split()) if self.done_file.exists() else []

    def cleanup(self):
        if self.process and self.process.poll() is None: self.kill()
        for path in (self.done_file, self.slow_go): path.unlink(missing_ok=True)


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


if __name__ == "__main__":
    unittest.main()
