import pytest
from core.function.postgres_util import func_postgres_runner, func_postgres_map_column, func_postgres_clean

# ===========================================================================
# Runner
# ===========================================================================
@pytest.mark.asyncio
async def test_runner_read(state, db_available):
    result = await func_postgres_runner(
        client_postgres_pool=state.client_postgres_pool, mode="read", query="SELECT 1 AS val"
    )
    assert result is not None

@pytest.mark.asyncio
async def test_runner_drop_blocked(state, db_available):
    with pytest.raises(Exception, match="drop"):
        await func_postgres_runner(
            client_postgres_pool=state.client_postgres_pool, mode="write", query="DROP TABLE test"
        )

@pytest.mark.asyncio
async def test_runner_truncate_blocked(state, db_available):
    with pytest.raises(Exception, match="truncate"):
        await func_postgres_runner(
            client_postgres_pool=state.client_postgres_pool, mode="write", query="TRUNCATE test"
        )

@pytest.mark.asyncio
async def test_runner_delete_blocked(state, db_available):
    with pytest.raises(Exception, match="delete"):
        await func_postgres_runner(
            client_postgres_pool=state.client_postgres_pool, mode="write", query="DELETE FROM test"
        )

@pytest.mark.asyncio
async def test_runner_invalid_mode(state):
    with pytest.raises(Exception, match="invalid mode"):
        await func_postgres_runner(
            client_postgres_pool=state.client_postgres_pool, mode="invalid", query="SELECT 1"
        )

@pytest.mark.asyncio
async def test_runner_read_mode_blocks_insert(state):
    with pytest.raises(Exception, match="restricted"):
        await func_postgres_runner(
            client_postgres_pool=state.client_postgres_pool, mode="read", query="INSERT INTO test (title) VALUES ('hack')"
        )

# ===========================================================================
# Map column
# ===========================================================================
@pytest.mark.asyncio
async def test_map_column(state, db_available):
    result = await func_postgres_map_column(
        client_postgres_pool=state.client_postgres_pool,
        config_sql="select id,role from users where role is not null order by id asc limit 10"
    )
    assert isinstance(result, dict)
    assert 1 in result  # root user

@pytest.mark.asyncio
async def test_map_column_empty_sql(state):
    result = await func_postgres_map_column(
        client_postgres_pool=state.client_postgres_pool, config_sql=""
    )
    assert result == {}

@pytest.mark.asyncio
async def test_map_column_none_sql(state):
    result = await func_postgres_map_column(
        client_postgres_pool=state.client_postgres_pool, config_sql=None
    )
    assert result == {}

# ===========================================================================
# Clean (retention)
# ===========================================================================
@pytest.mark.asyncio
async def test_clean_no_config(state):
    result = await func_postgres_clean(client_postgres_pool=state.client_postgres_pool, config_table={})
    assert result is None

@pytest.mark.asyncio
async def test_clean_with_retention(state, db_available):
    """Clean should not error with valid retention config."""
    result = await func_postgres_clean(
        client_postgres_pool=state.client_postgres_pool,
        config_table={"log_api": {"retention_day": 30}}
    )
    assert result is None
