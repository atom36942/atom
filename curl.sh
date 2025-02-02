curl -X GET "http://127.0.0.1:8000"

curl -X POST "http://127.0.0.1:8000/root/schema-init-default" -H "Authorization: Bearer token_root"
curl -X POST "http://127.0.0.1:8000/root/schema-init-custom" -H "Authorization: Bearer token_root" -H "Content-Type: application/json" -d '{"table":{"atom":["title-text-0-btree"],"users":["username-text-1-btree","password-text-1-btree"]},"query":{}}'

curl -X GET "http://127.0.0.1:8000/root/info" -H "Authorization: Bearer token_root"
curl -X PUT "http://127.0.0.1:8000/root/reset-global" -H "Authorization: Bearer token_root"
curl -X PUT "http://127.0.0.1:8000/root/reset-redis" -H "Authorization: Bearer token_root"
curl -X DELETE "http://127.0.0.1:8000/root/db-clean" -H "Authorization: Bearer token_root"
curl -X PUT "http://127.0.0.1:8000/root/db-checklist" -H "Authorization: Bearer token_root"

curl -X POST "http://127.0.0.1:8000/root/query-runner" -H "Authorization: Bearer token_root" -H "Content-Type: application/json" -d '{"query":"insert into otp (otp,email,mobile) values (123,'\''abc'\'',null)---insert into otp (otp,email,mobile) values (123,null,'\''abc'\'')"}'

curl -X POST "http://127.0.0.1:8000/root/csv-uploader" -H "Authorization: Bearer token_root" -F "file=@\"/Users/atom/Downloads/create.csv\"" -F "mode=create" -F "table=post"
curl -X POST "http://127.0.0.1:8000/root/csv-uploader" -H "Authorization: Bearer token_root" -F "file=@\"/Users/atom/Downloads/update.csv\"" -F "mode=update" -F "table=post"
curl -X POST "http://127.0.0.1:8000/root/csv-uploader" -H "Authorization: Bearer token_root" -F "file=@\"/Users/atom/Downloads/delete.csv\"" -F "mode=delete" -F "table=post"

curl -X GET "http://127.0.0.1:8000/root/s3-bucket-list" -H "Authorization: Bearer token_root"
curl -X POST "http://127.0.0.1:8000/root/s3-bucket-create" -H "Authorization: Bearer token_root" -H "Content-Type: application/json" -d '{"bucket":"master"}'
curl -X PUT "http://127.0.0.1:8000/root/s3-bucket-public" -H "Authorization: Bearer token_root" -H "Content-Type: application/json" -d '{"bucket":"master"}'
curl -X DELETE "http://127.0.0.1:8000/root/s3-bucket-empty" -H "Authorization: Bearer token_root" -H "Content-Type: application/json" -d '{"bucket":"master"}'
curl -X DELETE "http://127.0.0.1:8000/root/s3-bucket-delete" -H "Authorization: Bearer token_root" -H "Content-Type: application/json" -d '{"bucket":"master"}'
curl -X DELETE "http://127.0.0.1:8000/root/s3-url-delete" -H "Authorization: Bearer token_root" -H "Content-Type: application/json" -d '{"url":"www.abc.com"}'

curl -X POST "http://127.0.0.1:8000/root/redis-set-object" -H "Authorization: Bearer token_root" -H "Content-Type: application/json" -d '{"key":"post_1","expiry":3600,"object":{"name":"atom"}}'
curl -X POST "http://127.0.0.1:8000/root/redis-set-csv" -H "Authorization: Bearer token_root" -F "file=@\"/Users/atom/Downloads/update.csv\"" -F "table=post" -F "expiry=3600"

curl -X POST "http://127.0.0.1:8000/auth/signup" -H "Content-Type: application/json" -d '{"username":"atom","password":"123"}'
curl -X POST "http://127.0.0.1:8000/auth/login" -H "Content-Type: application/json" -d '{"username":"atom","password":"123"}'
curl -X POST "http://127.0.0.1:8000/auth/login-google" -H "Content-Type: application/json" -d '{"google_id":"atom"}'
curl -X POST "http://127.0.0.1:8000/auth/login-otp-email" -H "Content-Type: application/json" -d '{"email":"abc","otp":123}'
curl -X POST "http://127.0.0.1:8000/auth/login-otp-mobile" -H "Content-Type: application/json" -d '{"mobile":"abc","otp":123}'
curl -X POST "http://127.0.0.1:8000/auth/login-password-email" -H "Content-Type: application/json" -d '{"email":"atom","password":"123"}'
curl -X POST "http://127.0.0.1:8000/auth/login-password-mobile" -H "Content-Type: application/json" -d '{"mobile":"atom","password":"123"}'

curl -X GET "http://127.0.0.1:8000/my/profile" -H "Authorization: Bearer token"
curl -X GET "http://127.0.0.1:8000/my/token-refresh" -H "Authorization: Bearer token"

curl -X GET "http://127.0.0.1:8000/my/message-inbox" -H "Authorization: Bearer token"
curl -X GET "http://127.0.0.1:8000/my/message-inbox?mode=unread" -H "Authorization: Bearer token"
curl -X GET "http://127.0.0.1:8000/my/message-received" -H "Authorization: Bearer token"
curl -X GET "http://127.0.0.1:8000/my/message-received?mode=unread" -H "Authorization: Bearer token"
curl -X GET "http://127.0.0.1:8000/my/message-thread?user_id=2" -H "Authorization: Bearer token"

curl -X GET "http://127.0.0.1:8000/my/parent-read?table=action_comment&parent_table=post" -H "Authorization: Bearer token"
curl -X GET "http://127.0.0.1:8000/my/parent-check?table=action_comment&parent_table=post&parent_ids=1,2,11" -H "Authorization: Bearer token"
curl -X DELETE "http://127.0.0.1:8000/my/parent-delete?table=action_comment&parent_table=post&parent_id=11" -H "Authorization: Bearer token"
curl -X GET "http://127.0.0.1:8000/my/action-on-me-creator-read?table=action_rating" -H "Authorization: Bearer token"
curl -X GET "http://127.0.0.1:8000/my/action-on-me-creator-read-mutual?table=action_rating" -H "Authorization: Bearer token"

