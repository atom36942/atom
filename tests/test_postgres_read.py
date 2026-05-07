import sys
from pathlib import Path
import pytest
import re

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.function import func_postgres_read, func_postgres_serialize

class FakeAcquire:
    def __init__(self, conn):
        self.conn = conn
    async def __aenter__(self): return self.conn
    async def __aexit__(self, exc_type, exc, tb): return False

class FakePool:
    def __init__(self, fetch_responses=None):
        self.fetch_responses = fetch_responses or []
        self.queries = []
    def acquire(self):
        return FakeAcquire(self)
    async def fetch(self, sql, *args):
        self.queries.append((sql, args))
        if self.fetch_responses:
            return self.fetch_responses.pop(0)
        return []

@pytest.mark.asyncio
async def test_postgres_read_identifier_quoting_and_basic_logic():
    pool = FakePool(fetch_responses=[[{"id": 1, "name": "test"}]])
    schema = {"users": {"id": {"datatype": "integer"}, "name": {"datatype": "text"}}}
    
    await func_postgres_read(
        client_postgres_pool=pool,
        client_password_hasher=None,
        func_postgres_serialize=func_postgres_serialize,
        cache_postgres_schema=schema,
        table="users",
        filter_obj={"id": "=,1"},
        limit=10,
        page=1,
        order="id desc",
        column="id,name",
        creator_key=None,
        action_key=None
    )
    
    sql, args = pool.queries[0]
    # Check table quoting
    assert 'FROM "users"' in sql
    # Check column quoting
    assert 'SELECT "id","name"' in sql
    # Check filter quoting
    assert '"id" = $1' in sql
    # Check order quoting
    assert 'ORDER BY "id" DESC' in sql
    # Check limit/offset
    assert "LIMIT $2 OFFSET $3" in sql
    assert args == (1, 10, 0)

@pytest.mark.asyncio
async def test_postgres_read_creator_key_optimization():
    # Response for main query
    main_rows = [{"id": 1, "created_by_id": 10}]
    # Response for creator query
    creator_rows = [{"id": 10, "name": "admin"}]
    
    pool = FakePool(fetch_responses=[main_rows, creator_rows])
    schema = {
        "posts": {"id": {"datatype": "integer"}, "created_by_id": {"datatype": "integer"}},
        "users": {"id": {"datatype": "integer"}, "name": {"datatype": "text"}, "secret": {"datatype": "text"}}
    }
    
    result = await func_postgres_read(
        client_postgres_pool=pool,
        client_password_hasher=None,
        func_postgres_serialize=func_postgres_serialize,
        cache_postgres_schema=schema,
        table="posts",
        filter_obj={},
        limit=10,
        page=1,
        order="id",
        column="*",
        creator_key="name",
        action_key=None
    )
    
    # Second query should be the creator fetch
    sql, args = pool.queries[1]
    assert 'SELECT "name","id" FROM users' in sql
    assert args[0] == [10]
    assert result[0]["creator_name"] == "admin"

@pytest.mark.asyncio
async def test_postgres_read_action_key_validation_and_security():
    pool = FakePool(fetch_responses=[[{"id": 1}], [{"id": 1, "value": 5}]])
    schema = {"posts": {"id": {"datatype": "integer"}}}
    
    # Valid action_key
    await func_postgres_read(
        client_postgres_pool=pool,
        client_password_hasher=None,
        func_postgres_serialize=func_postgres_serialize,
        cache_postgres_schema=schema,
        table="posts",
        filter_obj={},
        limit=10,
        page=1,
        order="id",
        column="*",
        creator_key=None,
        action_key="comments,post_id,count,id"
    )
    
    sql, args = pool.queries[1]
    assert 'SELECT "post_id" AS id, count("id") AS value FROM "comments"' in sql
    
    # Invalid action_key (malicious table name)
    # We need result_list to be non-empty for action_key logic to trigger
    pool.fetch_responses = [[{"id": 1}]]
    with pytest.raises(Exception, match="invalid identifier in action_key"):
        await func_postgres_read(
            client_postgres_pool=pool,
            client_password_hasher=None,
            func_postgres_serialize=func_postgres_serialize,
            cache_postgres_schema=schema,
            table="posts",
            filter_obj={},
            limit=10,
            page=1,
            order="id",
            column="*",
            creator_key=None,
            action_key="comments; DROP TABLE users,post_id,count,id"
        )

    # Invalid action_op
    pool.fetch_responses = [[{"id": 1}]]
    with pytest.raises(Exception, match="invalid action operator"):
        await func_postgres_read(
            client_postgres_pool=pool,
            client_password_hasher=None,
            func_postgres_serialize=func_postgres_serialize,
            cache_postgres_schema=schema,
            table="posts",
            filter_obj={},
            limit=10,
            page=1,
            order="id",
            column="*",
            creator_key=None,
            action_key="comments,post_id,MALICIOUS,id"
        )

@pytest.mark.asyncio
async def test_postgres_read_complex_filters():
    pool = FakePool(fetch_responses=[[]])
    schema = {
        "test": {
            "tags": {"datatype": "text[]"},
            "meta": {"datatype": "jsonb"},
            "loc": {"datatype": "geography"}
        }
    }
    
    # Array ANY
    await func_postgres_read(
        client_postgres_pool=pool,
        client_password_hasher=None,
        func_postgres_serialize=func_postgres_serialize,
        cache_postgres_schema=schema,
        table="test",
        filter_obj={"tags": "any,python"},
        limit=10, page=1, order="id", column="*",
        creator_key=None, action_key=None
    )
    assert '$1 = ANY("tags")' in pool.queries[-1][0]
    
    # JSONB exists
    await func_postgres_read(
        client_postgres_pool=pool,
        client_password_hasher=None,
        func_postgres_serialize=func_postgres_serialize,
        cache_postgres_schema=schema,
        table="test",
        filter_obj={"meta": "exists,role"},
        limit=10, page=1, order="id", column="*",
        creator_key=None, action_key=None
    )
    assert '"meta" ? $1' in pool.queries[-1][0]

    # Point distance
    await func_postgres_read(
        client_postgres_pool=pool,
        client_password_hasher=None,
        func_postgres_serialize=func_postgres_serialize,
        cache_postgres_schema=schema,
        table="test",
        filter_obj={"loc": "point,80|15|0|1000"},
        limit=10, page=1, order="id", column="*",
        creator_key=None, action_key=None
    )
    assert 'ST_Distance("loc", ST_Point($1, $2)::geography) BETWEEN $3 AND $4' in pool.queries[-1][0]
