from core.app import app
import sys
from pathlib import Path
import pytest
import re

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


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

class ExplodingPool:
    async def fetch(self, *args):
        raise AssertionError("pool fetch should not be used when a relation connection is provided")

class RecordingConn:
    def __init__(self, fetch_responses=None):
        self.fetch_responses = fetch_responses or []
        self.queries = []
    async def fetch(self, sql, *args):
        self.queries.append((sql, args))
        if self.fetch_responses:
            return self.fetch_responses.pop(0)
        return []

@pytest.mark.asyncio
async def test_postgres_read_identifier_quoting_and_basic_logic():
    pool = FakePool(fetch_responses=[[{"id": 1, "name": "test"}]])
    schema = {"users": {"id": {"datatype": "integer"}, "name": {"datatype": "text"}}}
    
    await app.state.func_postgres_read(
        client_postgres_pool=pool,
        client_password_hasher=None,
        func_postgres_serialize=app.state.func_postgres_serialize,
        func_postgres_where_build=app.state.func_postgres_where_build,
        func_postgres_relation=app.state.func_postgres_relation,
        cache_postgres_schema=schema,
        config_relation_fetch_limit_max=100,
        table="users",
        filter=[{"id": "=,1"}],
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
    
    result = await app.state.func_postgres_read(
        client_postgres_pool=pool,
        client_password_hasher=None,
        func_postgres_serialize=app.state.func_postgres_serialize,
        func_postgres_where_build=app.state.func_postgres_where_build,
        func_postgres_relation=app.state.func_postgres_relation,
        cache_postgres_schema=schema,
        config_relation_fetch_limit_max=100,
        table="posts",
        filter=[],
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
    
    result = await app.state.func_postgres_read(
        client_postgres_pool=pool,
        client_password_hasher=None,
        func_postgres_serialize=app.state.func_postgres_serialize,
        func_postgres_where_build=app.state.func_postgres_where_build,
        func_postgres_relation=app.state.func_postgres_relation,
        cache_postgres_schema=schema,
        config_relation_fetch_limit_max=100,
        table="posts",
        filter=[],
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
async def test_postgres_read_empty_order_defaults_to_id_desc():
    pool = FakePool(fetch_responses=[[]])
    schema = {"posts": {"id": {"datatype": "integer"}}}

    await app.state.func_postgres_read(
        client_postgres_pool=pool,
        client_password_hasher=None,
        func_postgres_serialize=app.state.func_postgres_serialize,
        func_postgres_where_build=app.state.func_postgres_where_build,
        func_postgres_relation=app.state.func_postgres_relation,
        cache_postgres_schema=schema,
        config_relation_fetch_limit_max=100,
        table="posts",
        filter=[],
        limit=10,
        page=1,
        order="",
        column="*",
        relation=None
    )

    assert 'ORDER BY "id" DESC' in pool.queries[0][0]

@pytest.mark.asyncio
async def test_postgres_relation_requires_selected_source_column():
    pool = FakePool()

    with pytest.raises(Exception, match="relation source column missing from selected columns: created_by_id"):
        await app.state.func_postgres_relation(
            client_postgres_pool=pool,
            obj_list=[{"id": 1, "title": "hello"}],
            relation="created_by_id,users,id,fetch|1,name",
            config_relation_fetch_limit_max=100
        )

@pytest.mark.asyncio
async def test_postgres_relation_uses_provided_connection():
    conn = RecordingConn(fetch_responses=[[{"id": 1, "value": 2}]])

    result = await app.state.func_postgres_relation(
        client_postgres_pool=ExplodingPool(),
        client_postgres_conn=conn,
        obj_list=[{"id": 1}],
        relation="id,comments,post_id,count,id",
        config_relation_fetch_limit_max=100
    )

    assert len(conn.queries) == 1
    assert result[0]["comments_count"] == 2

@pytest.mark.asyncio
async def test_postgres_relation_validation():
    pool = FakePool()
    obj_list = [{"id": 1}]
    
    # 1. Missing limit error
    with pytest.raises(Exception, match="explicit limit required in relation fetch"):
        await app.state.func_postgres_relation(
            client_postgres_pool=pool,
            obj_list=obj_list,
            relation="id,comments,post_id,fetch,*",
            config_relation_fetch_limit_max=100
        )
        
    # 2. Exceeding max limit error
    with pytest.raises(Exception, match="exceeds maximum allowed"):
        await app.state.func_postgres_relation(
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
    
    await app.state.func_postgres_read(
        client_postgres_pool=pool,
        client_password_hasher=None,
        func_postgres_serialize=app.state.func_postgres_serialize,
        func_postgres_where_build=app.state.func_postgres_where_build,
        func_postgres_relation=app.state.func_postgres_relation,
        cache_postgres_schema=schema,
        config_relation_fetch_limit_max=100,
        table="test",
        filter=[{"tags": "any,python"}],
        limit=10, page=1, order="id", column="*",
        relation=None
    )
    assert '$1 = ANY("tags")' in pool.queries[-1][0]
    
    # JSONB exists
    await app.state.func_postgres_read(
        client_postgres_pool=pool,
        client_password_hasher=None,
        func_postgres_serialize=app.state.func_postgres_serialize,
        func_postgres_where_build=app.state.func_postgres_where_build,
        func_postgres_relation=app.state.func_postgres_relation,
        cache_postgres_schema=schema,
        config_relation_fetch_limit_max=100,
        table="test",
        filter=[{"meta": "exists,role"}],
        limit=10, page=1, order="id", column="*",
        relation=None
    )
    assert '"meta" ? $1' in pool.queries[-1][0]

    # Point distance
    await app.state.func_postgres_read(
        client_postgres_pool=pool,
        client_password_hasher=None,
        func_postgres_serialize=app.state.func_postgres_serialize,
        func_postgres_where_build=app.state.func_postgres_where_build,
        func_postgres_relation=app.state.func_postgres_relation,
        cache_postgres_schema=schema,
        config_relation_fetch_limit_max=100,
        table="test",
        filter=[{"loc": "point,80|15|0|1000"}],
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
    
    await app.state.func_postgres_read(
        client_postgres_pool=pool,
        client_password_hasher=None,
        func_postgres_serialize=app.state.func_postgres_serialize,
        func_postgres_where_build=app.state.func_postgres_where_build,
        func_postgres_relation=app.state.func_postgres_relation,
        cache_postgres_schema=schema,
        config_relation_fetch_limit_max=100,
        table="posts",
        filter=[complex_filter],
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
        await app.state.func_postgres_read(
            client_postgres_pool=pool,
            client_password_hasher=None,
            func_postgres_serialize=app.state.func_postgres_serialize,
            func_postgres_where_build=app.state.func_postgres_where_build,
            func_postgres_relation=app.state.func_postgres_relation,
            cache_postgres_schema=schema,
            config_relation_fetch_limit_max=100,
            table="posts",
            filter=[{"status": "active"}], # MISSING COMMA (still fails but now it's a list)
            limit=10, page=1, order="id", column="*",
            relation=None
        )

@pytest.mark.asyncio
async def test_postgres_read_flat_list_filters():
    pool = FakePool(fetch_responses=[[]])
    schema = {"posts": {"id": {"datatype": "integer"}, "status": {"datatype": "text"}, "title": {"datatype": "text"}}}
    
    # Test flat list filter
    flat_filter = [
        "id > 100",
        "status = 'active'",
        "title ILIKE '%apple%' OR title ILIKE '%samsung%'"
    ]
    
    await app.state.func_postgres_read(
        client_postgres_pool=pool,
        client_password_hasher=None,
        func_postgres_serialize=app.state.func_postgres_serialize,
        func_postgres_where_build=app.state.func_postgres_where_build,
        func_postgres_relation=app.state.func_postgres_relation,
        cache_postgres_schema=schema,
        config_relation_fetch_limit_max=100,
        table="posts",
        filter=flat_filter,
        limit=10, page=1, order="id", column="*",
        relation=None
    )
    
    sql, args = pool.queries[-1]
    assert '"id" > $1' in sql
    assert '"status" = $2' in sql
    assert '("title" ILIKE $3  OR  "title" ILIKE $4)' in sql
    assert args == (100, "active", "%apple%", "%samsung%", 10, 0)

@pytest.mark.asyncio
async def test_postgres_read_flat_list_preserves_repeated_columns():
    pool = FakePool(fetch_responses=[[]])
    schema = {"posts": {"status": {"datatype": "integer"}, "title": {"datatype": "text"}}}
    flat_filter = [
        "status = 1",
        "status in 1|2|3",
        "title ILIKE %apple%",
    ]

    await app.state.func_postgres_read(
        client_postgres_pool=pool,
        client_password_hasher=None,
        func_postgres_serialize=app.state.func_postgres_serialize,
        func_postgres_where_build=app.state.func_postgres_where_build,
        func_postgres_relation=app.state.func_postgres_relation,
        cache_postgres_schema=schema,
        config_relation_fetch_limit_max=100,
        table="posts",
        filter=flat_filter,
        limit=10, page=1, order="id", column="*",
        relation=None
    )

    sql, args = pool.queries[-1]
    assert '"status" = $1' in sql
    assert '"status" IN ($2,$3,$4)' in sql
    assert '"title" ILIKE $5' in sql
    assert args == (1, 1, 2, 3, "%apple%", 10, 0)

@pytest.mark.asyncio
async def test_postgres_read_flat_list_prefers_longer_operator_matches():
    pool = FakePool(fetch_responses=[[]])
    schema = {
        "posts": {
            "published_at": {"datatype": "timestamptz"},
            "owner_id": {"datatype": "integer"},
            "price": {"datatype": "numeric(10,2)"},
            "slug": {"datatype": "text"},
        }
    }
    flat_filter = [
        "published_at is not null",
        "owner_id is not distinct from 1",
        "price >= 100",
        "slug ~* ^post-",
    ]

    await app.state.func_postgres_read(
        client_postgres_pool=pool,
        client_password_hasher=None,
        func_postgres_serialize=app.state.func_postgres_serialize,
        func_postgres_where_build=app.state.func_postgres_where_build,
        func_postgres_relation=app.state.func_postgres_relation,
        cache_postgres_schema=schema,
        config_relation_fetch_limit_max=100,
        table="posts",
        filter=flat_filter,
        limit=10, page=1, order="id", column="*",
        relation=None
    )

    sql, args = pool.queries[-1]
    assert '"published_at" IS NOT NULL' in sql
    assert '"owner_id" IS NOT DISTINCT FROM $1' in sql
    assert '"price" >= $2' in sql
    assert '"slug" ~* $3' in sql
    assert args == (1, 100.0, "^post-", 10, 0)
