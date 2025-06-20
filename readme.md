# features
- functional+procedural programming style
- pure functions to reduce side effects
- primary database as postgres
- multiple drivers for postgres
- one click database setup
- bulk database uploader
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
- soft/hard delete
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
- rate limiter
- api caching
- middleware functions
- curl testing using tets.sh
- prometheus integration
- render html files
- google sheet integration
- openai integration
- fast2ms integration
- resend integration

# notes
1. run = python main.py
2. run with reload =  uvicorn main:app --reload
3. run with docker =  docker build -t atom . --- docker run -p 8000:8000 atom
4. api testing = ./curl.sh