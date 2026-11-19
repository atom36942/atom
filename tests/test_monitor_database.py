"""The monitor names the master database as host / database for the page header, never with the user or password; its upgrade check turns the server's counters into a verdict and what to ask DevOps for."""
import unittest
from datetime import datetime

from function.monitor import func_monitor_database_name
from function.monitor import func_monitor_database_upgrade

INFO = {"name": "app", "host": "db.example.com", "connections": 10, "max_connections": 100, "size_bytes": 2 * 1024 ** 3}
STATS = {"blks_hit": 10 ** 7, "blks_read": 1000, "temp_bytes": 0, "deadlocks": 0, "stats_reset": datetime(2026, 11, 1), "stats_age_sec": 10 * 86400, "shared_buffers_bytes": 128 * 1024 ** 2, "work_mem_bytes": 4 * 1024 ** 2, "net_bytes": 0, "server_bytes": 2 * 1024 ** 3}
WAL = {"wal_bytes": 10 * 1024 ** 3, "age_sec": 10 * 86400, "max_wal_bytes": 1024 ** 3, "checkpoint_timeout_sec": 300}


class MonitorDatabaseTests(unittest.TestCase):
    def test_host_and_database_only(self):
        self.assertEqual(func_monitor_database_name(url="postgresql://user:secret@localhost:5432/postgres"), "localhost / postgres")
        self.assertEqual(func_monitor_database_name(url="postgresql://user:secret@db.example.com:6432/app?sslmode=require"), "db.example.com:6432 / app")
        self.assertNotIn("secret", func_monitor_database_name(url="postgresql://user:secret@h/app"))

    def test_unset_or_unreadable_is_empty(self):
        for url in (None, "", "not a url"):
            with self.subTest(url=url): self.assertEqual(func_monitor_database_name(url=url), "")



class MonitorDatabaseUpgradeTests(unittest.TestCase):
    def check(self, wal=WAL, **changes):
        return func_monitor_database_upgrade(info={**INFO, **{k: v for k, v in changes.items() if k in INFO}}, stats={**STATS, **{k: v for k, v in changes.items() if k in STATS}}, wal=wal)

    def status(self, result, name):
        return next(signal["status"] for signal in result["signals"] if signal["name"] == name)

    def test_healthy_server_needs_nothing(self):
        result = self.check()
        self.assertEqual(result["verdict"], "ok")
        self.assertEqual((result["actions"], result["request"]), ([], ""))

    def test_data_size_is_information_only(self):
        result = self.check(server_bytes=500 * 1024 ** 3, net_bytes=20 * 1024 ** 3)    # large and growing fast: still no disk verdict, the disk size is not visible
        self.assertEqual((self.status(result, "Data size"), result["verdict"], result["actions"]), ("unknown", "ok", []))
        self.assertEqual(result["signals"][0]["value"], "500 GB")

    def test_an_upgrade_names_the_server_in_the_request(self):
        result = self.check(connections=85)
        self.assertEqual(result["verdict"], "upgrade")
        self.assertIn("db.example.com", result["request"])

    def test_each_resource_has_its_own_threshold(self):
        self.assertEqual(self.status(self.check(connections=70), "Connections"), "watch")
        self.assertEqual(self.status(self.check(connections=85), "Connections"), "upgrade")
        self.assertEqual(self.status(self.check(blks_hit=900000, blks_read=100000), "Memory"), "upgrade")
        self.assertEqual(self.status(self.check(blks_hit=500, blks_read=500), "Memory"), "ok")    # too few reads to judge
        self.assertEqual(self.status(self.check(temp_bytes=60 * 1024 ** 3), "Work memory"), "upgrade")
        self.assertEqual(self.status(self.check(wal={**WAL, "wal_bytes": 300 * 1024 ** 4}), "Write load"), "upgrade")    # 30 TB a day: a 1 GB WAL fills within 5 minutes
        self.assertEqual(self.status(self.check(wal={}), "Write load"), "ok")    # before PostgreSQL 14: can't judge

    def test_deadlocks_are_watched_never_an_upgrade(self):
        result = self.check(deadlocks=5)
        self.assertEqual((result["verdict"], self.status(result, "Deadlocks"), result["actions"]), ("watch", "watch", []))

    def test_young_counters_say_so(self):
        self.assertIn("under a day", self.check(stats_age_sec=3600)["window"])


if __name__ == "__main__":
    unittest.main()
