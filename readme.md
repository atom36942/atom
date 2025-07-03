# features
- functional+procedural programming style
- pure functions to reduce side effects
- primary database as postgres
- multiple async drivers for postgres
- one click database setup
- sql query runner
- database read/write replica
- one click deployment using render
- object level programming
- inbuilt api logs
- auth module with n number of login types
- login methods - username,email,mobile,oauth
- logged in user apis
- message module
- public apis to read objects
- admin apis with rbac
- object soft/hard delete
- background apis
- redis integration
- redis bulk uploader
- s3 integation
- sns integration
- ses integration
- sentry integration
- kafka integration
- rabbitmq integration
- lavinmq integration
- mongodb integration
- ratelimiter
- api caching
- middleware functions
- curl testing using tets.sh
- prometheus integration
- render html files
- google sheet integration
- openai integration
- fast2ms integration
- resend integration
- inmemory caching
- celery integration
- tesseract ocr
- postgres csv export
- postgres csv import
- posthog integration

# notes
1. main.py run = python main.py
2. main.py run with reload =  uvicorn main:app --reload
3. main.py run with docker =  docker build -t atom . --- docker run -p 8000:8000 atom
4. api testing = ./test.sh
5. celery run = celery -A consumerc.client_celery_consumer worker --loglevel=info