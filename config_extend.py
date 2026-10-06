"""Personal MDM and WiseTech configuration, preserved by Atom sync."""

from config import config_api as base_config_api

config_api = {
    **base_config_api,
    # mdm
    "/mdm/read": {"id": 114, "is_token": True, "user_check_role": {"mode": "realtime", "roles": [10]}},
    "/mdm/review": {"id": 115, "is_token": True, "user_check_role": {"mode": "realtime", "roles": [10]}},
    "/mdm/export": {"id": 116, "is_token": True, "user_check_role": {"mode": "realtime", "roles": [10]}},
    # wisetech
    "/wisetech/countries": {"id": 117, "is_token": True, "user_check_role": {"mode": "realtime", "roles": [11]}},
    "/wisetech/reference": {"id": 118, "is_token": True, "user_check_role": {"mode": "realtime", "roles": [11]}},
    "/wisetech/search": {"id": 119, "is_token": True, "user_check_role": {"mode": "realtime", "roles": [11]}},
}
