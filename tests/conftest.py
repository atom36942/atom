import os

# Clear configuration environment variables to avoid triggering real connections during tests
# This must happen before any core.* modules are imported
for key in list(os.environ.keys()):
    if key.startswith("config_") and "url" in key.lower():
        os.environ[key] = ""

os.environ["config_postgres_url"] = ""
os.environ["config_redis_url"] = ""
os.environ["config_mongodb_url"] = ""
os.environ["config_rabbitmq_url"] = ""
os.environ["config_kafka_url"] = ""
