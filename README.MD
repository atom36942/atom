# about
```
1. an open-source backend framework for faster development
2. entire codebase is in a single file, main.py
3. combines procedural and functional programming
4. procedures ensures better global/local state access
5. functions ensures deterministic behavior of the code
6. follows SOLID principles
7. supports high-performance application development
8. uses realtional dataabse at its core
9. Reduces repetitive work with reusable modules
10. Enables rapid iteration and faster go-to-market
11. Built with Python,FastAPI,PostgreSQL,Redis,Kafka,Rabbitmq,Mongodb
12. Uses raw SQL for optimized queries and better control
13. Supports high-throughput pipelines via RabbitMQ, LavinMQ, or Kafka
14. Provides object-level CRUD operations by directly interacting with database schema
15. Auto-generates entire business database schemas from a single JSON config
16. ex. build a linkedIn-like backend in 2-3 weeks
```

# modules
```
1. authentication module
2. endpoints for authenticated users
3. direct crud apis on database objects
4. role-based access control for admin operations
5. built-in apis for aws services like s3,ses,sns 
6. deploy instantly using render
7. privileged access for root users 
8. import large datasets via csv 
9. improve performance with redis caching
10. kafka, rabbitmq, lavinmq, redis pub-sub
11. prevent api abuse with request limiting 
12. auto-generate database schemas via api 
13. background task execution 
14. scale with read database replication  
15. use mongodb as a secondary database
16. soft/hard delete on object level
```

# curl testing
```
1. add .env key=baseurl,token_root,token_admin,file_create,file_update,file_delete,test_id
2. chmod +x curl.sh
3. ./curl.sh
```

# how to run
```
1. download atom repo
2. install requirements.txt
3. create .env file
4. run =  python main.py
5. run with reload =  uvicorn main:app --reload 
```

# how to run using docker
```
1. docker build -t atom .
2. docker run -p 8000:8000 atom
```

# misc
```
1. Have an idea! email @ atom36942@gmail.com
2. api docs = https://www.atom42.org/docs
```

# commands
```
#git
git init
git remote add origin https://github.com/atom36942123/atom.git
git branch -M main

#venv
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip freeze > requirements.txt
pip list --outdated | tail -n +3 | awk '{print $1}' | xargs -n1 pip install --upgrade

#redis
brew install redis
brew services start redis
redis-cli -u redis://localhost

#postgres install
brew install postgresql@17
brew services start postgresql@17
psql postgresql://atom:123@localhost/postgres

#postgres reset
drop schema if exists public cascade;
create schema if not exists public;

#postgres export
\copy post to 'path'  delimiter ',' csv header;
\copy (query) to '/Users/atom/Downloads/xxx.csv' delimiter ',' csv header;
pg_dump --format=c  -d url > /Users/atom/Downloads/atom.dump

#postgres import
\copy post(created_by_id,type,title,location) from '/Users/atom/Downloads/location.csv' delimiter ',' csv header;
pg_restore -d url  /Users/atom/Downloads/atom.dump

#misc
pid kill = lsof -ti :8000 | xargs kill -9
git commit delete = git reset --hard HEAD~3 / git push origin main --force
postgres table count = SELECT relname AS table_name,n_live_tup AS row_count FROM pg_stat_user_tables;
```
