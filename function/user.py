# import
import asyncio
import asyncpg
from argon2 import PasswordHasher
from .auth import func_otp_verify
from .middleware import func_api_error
from .validation import func_regex_check

# function
async def func_user_create(*, client_postgres: asyncpg.Pool | None, client_password_hasher: PasswordHasher | None, config_column_regex: dict, role: int, username: str, password: str, created_by_id: int = None) -> int:
    """Create a username + password user (admin); returns its id. A taken username in that role fails as "username, role already exists"."""
    if not client_postgres: raise func_api_error(message="postgres client not initialized", status_code=500)
    if not client_password_hasher: raise func_api_error(message="password hasher not initialized", status_code=500)
    username = username.strip()
    await func_regex_check(config_column_regex=config_column_regex, obj_list=[{"username": username, "password": password}])
    hashed_password = await asyncio.to_thread(client_password_hasher.hash, str(password))
    return await client_postgres.fetchval("INSERT INTO users (role, username, password, created_by_id) VALUES ($1, $2, $3, $4) RETURNING id;", role, username, hashed_password, created_by_id)

async def func_user_update_check(*, client_postgres: asyncpg.Pool | None, obj: dict, is_admin: bool, is_otp_required: bool, config_column_single_update: list, config_column_users_blocked: list, config_column_users_my_blocked: list, config_otp_expiry_sec: int, config_otp_static: int = None, config_otp_max_attempt: int = 5) -> dict:
    """The columns of one user update after its rules: config_column_users_blocked refused for everyone (deletion has its own API), config_column_users_my_blocked refused for the user's own update,
    a single-update column (password, email, ...) sent alone, email or mobile verified with the otp sent to the new value when is_otp_required, email lowercased."""
    obj = dict(obj)
    otp, user_id = obj.pop("otp", None), obj.pop("id", None)
    if not obj: raise Exception("update field required")
    if column := next((c for c in obj if c in (config_column_users_blocked or [])), None): raise Exception(f"{column} cannot be updated")
    if not is_admin and (column := next((c for c in obj if c in (config_column_users_my_blocked or [])), None)): raise Exception(f"{column} can be updated only by an admin")
    if (column := next((c for c in obj if c in (config_column_single_update or [])), None)) and len(obj) > 1: raise Exception(f"{column} must be updated alone")
    if user_id == 1 and (column := next((c for c in obj if c in ("role", "permissions", "deactivated_at")), None)): raise Exception(f"root user {column} cannot be updated")
    if isinstance(obj.get("email"), str): obj["email"] = obj["email"].strip().lower()
    if is_otp_required and ("email" in obj or "mobile" in obj):
        if otp is None: raise Exception(f"{'email' if 'email' in obj else 'mobile'} update needs otp")
        await func_otp_verify(client_postgres=client_postgres, otp=otp, email=obj.get("email"), mobile=obj.get("mobile"), config_otp_expiry_sec=config_otp_expiry_sec, config_otp_static=config_otp_static, config_otp_max_attempt=config_otp_max_attempt)
    return obj

async def func_user_delete(*, client_postgres: asyncpg.Pool | None, user_id: int, config_is_user_delete: bool) -> str:
    """Hard-delete one user, when config_is_user_delete allows it; never the root user."""
    if not client_postgres: raise func_api_error(message="postgres client not initialized", status_code=500)
    if not config_is_user_delete: raise func_api_error(message="users hard delete disabled", status_code=403)
    if int(user_id) == 1: raise func_api_error(message="root user cannot be deleted", status_code=403)
    try: result = await client_postgres.execute("DELETE FROM users WHERE id=$1;", user_id)
    except asyncpg.exceptions.RaiseError as error:
        # the database's own guard: config_postgres control table_row_delete_disable lists users
        if "not allowed on users" in str(error): raise func_api_error(message="users delete blocked in the database: remove users from config_postgres control table_row_delete_disable", status_code=403) from None
        raise
    if result == "DELETE 0": raise func_api_error(message="user not found", status_code=404)
    return "user deleted"
