# 🏭 Production Configuration

## 1. Required production `.env`

```dotenv
config_root_user_password=<strong-root-password>
config_login_password=<strong-login-password>
config_token_secret_key=<long-random-token-secret>
config_root_html_path=static/api.html
config_is_enable_user_delete=0
```

## 2. Recommended production `.env`

```dotenv
config_is_debug=0
config_is_enable_signup=0
config_cors_allow_origins=["https://app.example.com"]
config_access_token_expires_sec=900
config_refresh_token_expires_sec=2592000
config_table_public_create_enable=[]
config_table_public_read_enable=[]
config_table_my_delete_all_enable=[]
config_table_my_delete_all_received_enable=[]
config_table_my_create_disable=["users","log_api","log_users_password","otp","spatial_ref_sys"]
```

---

📚 [Back to README](../readme.md)
