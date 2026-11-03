# command: venv/bin/python -m script.consumer_celery channel_object_create
# command: venv/bin/python -m script.consumer_celery channel_object_update

# info: Listens on one Celery channel and runs that channel's function (func_consumer_channels) for each message.

# import
import os
import sys
from dotenv import load_dotenv
from config import config_buffer_limit_default
from config import config_buffer_rows_max
from config import config_column_regex
from config import config_table
from function import func_consumer_channels
from function import func_consumer_run

# config
load_dotenv(".env")
config_postgres_url_master = os.getenv("config_postgres_url_master")
config_celery_url = os.getenv("config_celery_url")

# setting

# logic
def main():
    channel = sys.argv[1] if len(sys.argv) > 1 else None    # the channel to listen on
    if channel not in func_consumer_channels(): sys.exit(f"Error: channel is required. Usage: venv/bin/python -m script.consumer_celery <{'|'.join(func_consumer_channels())}>")
    func_consumer_run(queue="celery", channel=channel, broker_settings={"config_celery_url": config_celery_url}, postgres_url=config_postgres_url_master, config_column_regex=config_column_regex, config_table=config_table, config_buffer_limit_default=config_buffer_limit_default, config_buffer_rows_max=config_buffer_rows_max)

# main
if __name__ == "__main__":
    main()
