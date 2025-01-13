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
### coding paradigm
```
1. Atom combines procedural and functional programming
2. Follows SOLID principles for scalability and maintainability.
3. Procedural code is structured into reusable procedures.
4. Procedures encapsulate local state and control global state access.
5. Emphasizes modularity and separation of concerns.
6. Promotes efficient memory usage and data encapsulation.
7. Ensures robustness and flexibility for large-scale applications.
8. Supports high-performance application development.
9. Enhances code reusability and maintainability.
10. The entire code is contained in a single file, named main.py
```

### contact
````
Have a startup idea? Build your backend faster with Atom! Share your requirements at:
atom36942@gmail.com
```

### links
```
1. api docs = https://www.atom42.org/docs
2. localhost = http://localhost:8000/docs
```





### how to run
1. download atom repo
2. create .env file inside downloaded folder(check env file section)
3. create venv
4. install requirements.txt
5. run python main.py
--using docker
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


