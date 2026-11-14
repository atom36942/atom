"""Permission policy tests independent of external services."""
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock
from unittest.mock import patch

from function import func_check_table_permission
from function import func_check_table_not_users
from function import func_check_table_write_blocked
from function import func_middleware_api_user_check_fill
from function import func_user_update_check
from function import func_user_update
from function import func_user_delete
from function import func_validate_restricted_columns
from function import func_check_batch_limit
from function import func_attach_user_audit_fields
from function import func_middleware_check_role
from function import func_middleware_check_permission
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

    def test_tables_only_atom_writes_are_refused_with_403(self):
        state = SimpleNamespace(config_table_write_blocked=["log_api"])
        func_check_table_write_blocked(app_state=state, table="orders")
        with self.assertRaisesRegex(Exception, "write disabled for table: log_api") as caught:
            func_check_table_write_blocked(app_state=state, table="log_api")
        self.assertEqual(caught.exception.status_code, 403)
        func_check_table_write_blocked(app_state=SimpleNamespace(), table="log_api")    # a project without the setting: no block

    def test_every_generic_write_api_checks_the_write_blocked_tables(self):
        import inspect
        import router.admin
        import router.my
        import router.public
        writes = {"/admin/object-create", "/admin/object-update", "/admin/object-delete", "/admin/postgres-import", "/my/object-create", "/my/object-update", "/my/object-delete", "/my/object-delete-all", "/public/object-create"}
        found = {route.path: route.endpoint for module in (router.admin, router.my, router.public) for route in module.router.routes if route.path in writes}
        self.assertEqual(set(found), writes)
        for path, endpoint in found.items():
            self.assertIn("func_check_table_write_blocked", inspect.getsource(endpoint), path)

    def test_global_user_checks_fill_every_token_route_unless_it_sets_its_own(self):
        config_api = {"/public": {"id": 1, "is_token": False}, "/my/x": {"id": 2, "is_token": True}, "/admin/x": {"id": 3, "is_token": False, "user_check_role": {"mode": "token", "roles": [1]}},
                      "/my/own": {"id": 4, "is_token": True, "user_check_deleted": {"mode": "realtime"}}, "/my/off": {"id": 5, "is_token": True, "user_check_deactivated": None}}
        filled = func_middleware_api_user_check_fill(config_api=config_api, config_api_global_user_check_deleted="token", config_api_global_user_check_deactivated="token")
        self.assertEqual(filled["/public"], {"id": 1, "is_token": False})
        for path in ("/my/x", "/admin/x"):
            self.assertEqual((filled[path]["user_check_deleted"], filled[path]["user_check_deactivated"]), ({"mode": "token"}, {"mode": "token"}), path)
        self.assertEqual(filled["/my/own"]["user_check_deleted"], {"mode": "realtime"})
        self.assertIsNone(filled["/my/off"]["user_check_deactivated"])
        self.assertNotIn("user_check_deleted", config_api["/my/x"], "config_api itself is not changed")
        off = func_middleware_api_user_check_fill(config_api=config_api, config_api_global_user_check_deleted=None, config_api_global_user_check_deactivated=None)
        self.assertNotIn("user_check_deleted", off["/my/x"])

    def test_global_user_check_defaults_are_token(self):
        import config
        self.assertEqual((config.config_api_global_user_check_deleted, config.config_api_global_user_check_deactivated), ("token", "token"))
        self.assertTrue({"deleted_at", "deactivated_at"} <= set(config.config_column_token_encode))

    def test_atom_tables_nobody_edits_are_in_the_defaults(self):
        import config
        self.assertTrue({"log_api", "log_users_password", "log_users_delete", "script_run", "otp"} <= set(config.config_table_write_blocked))
        self.assertEqual(config.config_postgres["control"]["table_row_update_disable"], ["log_api", "log_users_password"])

    def test_generic_object_apis_refuse_the_users_table(self):
        func_check_table_not_users(table="orders", api="/my/user-update")
        with self.assertRaisesRegex(Exception, "users table: use /my/user-update"):
            func_check_table_not_users(table="users", api="/my/user-update")

    async def update_check(self, obj, **changes):
        args = dict(client_postgres=object(), obj=obj, is_admin=False, is_otp_required=True,
                    config_column_single_update=["username", "password", "email", "mobile"], config_column_users_blocked=["created_by_id", "deleted_at"], config_column_users_my_blocked=["role", "deactivated_at"],
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

    async def test_admin_grants_only_labelled_route_ids_and_root_may_hold_them(self):
        labels = {205: "Task delete", 206: "Task export"}
        self.assertEqual(await self.update_check({"id": 1, "permissions": [206, 205, 205]}, is_admin=True, config_permission_label=labels), {"permissions": [205, 206]})
        self.assertEqual(await self.update_check({"id": 7, "permissions": None}, is_admin=True, config_permission_label=labels), {"permissions": None})
        for value, message in [([207], "not labelled"), (["205"], "list of route ids"), ([True], "list of route ids"), ("205", "list of route ids")]:
            with self.subTest(value=value), self.assertRaisesRegex(Exception, message):
                await self.update_check({"id": 7, "permissions": value}, is_admin=True, config_permission_label=labels)
        with self.assertRaisesRegex(Exception, "permissions can be updated only by an admin"):
            await self.update_check({"permissions": [205]}, config_column_users_my_blocked=["permissions"], config_permission_label=labels)

    async def test_permission_check_needs_the_route_id_in_the_token_permissions(self):
        check = {"mode": "token"}
        await func_middleware_check_permission(user_dict={"id": 7, "role": 2, "permissions": [205]}, user_check_permission=check, api_id=205)
        await func_middleware_check_permission(user_dict={"id": 7}, user_check_permission=None, api_id=205)    # route without the key
        for user, status in [({"id": 1, "role": 1, "permissions": None}, 403),    # admins are not exempt
                             ({"id": 7, "role": 2, "permissions": [206]}, 403),
                             ({"id": 7, "role": 2, "permissions": []}, 403),
                             ({"id": 7, "role": 2}, 500),    # permissions not encoded in the token
                             ({}, 401)]:
            with self.subTest(user=user), self.assertRaises(Exception) as caught:
                await func_middleware_check_permission(user_dict=user, user_check_permission=check, api_id=205)
            self.assertEqual(caught.exception.status_code, status)

    def test_permission_route_counts_as_a_token_route(self):
        filled = func_middleware_api_user_check_fill(config_api={"/x": {"id": 205, "user_check_permission": {"mode": "token"}}}, config_api_global_user_check_deleted="token", config_api_global_user_check_deactivated="token")
        self.assertEqual(filled["/x"]["user_check_deleted"], {"mode": "token"})

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

    async def test_admin_user_update_batches_by_columns_in_one_transaction(self):
        class Context:
            def __init__(self, value=None): self.value = value
            async def __aenter__(self): return self.value
            async def __aexit__(self, *exc): return False
        connection = SimpleNamespace(transaction=lambda: Context())
        pool = SimpleNamespace(acquire=lambda: Context(connection))
        args = dict(client_postgres=pool, client_password_hasher=None, cache_postgres_schema={}, config_column_regex={}, updated_by_id=1, is_otp_required=False,
                    config_column_single_update=["password"], config_column_users_blocked=["created_by_id"], config_column_users_my_blocked=["role"], config_otp_expiry_sec=300)
        update = AsyncMock(side_effect=lambda **kwargs: [obj["id"] for obj in kwargs["obj_list"]])
        with patch("function.user.func_postgres_update", new=update):
            self.assertEqual(await func_user_update(obj_list=[{"id": 7, "name": "a"}, {"id": "8", "role": 3}, {"id": 9, "name": "c"}], **args), [7, 8, 9])
            self.assertEqual([[obj["id"] for obj in call.kwargs["obj_list"]] for call in update.await_args_list], [[7, 9], [8]])    # one UPDATE per set of columns
            self.assertTrue(all(call.kwargs["client_postgres_conn"] is connection and call.kwargs["obj_list"][0]["updated_by_id"] == 1 for call in update.await_args_list))
            update.reset_mock()
            for obj_list, message in [([], "object list required"), ([{"name": "a"}], "missing required field"), ([{"id": "x", "name": "a"}], "must be integers"),
                                      ([{"id": 7, "name": "a"}, {"id": 7, "city": "b"}], r"id repeated: \[7\]"), ([{"id": 7, "name": "a"}, {"id": 1, "role": 2}], "root user role cannot be updated")]:
                with self.subTest(obj_list=obj_list), self.assertRaisesRegex(Exception, message):
                    await func_user_update(obj_list=obj_list, **args)
            update.assert_not_awaited()    # rules are checked before anything is written
            update.side_effect = lambda **kwargs: [7]
            with self.assertRaisesRegex(Exception, r"user not found: \[9\]"):
                await func_user_update(obj_list=[{"id": 7, "name": "a"}, {"id": 9, "name": "c"}], **args)

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
                with self.subTest(field=field, user=user), self.assertRaisesRegex(Exception, "missing deactivated_at|missing deleted_at|account deleted|account deactivated"):
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
