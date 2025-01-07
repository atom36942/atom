### about atom
1. Atom is an open-source backend framework with pre-built, reusable modules for commonly required functionalities, reducing the need for repetitive development.
2. Designed to significantly reduce development time, enabling faster project completion and iteration cycles.
3. Atom’s mission is to empower entrepreneurs to launch and scale their ideas quickly without extensive backend overhead.
4. Atom is highly flexible and unopinionated, making it suitable for building the backend of a wide variety of applications and domains.
5. Built on a robust stack of Python, FastAPI, PostgreSQL, and Redis for high performance and scalability.
6. Atom avoids traditional ORMs, leveraging raw SQL for greater control, optimized queries, and database flexibility.
7. Supports high-throughput data ingestion pipelines using RabbitMQ, LavinMQ, or Kafka.
8. Implements object-level CRUD operations by directly interacting with the database schema, ensuring efficient serialization and deserialization.
9. Enables entire business schema generation from a single JSON configuration, simplifying initial setup and iterations.
10. ex - linkedin backend can be built in apporx 2-3 weeks.

### coding paradigm
Atom leverages a hybrid programming paradigm, integrating procedural and functional principles while adhering to SOLID design principles for scalable and maintainable codebases. Procedural programming structures code into discrete, reusable units called procedures, akin to functions, which encapsulate local state and provide controlled access to global state. This paradigm emphasizes modularity, enabling clear separation of concerns and fostering efficient memory usage and data encapsulation. By combining these paradigms, Atom ensures robustness and flexibility for building large-scale,high-performance applications.

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


