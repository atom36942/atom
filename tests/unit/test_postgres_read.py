import sys
from pathlib import Path
import pytest
import re

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.function import func_postgres_read, func_postgres_serialize, func_postgres_where_build, func_postgres_relation

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
        func_postgres_where_build=func_postgres_where_build,
        func_postgres_relation=func_postgres_relation,
        cache_postgres_schema=schema,
        config_relation_fetch_limit_max=100,
        table="users",
        filter={"id": "=,1"},
        limit=10,
        page=1,
        order="id desc",
        column="id,name",
        relation=None
    )
    
    sql, args = pool.queries[0]
    assert 'FROM "users"' in sql
    assert 'SELECT "id","name"' in sql
    assert '"id" = $1' in sql
    assert 'ORDER BY "id" DESC' in sql
    assert "LIMIT $2 OFFSET $3" in sql
    assert args == (1, 10, 0)

@pytest.mark.asyncio
async def test_postgres_read_relation_fetch_one_to_one():
    # Response for main query
    main_rows = [{"id": 1, "created_by_id": 10}]
    # Response for relation fetch
    relation_rows = [{"id": 10, "name": "admin", "relation_id": 10, "rn": 1}]
    
    pool = FakePool(fetch_responses=[main_rows, relation_rows])
    schema = {
        "posts": {"id": {"datatype": "integer"}, "created_by_id": {"datatype": "integer"}},
        "users": {"id": {"datatype": "integer"}, "name": {"datatype": "text"}}
    }
    
    result = await func_postgres_read(
        client_postgres_pool=pool,
        client_password_hasher=None,
        func_postgres_serialize=func_postgres_serialize,
        func_postgres_where_build=func_postgres_where_build,
        func_postgres_relation=func_postgres_relation,
        cache_postgres_schema=schema,
        config_relation_fetch_limit_max=100,
        table="posts",
        filter={},
        limit=10,
        page=1,
        order="id",
        column="*",
        relation="created_by_id,users,id,fetch|1,username,name"
    )
    
    sql, args = pool.queries[1]
    assert 'FROM "users"' in sql
    assert 'rn <= $2' in sql
    assert args[1] == 1 # Custom limit
    assert result[0]["users"]["name"] == "admin"

@pytest.mark.asyncio
async def test_postgres_read_relation_aggregate():
    pool = FakePool(fetch_responses=[[{"id": 1}], [{"id": 1, "value": 5}]])
    schema = {"posts": {"id": {"datatype": "integer"}}}
    
    result = await func_postgres_read(
        client_postgres_pool=pool,
        client_password_hasher=None,
        func_postgres_serialize=func_postgres_serialize,
        func_postgres_where_build=func_postgres_where_build,
        func_postgres_relation=func_postgres_relation,
        cache_postgres_schema=schema,
        config_relation_fetch_limit_max=100,
        table="posts",
        filter={},
        limit=10,
        page=1,
        order="id",
        column="*",
        relation="id,comments,post_id,count,id"
    )
    
    sql, args = pool.queries[1]
    assert 'SELECT "post_id" AS id, count("id") AS value FROM "comments"' in sql
    assert result[0]["comments_count"] == 5

@pytest.mark.asyncio
async def test_postgres_relation_validation():
    pool = FakePool()
    obj_list = [{"id": 1}]
    
    # 1. Missing limit error
    with pytest.raises(Exception, match="explicit limit required in relation fetch"):
        await func_postgres_relation(
            client_postgres_pool=pool,
            obj_list=obj_list,
            relation="id,comments,post_id,fetch,*",
            config_relation_fetch_limit_max=100
        )
        
    # 2. Exceeding max limit error
    with pytest.raises(Exception, match="exceeds maximum allowed"):
        await func_postgres_relation(
            client_postgres_pool=pool,
            obj_list=obj_list,
            relation="id,comments,post_id,fetch|500,*",
            config_relation_fetch_limit_max=100
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
    
    await func_postgres_read(
        client_postgres_pool=pool,
        client_password_hasher=None,
        func_postgres_serialize=func_postgres_serialize,
        func_postgres_where_build=func_postgres_where_build,
        func_postgres_relation=func_postgres_relation,
        cache_postgres_schema=schema,
        config_relation_fetch_limit_max=100,
        table="test",
        filter={"tags": "any,python"},
        limit=10, page=1, order="id", column="*",
        relation=None
    )
    assert '$1 = ANY("tags")' in pool.queries[-1][0]
    
    # JSONB exists
    await func_postgres_read(
        client_postgres_pool=pool,
        client_password_hasher=None,
        func_postgres_serialize=func_postgres_serialize,
        func_postgres_where_build=func_postgres_where_build,
        func_postgres_relation=func_postgres_relation,
        cache_postgres_schema=schema,
        config_relation_fetch_limit_max=100,
        table="test",
        filter={"meta": "exists,role"},
        limit=10, page=1, order="id", column="*",
        relation=None
    )
    assert '"meta" ? $1' in pool.queries[-1][0]

    # Point distance
    await func_postgres_read(
        client_postgres_pool=pool,
        client_password_hasher=None,
        func_postgres_serialize=func_postgres_serialize,
        func_postgres_where_build=func_postgres_where_build,
        func_postgres_relation=func_postgres_relation,
        cache_postgres_schema=schema,
        config_relation_fetch_limit_max=100,
        table="test",
        filter={"loc": "point,80|15|0|1000"},
        limit=10, page=1, order="id", column="*",
        relation=None
    )
    assert 'ST_Distance("loc", ST_Point($1, $2)::geography) BETWEEN $3 AND $4' in pool.queries[-1][0]

@pytest.mark.asyncio
async def test_postgres_read_json_and_logical_filters():
    import orjson
    pool = FakePool(fetch_responses=[[]])
    schema = {"posts": {"id": {"datatype": "integer"}, "status": {"datatype": "text"}, "category": {"datatype": "text"}}}
    
    # Test JSON string 'filter' parameter
    complex_filter = {
        "status": "in,active|pending",
        "_or": [
            {"category": "=,news"},
            {"id": ">,100"}
        ]
    }
    
    await func_postgres_read(
        client_postgres_pool=pool,
        client_password_hasher=None,
        func_postgres_serialize=func_postgres_serialize,
        func_postgres_where_build=func_postgres_where_build,
        func_postgres_relation=func_postgres_relation,
        cache_postgres_schema=schema,
        config_relation_fetch_limit_max=100,
        table="posts",
        filter={"filter": orjson.dumps(complex_filter).decode()},
        limit=10, page=1, order="id", column="*",
        relation=None
    )
    
    sql, args = pool.queries[-1]
    # Check for both conditions and the logical grouping
    assert '"status" IN ($1,$2)' in sql
    assert '("category" = $3  OR  "id" > $4)' in sql
    assert args == ("active", "pending", "news", 100, 10, 0)

    
    # Test explicit operator requirement (Failure case)
    with pytest.raises(Exception, match="Expected 'operator,value'"):
        await func_postgres_read(
            client_postgres_pool=pool,
            client_password_hasher=None,
            func_postgres_serialize=func_postgres_serialize,
            func_postgres_where_build=func_postgres_where_build,
            func_postgres_relation=func_postgres_relation,
            cache_postgres_schema=schema,
            config_relation_fetch_limit_max=100,
            table="posts",
            filter={"status": "active"}, # MISSING COMMA
            limit=10, page=1, order="id", column="*",
            relation=None
        )

