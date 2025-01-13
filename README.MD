### about atom
```
Open-source backend framework with reusable modules to minimize repetitive development.
Speeds up development, enabling faster project delivery and iteration.
Helps entrepreneurs launch and scale ideas quickly with minimal backend effort.
Flexible and unopinionated, suitable for diverse applications.
Built on Python, FastAPI, PostgreSQL, and Redis for performance and scalability.
Uses raw SQL instead of ORMs for optimized queries and greater control.
Supports high-throughput data pipelines with RabbitMQ, LavinMQ, or Kafka.
Offers object-level CRUD operations by interacting directly with the database schema.
Simplifies setup by generating business schemas from a single JSON configuration.
Example: Build a LinkedIn-like backend in just 2-3 weeks.
```

### coding paradigm
Atom leverages a hybrid programming paradigm, integrating procedural and functional principles while adhering to SOLID design principles for scalable and maintainable codebases. Procedural programming structures code into discrete, reusable units called procedures, akin to functions, which encapsulate local state and provide controlled access to global state. This paradigm emphasizes modularity, enabling clear separation of concerns and fostering efficient memory usage and data encapsulation. By combining these paradigms, Atom ensures robustness and flexibility for building large-scale,high-performance applications.

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


