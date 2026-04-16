def func_client_read_posthog(*, config_posthog_project_host: str, config_posthog_project_key: str) -> any:
    """Initialize PostHog client for analytics tracking."""
    from posthog import Posthog
    return Posthog(config_posthog_project_key, host=config_posthog_project_host)

def func_client_read_gsheet(*, config_gsheet_service_account_json_path: str, config_gsheet_scope: list) -> any:
    """Initialize Google Sheets client using a service account credentials file and specific scopes."""
    import gspread
    from google.oauth2.service_account import Credentials
    creds = Credentials.from_service_account_file(config_gsheet_service_account_json_path, scopes=config_gsheet_scope)
    return gspread.authorize(creds)

async def func_client_read_sftp(*, config_sftp_host: str, config_sftp_port: int, config_sftp_username: str, config_sftp_password: str, config_sftp_key_path: str, config_sftp_auth_method: str) -> any:
    """Initialize SFTP connection using asyncssh."""
    import asyncssh
    if config_sftp_auth_method not in ("key", "password"):
        raise Exception(f"invalid sftp auth mode: {config_sftp_auth_method}, allowed: key, password")
    if config_sftp_auth_method == "key":
        if not config_sftp_key_path:
            raise Exception("ssh key path missing")
        return await asyncssh.connect(host=config_sftp_host, port=int(config_sftp_port), username=config_sftp_username, client_keys=[config_sftp_key_path], known_hosts=None)
    if config_sftp_auth_method == "password":
        if not config_sftp_password:
            raise Exception("password missing")
        return await asyncssh.connect(host=config_sftp_host, port=int(config_sftp_port), username=config_sftp_username, password=config_sftp_password, known_hosts=None)
