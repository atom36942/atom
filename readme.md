## about
atom is an open-source backend framework designed to accelerate development of large-scale applications. It follows a clean, modular architecture combining functional and procedural programming styles, prioritizing pure functions and low side-effects. With out-of-the-box support for Postgres, Redis, S3, Kafka, and more, atom provides a comprehensive toolkit to quickly scaffold and deploy production-ready APIs, background jobs, and integrations—without reinventing the wheel.

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