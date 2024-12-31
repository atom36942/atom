### about atom
1. atom is an open-source backend that has pre-built modules which are most commonly used
2. atom can reduce develoment time to a large extent
3. primary vision is to help entreprenurs to laucnh their ideas faster
4. atom is non-opionanted and can be used to build backend for most of the ideas
5. core tech stack=python,fastapi,postgres,redis
6. atom doesn't rely on any orm and uses raw sql entirely
7. atom supports large scale data ingestion using rabbitmq/lavinmq/kafka
8. atom has object-level crud by directly interacting with databaese schema for serialization
9. atom can generate entire business schema with a single json

### coding paradigm
Atom follows procedural+functional programming paradigm with focus on solid principles.  
Procedural programming is a programming paradigm built around the idea that programs are sequences of instructions to be executed.
They focus heavily on splitting up programs into named sets of instructions called procedures, analogous to functions.
A procedure can store local data that is not accessible from outside the procedure's scope and can also access and modify global data variables.

### contact
If you have an idea and want to use atom to build tech super-fast,email your requirement @:-
atom36942@gmail.com

### api docs
1. live = https://www.atom42.org/docs
2. localhost = http://localhost:8000/docs
3. localhost =  http://127.0.0.1:8000/redoc

### how to run
1. download atom repo
2. create .env file inside downloaded folder(check env file section)
3. create venv
4. install requirements.txt
5. run python main.py

### how to run using docker
1. docker build -t atom .
2. docker run -p 8000:8000 atom

### env
```
postgres_database_url=null
redis_server_url=null
secret_key_jwt=null
secret_key_root=null
```

### helpers
```
#git init
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

#postgres
brew install postgresql@17
brew services start postgresql@17
psql postgresql://atom:123@localhost/postgres
drop schema public cascade;---create schema public;

#postgres export
\copy post to 'path'  delimiter ',' csv header;
\copy (query) to '/Users/atom/Downloads/xxx.csv' delimiter ',' csv header;
pg_dump --format=c  -d url > /Users/atom/Downloads/atom.dump

#postgres import
\copy atom(title,description,link_url,tag) from '/Users/atom/Downloads/post.csv' delimiter ',' csv header;
pg_restore -d url  /Users/atom/Downloads/atom.dump
```


