### brew setup
```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.zprofile
eval "$(/opt/homebrew/bin/brew shellenv)"
brew install python@3.11
brew install postgis
brew install postgresql && brew install redis && brew install rabbitmq && brew tap mongodb/brew && brew install mongodb-community && echo 'export PATH="/opt/homebrew/sbin:$PATH"' >> ~/.zshrc && source ~/.zshrc
brew services start postgresql && brew services start redis && brew services start rabbitmq && brew services start mongodb-community
brew services restart postgresql && brew services restart redis && brew services start rabbitmq && brew services start mongodb-community
brew services stop postgresql && brew services stop redis && brew services stop rabbitmq && brew services stop mongodb-community
brew update && brew upgrade postgresql && brew upgrade redis && brew upgrade rabbitmq && brew upgrade mongodb-community && brew services restart --all
brew services stop --all && brew uninstall --force postgresql && brew uninstall --force redis && brew uninstall --force rabbitmq && brew uninstall --force mongodb-community && rm -rf /opt/homebrew/var/postgres /opt/homebrew/var/db/redis /opt/homebrew/var/lib/rabbitmq /opt/homebrew/var/mongodb && brew cleanup
psql --version && redis-cli --version && rabbitmqctl version && mongosh --version && mongod --version
brew services list && nc -zv 127.0.0.1 5432 6379 5672 27017
brew services list
```

### github setup repo as dev
```bash
ssh-keygen -t ed25519 -C "atom36942@gmail.com"
cat ~/.ssh/id_ed25519.pub
ssh -T git@github.com
git clone git@github.com:atom36942/atom.git
cd atom
git remote set-url origin git@github.com:atom36942/atom.git
git pull origin main
git add .
git commit -m "sync"
git push origin main
```

### env
```bash
config_postgres_url=postgresql://atom@127.0.0.1/postgres
config_redis_url=redis://localhost:6379
config_rabbitmq_url=amqp://guest:guest@localhost:5672
config_mongodb_url=mongodb://localhost:27017
```

### package
```bash
./venv/bin/pip install fastapi
./venv/bin/pip uninstall fastapi
./venv/bin/pip install --upgrade fastapi
./venv/bin/pip install -r requirements.txt
./venv/bin/pip freeze > requirements.txt
```

### psql
```bash
psql --version
psql -U atom -d postgres
psql postgres
\x off
psql postgres -c "\du"
psql postgres -c "\l"
\c snp;
```

### psql user setup
```bash
psql postgres -c "CREATE USER user_1;"
psql postgres -c "ALTER USER user_1 WITH PASSWORD '123';"
psql postgres -c "ALTER USER user_1 NOSUPERUSER NOCREATEDB NOCREATEROLE;"
psql postgres -c "CREATE DATABASE db_1 OWNER user_1;"
psql -U user_1 -d db_1
postgresql://user_1:123@127.0.0.1/db_1
```

### exim postgres
```bash
\copy test to 'tmp/file.csv' csv header;
\copy (select * from test limit 1000) to 'file.csv' csv header;
\copy test(title,type,rating) from 'file.csv' delimiter ',' csv header;
```

### zzz
```bash
drop schema if exists public cascade;
create schema if not exists public;
lsof -ti :8000 | xargs kill -9
uuidgen | tr '[:upper:]' '[:lower:]' | tr -d '-'
head -n 2 snp2.csv
pgweb --url "postgresql://atom@127.0.0.1/postgres?sslmode=disable"
```
