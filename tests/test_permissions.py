"""Permission policy tests independent of external services."""
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock

from function import func_check_table_permission
from function import func_check_table_not_users
from function import func_user_update_check
from function import func_user_delete
from function import func_validate_restricted_columns
from function import func_check_batch_limit
from function import func_attach_user_audit_fields
from function import func_middleware_check_role
from function import func_middleware_check_user_deactivated
from function import func_middleware_check_user_deleted


class PermissionTests(unittest.IsolatedAsyncioTestCase):
    def test_table_and_relation_allowlists(self):
        state = SimpleNamespace(config_table_public_read_allowed=["product"])
        func_check_table_permission(app_state=state, table="product")
        for table, relation in [("users", None), ("product", ["user,users,id,created_by_id"])]:
            with self.subTest(table=table, relation=relation), self.assertRaisesRegex(Exception, "disabled"):
                func_check_table_permission(app_state=state, table=table, relation=relation)
        with self.assertRaisesRegex(Exception, "disabled"):
            func_check_table_permission(app_state=SimpleNamespace(), table="product")

    def test_blocklist_takes_precedence_over_wildcard_allowlist(self):
        state = SimpleNamespace(config_table_public_read_blocked=["users"], config_table_public_read_allowed=["*"])
        func_check_table_permission(app_state=state, table="product")
        with self.assertRaisesRegex(Exception, "disabled"):
            func_check_table_permission(app_state=state, table="users")
        with self.assertRaisesRegex(Exception, "relation read disabled"):
            func_check_table_permission(app_state=state, table="product", relation=["user,users,id,created_by_id"])
        state.config_table_public_read_blocked = ["*"]
        with self.assertRaisesRegex(Exception, "disabled"):
            func_check_table_permission(app_state=state, table="product")

    def test_restricted_fields_checked_across_entire_batch(self):
        with self.assertRaisesRegex(Exception, "restricted field: role"):
            func_validate_restricted_columns(app_state=SimpleNamespace(config_column_admin={"role"}),
                                             obj_list=[{"name": "ok"}, {"role": 1}])

    def test_generic_object_apis_refuse_the_users_table(self):
        func_check_table_not_users(table="orders", api="/my/user-update")
        with self.assertRaisesRegex(Exception, "users table: use /my/user-update"):
            func_check_table_not_users(table="users", api="/my/user-update")

    async def update_check(self, obj, **changes):
        args = dict(client_postgres=object(), obj=obj, is_admin=False, is_otp_required=True,
                    config_column_single_update=["username", "password", "email", "mobile"], config_column_users_admin_only=["role", "deactivated_at"],
                    config_otp_expiry_sec=300, config_otp_static=None, config_otp_max_attempt=5)
        return await func_user_update_check(**(args | changes))

    async def test_user_update_rules(self):
        self.assertEqual(await self.update_check({"name": "Ravi", "city": "Pune"}), {"name": "Ravi", "city": "Pune"})
        self.assertEqual(await self.update_check({"password": "new-secret"}), {"password": "new-secret"})
        for obj, message, changes in [({}, "update field required", {}),
                                      ({"otp": 1}, "update field required", {}),
                                      ({"created_by_id": 2}, "created_by_id cannot be updated", {}),
                                      ({"deleted_at": "2026-01-01"}, "deleted_at cannot be updated", {"is_admin": True}),
                                      ({"role": 1}, "role can be updated only by an admin", {}),
                                      ({"password": "x", "name": "y"}, "password must be updated alone", {}),
                                      ({"password": "x", "name": "y"}, "password must be updated alone", {"is_admin": True}),
                                      ({"email": "a@x.test"}, "email update needs otp", {}),
                                      ({"mobile": "+911"}, "mobile update needs otp", {}),
                                      ({"id": 1, "role": 2}, "root user role cannot be updated", {"is_admin": True})]:
            with self.subTest(obj=obj, changes=changes), self.assertRaisesRegex(Exception, message):
                await self.update_check(obj, **changes)
        # an admin may update admin-only columns, and email without otp when config_is_otp_require_users_update is off
        self.assertEqual(await self.update_check({"id": 7, "role": 3}, is_admin=True), {"role": 3})
        self.assertEqual(await self.update_check({"id": 7, "email": " Ravi@X.test "}, is_admin=True, is_otp_required=False), {"email": "ravi@x.test"})

    async def test_email_update_verifies_the_otp_sent_to_the_new_email(self):
        from unittest.mock import patch
        with patch("function.user.func_otp_verify", AsyncMock()) as verify:
            self.assertEqual(await self.update_check({"email": "New@X.test", "otp": 123456}), {"email": "new@x.test"})
            self.assertEqual((verify.await_args.kwargs["otp"], verify.await_args.kwargs["email"]), (123456, "new@x.test"))
            verify.side_effect = ValueError("invalid otp")
            with self.assertRaisesRegex(ValueError, "invalid otp"):
                await self.update_check({"email": "new@x.test", "otp": 1})

    async def test_user_delete_needs_the_setting_and_never_deletes_root(self):
        pool = SimpleNamespace(execute=AsyncMock(return_value="DELETE 1"))
        self.assertEqual(await func_user_delete(client_postgres=pool, user_id=7, config_is_user_delete=True), "user deleted")
        for user_id, enabled, message in [(7, False, "users hard delete disabled"), (1, True, "root user cannot be deleted")]:
            with self.subTest(user_id=user_id), self.assertRaisesRegex(Exception, message):
                await func_user_delete(client_postgres=pool, user_id=user_id, config_is_user_delete=enabled)
        pool.execute.return_value = "DELETE 0"
        with self.assertRaisesRegex(Exception, "user not found"):
            await func_user_delete(client_postgres=pool, user_id=8, config_is_user_delete=True)

    async def test_role_policy_allows_authorized_and_rejects_other_roles(self):
        args = dict(user_check_role={"mode": "token", "roles": [5]}, client_postgres=None,
                    client_redis=None, cache_users_role={}, config_redis_cache_ttl_sec=60)
        await func_middleware_check_role(user_dict={"id": 7, "role": 5}, **args)
        for user, message in [({}, "token missing"), ({"id": 7}, "role missing"), ({"id": 7, "role": 9}, "access denied")]:
            with self.subTest(user=user), self.assertRaisesRegex(Exception, message):
                await func_middleware_check_role(user_dict=user, **args)

    async def test_deactivated_and_deleted_users_are_rejected(self):
        for func, key, cache_key, field in [
            (func_middleware_check_user_deactivated, "user_check_deactivated", "cache_users_deactivated", "deactivated_at"),
            (func_middleware_check_user_deleted, "user_check_deleted", "cache_users_deleted", "deleted_at"),
        ]:
            args = {key: {"mode": "token"}, cache_key: {}, "client_postgres": None,
                    "client_redis": None, "config_redis_cache_ttl_sec": 60}
            await func(user_dict={"id": 7, field: None}, **args)
            for user in ({"id": 7, field: "2026-01-01"}, {"id": 7}):
                with self.subTest(field=field, user=user), self.assertRaisesRegex(Exception, "missing deactivated_at|missing deleted_at|user is deleted|user not active"):
                    await func(user_dict=user, **args)

    def test_audit_owner_cannot_be_spoofed_and_input_is_not_mutated(self):
        request = SimpleNamespace(state=SimpleNamespace(user={"id": 7}))
        objects = [{"name": "item", "created_by_id": 999}]
        result = func_attach_user_audit_fields(request=request, obj_list=objects)
        self.assertEqual(result[0]["created_by_id"], 7)
        self.assertEqual(objects[0]["created_by_id"], 999)

    def test_batch_limit_boundary(self):
        state = SimpleNamespace(config_batch_item_limit=2)
        func_check_batch_limit(app_state=state, items=[{}, {}])
        with self.assertRaisesRegex(Exception, "maximum 2"):
            func_check_batch_limit(app_state=state, items=[{}, {}, {}])
