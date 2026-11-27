"""User create takes other users columns in one insert; every Atom users column is either allowed there or refused by a block list, so a new sign-up or login column can never be set at creation by accident."""
import re
import unittest
from pathlib import Path
import config

ROOT = Path(__file__).resolve().parents[1]
CONFIG = (ROOT / "config.py").read_text()
REFUSED_ALWAYS = {"id", "role", "username", "password", "deactivated_at"}    # role, username and password are the create params; the rest never at creation
ALLOWED = {"name", "country", "state", "city", "email_secondary", "mobile_secondary", "address", "job_title", "about", "gender", "date_of_birth", "dashboard"}


class UserCreateColumnsTests(unittest.TestCase):
    def test_every_users_column_is_allowed_or_blocked_on_create(self):
        block = CONFIG[CONFIG.index('"users":['):]; block = block[:block.index("\n],")]
        columns = set(re.findall(r'"name":\s*"([a-z_]+)"', block))
        blocked = REFUSED_ALWAYS | set(config.config_column_users_my_blocked) | set(config.config_column_single_update) | set(config.config_column_users_blocked)
        self.assertEqual(sorted(columns - blocked - ALLOWED), [], "a new users column: block it in config_column_users_my_blocked or config_column_users_blocked, or add it to ALLOWED here")
        self.assertEqual(sorted(ALLOWED & blocked), [])

    def test_sign_up_and_login_columns_are_blocked(self):
        blocked = set(config.config_column_users_my_blocked) | set(config.config_column_single_update) | set(config.config_column_users_blocked)
        for column in ("email", "mobile", "oidc_google", "id_ext", "source", "parent_id", "verified_at", "permissions", "created_at", "last_active_at", "is_protected"):
            with self.subTest(column=column): self.assertIn(column, blocked)

    def test_the_create_route_passes_the_block_lists(self):
        self.assertIn("columns_blocked=[*(app_state.config_column_users_my_blocked or []), *(app_state.config_column_single_update or []), *(app_state.config_column_users_blocked or [])]", (ROOT / "router/admin.py").read_text())


if __name__ == "__main__":
    unittest.main()
