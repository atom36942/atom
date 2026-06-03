# Deployment
```bash
#Direct
git clone https://github.com/atom36942/atom.git
cd atom
rm -rf venv
/opt/homebrew/bin/python3.11 -m venv venv
venv/bin/python -V
venv/bin/pip install --upgrade pip
venv/bin/pip install -r requirements.txt
venv/bin/python main.py
venv/bin/uvicorn main:app --reload

# Docker
docker build -t atom .
docker run --rm -p 8000:8000 atom
```

# Commands
```bash
# Script Start
venv/bin/python -m script.<script_name_without_py>
venv/bin/python -m script.<consumer_name_without_py> [redis|rabbitmq|kafka|celery]
```
