### about atom
```
atom is an open-source backend framework that reduces repetitive work through reusable modules, enabling faster backend development and iteration. it is designed for entrepreneurs to build and scale their ideas quickly with minimal backend work.

built with python, fastapi, postgresql, and redis for scalability.
optimized queries using raw sql for better control.
supports high-throughput pipelines with rabbitmq, lavinmq, or kafka.
one-click deployment and database setup.
easy integration with s3, ses, sns, and more.

```

### coding paradigm
```
Atom entire codebase is in a single file, main.py.

1. Atom combines procedural and functional programming
2. Procedures ensures better global/local state access. 
3. Functions ensures deterministic behavior of the code.
4. Atom uses realtional dataabse at its core.
5. Follows SOLID principles for scalability and maintainability.
6. Emphasizes modularity and separation of concerns.
7. Promotes efficient memory usage and data encapsulation.
8. Ensures robustness and flexibility for large-scale applications.
9. Supports high-performance application development.
10. Enhances code reusability and maintainability.
```

### modules
```
1. auth
2. logged in user apis
3. object level crud
4. admin apis with rbac
5. s3/ses/sns/etc integaration
6. one click depolyment using render
7. root user apis
8. bulk csv uploader
9. api caching
10.large scale data ingestion using kafka/rabbitmq/lavinmq/redis pub-sub
11. rate limiter
12. one click database schema setup api
13. background jobs
14. read/write database replicas
15. mongodb integraton as secondary database
```

### contact
```
Have a startup idea! Build your backend faster with atom! 

Share your requirements at: atom36942@gmail.com
```

### api docs
```
https://www.atom42.org/docs
```

### how to run
```
1. download atom repo
2. install requirements.txt
3. create .env file
4. run python main.py
```

### how to run using docker
```
1. docker build -t atom .
2. docker run -p 8000:8000 atom
```

### helper commands
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
drop schema if exists public cascade;---create schema if not exists public;

#postgres export
\copy post to 'path'  delimiter ',' csv header;
\copy (query) to '/Users/atom/Downloads/xxx.csv' delimiter ',' csv header;
pg_dump --format=c  -d url > /Users/atom/Downloads/atom.dump

#postgres import
\copy users(username,password,city,location) from '/Users/atom/Downloads/location.csv' delimiter ',' csv header;
pg_restore -d url  /Users/atom/Downloads/atom.dump

#kill python pids
lsof -ti :8000 | xargs kill -9
```
