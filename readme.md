## about
- **Open-source backend framework** to speed up large-scale application development  
- **Clean, modular architecture** combining functional and procedural styles  
- **Pure functions** used to minimize side effects and improve testability  
- **Built-in support** for Postgres, Redis, S3, Kafka, and many other services  
- **Fast scaffolding** of production-ready APIs, background jobs, and integrations  
- **Reduces boilerplate**, so you don’t have to reinvent the wheel each time

## setup
mac
```bash
git clone https://github.com/atom36942/atom.git
cd atom
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```
## server start
direct
```bash
python main.py
```
using reload
```bash
uvicorn main:app --reload
```
without env activate
```bash
./venv/bin/uvicorn main:app --reload
```
## docker start
```bash
docker build -t atom .
docker run -p 8000:8000 atom
```