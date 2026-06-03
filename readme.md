# Direct Deployment
```bash
git clone https://github.com/atom36942/atom.git
cd atom
rm -rf venv
/opt/homebrew/bin/python3.11 -m venv venv
venv/bin/pip install --upgrade pip
venv/bin/pip install -r requirements.txt
venv/bin/python main.py
venv/bin/uvicorn main:app --reload
```

# Docker Deployment
```bash
git clone https://github.com/atom36942/atom.git
cd atom
docker build -t atom .
docker run --rm -p 8000:8000 atom
```
