## what is atom
atom is an open-source backend framework designed to accelerate development of large-scale applications. It follows a clean, modular architecture combining functional and procedural programming styles, prioritizing pure functions and low side-effects. With out-of-the-box support for Postgres, Redis, S3, Kafka, and more, atom provides a comprehensive toolkit to quickly scaffold and deploy production-ready APIs, background jobs, and integrations—without reinventing the wheel.

## how to run using Docker
```bash
docker build -t atom .
docker run -p 8000:8000 atom
