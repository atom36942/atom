import pytest
import os
from core.function.postgres_util import func_postgres_sql_parallel
from core.config import config_postgres_url

@pytest.mark.asyncio
async def test_func_postgres_sql_parallel_success():
    # Setup: Create a list of simple SQL queries
    sql_list = [
        "CREATE TEMP TABLE test_parallel_1 (id serial, val text);",
        "INSERT INTO test_parallel_1 (val) VALUES ('a'), ('b');",
        "SELECT * FROM test_parallel_1;"
    ]
    
    # We use the real connection string from config
    result = func_postgres_sql_parallel(conn_str=config_postgres_url, sql_list=sql_list)
    
    # The function returns "done" on completion
    assert result == "done"

def test_func_postgres_sql_parallel_empty():
    result = func_postgres_sql_parallel(conn_str=config_postgres_url, sql_list=[])
    assert result == "done"

@pytest.mark.asyncio
async def test_func_postgres_sql_parallel_partial_failure():
    # One valid, one invalid SQL
    sql_list = [
        "SELECT 1;",
        "SELECT * FROM non_existent_table_999;"
    ]
    
    # Even with failures, the function should complete and return "done"
    # It prints errors to stdout but doesn't raise exception for the whole batch
    result = func_postgres_sql_parallel(conn_str=config_postgres_url, sql_list=sql_list)
    assert result == "done"
