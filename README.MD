### about atom
```
1. Open-source backend framework with reusable modules to reduce repetitive work.
2. Accelerates development for faster delivery and iteration.
3. Enables entrepreneurs to launch and scale ideas quickly with minimal backend work.
4. Flexible and suitable for diverse applications.
5. Built with Python, FastAPI, PostgreSQL, and Redis for scalability.
6. Uses raw SQL for optimized queries and better control.
7. Supports high-throughput pipelines with RabbitMQ, LavinMQ, or Kafka.
8. Offers object-level CRUD operations directly on the database schema.
9. Simplifies setup by generating business schemas from a single JSON config.
10. Example: Build a LinkedIn-like backend in 2-3 weeks.
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
### coding paradigm
```
1. The entire code is contained in a single file, named main.py
2. Atom combines procedural and functional programming
3. Follows SOLID principles for scalability and maintainability.
4. Procedures encapsulate local state and control global state access.
5. Procedures encapsulate local state and control global state access.
6. Emphasizes modularity and separation of concerns.
7. Promotes efficient memory usage and data encapsulation.
8. Ensures robustness and flexibility for large-scale applications.
9. Supports high-performance application development.
10. Enhances code reusability and maintainability.
```
### contact
```
Got a startup idea? Build your backend faster with Atom! Share your requirements at:
atom36942@gmail.com
```
### links
```
1. api docs = https://www.atom42.org/docs
2. localhost = http://localhost:8000/docs
```
### how to run
```
1. download atom repo
2. create .env file inside downloaded folder(check env file section)
3. create venv
4. install requirements.txt
5. run python main.py
--using docker
1. docker build -t atom .
2. docker run -p 8000:8000 atom
```
### env
```
postgres_database_url=null
redis_server_url=null
secret_key_jwt=null
secret_key_root=null
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
drop schema public cascade;---create schema public;

#postgres export
\copy post to 'path'  delimiter ',' csv header;
\copy (query) to '/Users/atom/Downloads/xxx.csv' delimiter ',' csv header;
pg_dump --format=c  -d url > /Users/atom/Downloads/atom.dump

#postgres import
\copy atom(title,description,link_url,tag) from '/Users/atom/Downloads/post.csv' delimiter ',' csv header;
pg_restore -d url  /Users/atom/Downloads/atom.dump
```


