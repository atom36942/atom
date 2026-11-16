"""The monitor names the master database as host / database for Admin's sidebar, never with the user or password."""
import unittest

from function.monitor import func_monitor_database_name


class MonitorDatabaseTests(unittest.TestCase):
    def test_host_and_database_only(self):
        self.assertEqual(func_monitor_database_name(url="postgresql://user:secret@localhost:5432/postgres"), "localhost / postgres")
        self.assertEqual(func_monitor_database_name(url="postgresql://user:secret@db.example.com:6432/app?sslmode=require"), "db.example.com:6432 / app")
        self.assertNotIn("secret", func_monitor_database_name(url="postgresql://user:secret@h/app"))

    def test_unset_or_unreadable_is_empty(self):
        for url in (None, "", "not a url"):
            with self.subTest(url=url): self.assertEqual(func_monitor_database_name(url=url), "")


if __name__ == "__main__":
    unittest.main()
