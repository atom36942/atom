"""Atom's pages that log in (Admin, Monitor, API, Message) follow one page standard (docs/page.md, Page standard): each page carries the same four blocks,
copied unchanged (look CSS, account script, account header, dialogs), and only sets PAGE above the account script. A new page or project copies the blocks."""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAGES = {name: (ROOT / "static" / f"{name}.html").read_text() for name in ("admin", "monitor", "api", "message")}
BLOCKS = {
    "look": r"/\* ==== atom page: look ==== \*/.*?/\* ==== end atom page: look ==== \*/",
    "account": r"/\* ==== atom page: account ==== \*/.*?/\* ==== end atom page: account ==== \*/",
    "account header": r"<!-- ==== atom page: account header ==== -->.*?<!-- ==== end atom page: account header ==== -->",
    "dialogs": r"<!-- ==== atom page: dialogs ==== -->.*?<!-- ==== end atom page: dialogs ==== -->",
}
# what each page sets in PAGE: key (its localStorage key and IndexedDB database), role (null: any role), whether it needs a login, whether it keeps IndexedDB data
SETTINGS = {
    "admin": 'key: "admin", title: "Admin", role: 1, loginRequired: true, idb: true',
    "monitor": 'key: "monitor", title: "Monitor", role: 1, loginRequired: true, idb: false',
    "api": 'key: "api", title: "API", role: null, loginRequired: false, idb: true',
    "message": 'key: "message", title: "Message", role: null, loginRequired: true, idb: false',
}


def block(page, name):
    found = re.findall(BLOCKS[name], PAGES[page], re.S)
    return [re.sub(r"\n[ \t]+", "\n", text) for text in found]    # the indentation where a page places the block does not count


ACCOUNT = block("admin", "account")[0]
LOOK = block("admin", "look")[0]


class PageStandardTests(unittest.TestCase):
    def test_every_page_carries_each_block_once_and_unchanged(self):
        for name in BLOCKS:
            copies = {page: block(page, name) for page in PAGES}
            for page, found in copies.items():
                with self.subTest(block=name, page=page): self.assertEqual(len(found), 1)
            with self.subTest(block=name): self.assertEqual(len({found[0] for found in copies.values()}), 1, f"the {name} block differs between pages: copy it again")

    def test_each_page_sets_page_above_the_account_block(self):
        for page, settings in SETTINGS.items():
            with self.subTest(page=page):
                text = PAGES[page]
                self.assertIn(f"const PAGE = {{ {settings}", text)
                self.assertLess(text.index("const PAGE = {"), text.index("/* ==== atom page: account ==== */"))
                self.assertIn("Page.start();", text)
                outside = re.sub(BLOCKS["account"], "", text, flags=re.S)
                self.assertNotIn("localStorage.", outside)    # only the block touches the browser's storage
                self.assertNotIn("indexedDB.", outside)

    def test_pages_do_not_keep_their_own_login_code(self):
        # the login, the token, the user check and the account dialogs live only in the blocks
        for page, text in PAGES.items():
            outside = text
            for pattern in BLOCKS.values(): outside = re.sub(pattern, "", outside, flags=re.S)
            for name in ("const loginValid", "const tokenRefresh", "const userBlock", "/auth/login-username-password\"", "fetch(\"/my/token-refresh\"", "accountDialog", "id=\"loginForm\"", "id=\"accountBtn\""):
                with self.subTest(page=page, name=name): self.assertNotIn(name, outside)

    def test_logged_in_means_a_valid_token_object(self):
        check = re.search(r"const loginValid = token => (.*?);\n", ACCOUNT).group(1)
        for part in ("token.access_token", "token.refresh_token", "Number.isFinite(token.access_token_expires_at)", "Number.isFinite(token.refresh_token_expires_at)", "token.refresh_token_expires_at > nowSec()"):
            with self.subTest(part=part): self.assertIn(part, check)
        self.assertIn("if (!loginValid(body.message)) return false", ACCOUNT)    # a refresh stores only a valid token
        self.assertIn("if (!loginValid(token)) throw", ACCOUNT)    # so does a login

    def test_expiry_comes_from_the_token_object(self):
        self.assertIn("token.access_token_expires_at - nowSec() <= 300", ACCOUNT)
        self.assertNotIn("payload.exp", ACCOUNT)

    def test_the_user_check(self):
        check = re.search(r"const userBlock = user => (.*?);\n", ACCOUNT).group(1)
        for part in ("user.deactivated_at", "user.deleted_at", "PAGE.role"):
            with self.subTest(part=part): self.assertIn(part, check)

    def test_logout_clears_the_key_and_the_cache_in_every_tab(self):
        self.assertIn("localStorage.removeItem(STORAGE_KEY)", ACCOUNT)
        self.assertIn("indexedDB.deleteDatabase(STORAGE_KEY)", ACCOUNT)
        self.assertIn('window.addEventListener("storage"', ACCOUNT)
        self.assertIn('"You logged out in another tab."', ACCOUNT)

    def test_storage_layout(self):
        self.assertIn('const STORAGE_KEY = PAGE.key, STORAGE_VERSION = 1, IDB_STORE = "cache"', ACCOUNT)
        self.assertIn('createObjectStore(IDB_STORE, { keyPath: "name" })', ACCOUNT)
        self.assertIn("put({ name, user_id:", ACCOUNT)
        self.assertIn("SYNC_EVERY_MS = 3 * 3600 * 1000", ACCOUNT)

    def test_the_account_words(self):
        for words in ('title: "My profile"', 'title: "Login details"', 'title: "Update password"', "6–120 characters, no spaces.</p>", '"Use 6–120 characters, no spaces"', '"Passwords don\'t match"',
                      'toast("Password updated")', 'title: "Logout?"', "Are you sure you want to logout?", 'title: "Sync", sub: "Auto sync every 3 hr"', '"Everything is up to date."',
                      '"Sync failed. Please try again."', '"Renewing login…"', '"Loading your profile…"', '"Downloading data…"', '"/my/user-update"', "const initials = name =>"):
            with self.subTest(words=words): self.assertIn(words, ACCOUNT)
        self.assertNotIn("Logged out", ACCOUNT)    # logout shows no message
        header = block("admin", "account header")[0]
        for label in (">My profile</button>", ">Login details</button>", ">Logout</button>", ">Sync</button>", ">Log in</button>"):
            with self.subTest(label=label): self.assertIn(label, header)


class PageThemeTests(unittest.TestCase):
    def test_one_dark_theme_without_toggles(self):
        self.assertIn("--bg:#0b0d10", (ROOT / "static" / "home.html").read_text())
        for token in ("--bg:#0b0d10", "--danger:#f87171", "--font:", "--fs:13px", "--fs-title:15px"):
            with self.subTest(token=token): self.assertIn(token, LOOK)
        pgweb = (ROOT / "static" / "pgweb.html").read_text()
        self.assertIn('<html lang="en" data-theme="dark">', pgweb)
        self.assertIn("--bg:#0b0d10", pgweb)
        for name in ("home", "pgweb"):
            with self.subTest(page=name): self.assertNotIn('id="theme"', (ROOT / "static" / f"{name}.html").read_text())

    def test_dialog_header_and_actions_stand_apart_from_the_body(self):
        self.assertRegex(LOOK, r"\.dlg-head\{[^}]*background:var\(--panel\)")
        self.assertRegex(LOOK, r"\.dlg-body\{padding:18px")
        self.assertRegex(LOOK, r"\.dlg-actions\{[^}]*background:var\(--panel\)")


if __name__ == "__main__":
    unittest.main()
