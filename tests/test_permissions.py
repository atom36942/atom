"""Permission policy tests independent of external services."""
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock

from function import (
    func_check_table_permission, func_check_user_update_permission,
    func_check_user_delete_permission, func_validate_restricted_columns,
    func_check_batch_limit, func_attach_user_audit_fields,
    func_middleware_check_role, func_middleware_check_user_deactivated,
    func_middleware_check_user_deleted,
)


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

    async def test_user_cannot_update_another_account_or_mix_password_fields(self):
        for objects, message in [([{"id": 8, "name": "other"}], "ownership"),
                                 ([{"id": 7, "password": "new", "email": "a@example.test"}], "exactly two fields"),
                                 ([{"id": 7, "name": "me"}, {"id": 8, "name": "other"}], "multi-object")]:
            with self.subTest(objects=objects), self.assertRaisesRegex(Exception, message):
                await func_check_user_update_permission(app_state=SimpleNamespace(), table="users",
                                                        obj_list=objects, scope="my", user_id=7)

    async def test_email_change_requires_otp_and_propagates_failure(self):
        state = SimpleNamespace(func_otp_verify=AsyncMock(), client_postgres=object(),
                                config_otp_expiry_sec=300, config_otp_static=None)
        args = dict(app_state=state, table="users", obj_list=[{"id": 7, "email": "new@example.test"}],
                    scope="my", user_id=7, otp=123456)
        await func_check_user_update_permission(**args)
        state.func_otp_verify.assert_awaited_once_with(client_postgres=state.client_postgres, otp=123456,
                                                     email="new@example.test", mobile=None,
                                                     config_otp_expiry_sec=300, config_otp_static=None)
        state.func_otp_verify.side_effect = ValueError("invalid otp")
        with self.assertRaisesRegex(ValueError, "invalid otp"):
            await func_check_user_update_permission(**args)

    def test_account_deletion_requires_enabled_policy_and_own_single_id(self):
        state = SimpleNamespace(config_is_user_delete=True)
        func_check_user_delete_permission(app_state=state, table="users", scope="my", ids=[7], user_id=7)
        for changes in ({"ids": [8]}, {"ids": [7, 8]}, {"scope": "public"}, {"user_id": None}):
            args = dict(app_state=state, table="users", scope="my", ids=[7], user_id=7) | changes
            with self.subTest(changes=changes), self.assertRaises(Exception):
                func_check_user_delete_permission(**args)
        state.config_is_user_delete = False
        with self.assertRaisesRegex(Exception, "disabled"):
            func_check_user_delete_permission(app_state=state, table="users", scope="admin", ids=[7])

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
                with self.subTest(field=field, user=user), self.assertRaises(Exception):
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
