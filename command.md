# git
```
git init
git remote add origin https://github.com/atom36942123/atom.git
git branch -M main
```

# venv
```
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip freeze > requirements.txt
pip list --outdated | tail -n +3 | awk '{print $1}' | xargs -n1 pip install --upgrade
```

# postgres install
```
brew install postgresql@17
brew services start postgresql@17
psql postgresql://atom:123@localhost/postgres
```

# redis install
```
brew install redis
brew services start redis
redis-cli -u redis://localhost
```

# postgres reset
```
drop schema if exists public cascade;
create schema if not exists public;
```

# postgres exim
```
export_all=\copy post to 'path'  delimiter ',' csv header;
export_column=\copy (query) to 'path'  delimiter ',' csv header;
import_column=\copy post(column) from 'path' delimiter ',' csv header;
```

# misc
```
pid kill = lsof -ti :8000 | xargs kill -9
git commit delete = git reset --hard HEAD~3 / git push origin main --force
postgres table rows count = SELECT relname AS table_name,n_live_tup AS row_count FROM pg_stat_user_tables;
```

