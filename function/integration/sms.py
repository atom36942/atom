def func_fast2sms_send_otp_mobile(*, config_fast2sms_url: str, config_fast2sms_key: str, mobile: str, otp_code: str) -> dict:
    """Send an OTP via Fast2SMS API."""
    import requests
    response = requests.get(config_fast2sms_url, params={"authorization": config_fast2sms_key, "numbers": mobile, "variables_values": otp_code, "route": "otp"}).json()
    if not response.get("return"):
        raise Exception(response.get("message"))
    return response
