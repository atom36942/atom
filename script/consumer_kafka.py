# type: continuous

# command: venv/bin/python -m script.consumer_kafka channel_object_create
# command: venv/bin/python -m script.consumer_kafka channel_object_update

# info: Listens on one Kafka channel and runs that channel's function (func_consumer_channels) for each message.

# import
import os
import sys
from dotenv import load_dotenv
from config import config_buffer_limit_default
from config import config_buffer_rows_max
from config import config_column_regex
from config import config_queue_concurrency
from config import config_queue_retry_max
from config import config_queue_retry_wait_sec
from config import config_table
from function import func_consumer_channels
from function import func_consumer_run

# config
load_dotenv(".env")
config_postgres_url_master = os.getenv("config_postgres_url_master")
config_kafka_url = os.getenv("config_kafka_url")
config_kafka_username = os.getenv("config_kafka_username")
config_kafka_password = os.getenv("config_kafka_password")

# setting

# logic
def main():
    channel = sys.argv[1] if len(sys.argv) > 1 else None    # the channel to listen on
    if channel not in func_consumer_channels(): sys.exit(f"Error: channel is required. Usage: venv/bin/python -m script.consumer_kafka <{'|'.join(func_consumer_channels())}>")
    func_consumer_run(queue="kafka", channel=channel, broker_settings={"config_kafka_url": config_kafka_url, "config_kafka_username": config_kafka_username, "config_kafka_password": config_kafka_password}, postgres_url=config_postgres_url_master, config_column_regex=config_column_regex, config_table=config_table, config_buffer_limit_default=config_buffer_limit_default, config_buffer_rows_max=config_buffer_rows_max, config_queue_concurrency=config_queue_concurrency, config_queue_retry_max=config_queue_retry_max, config_queue_retry_wait_sec=config_queue_retry_wait_sec)

# main
if __name__ == "__main__":
    main()
