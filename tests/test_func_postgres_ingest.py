import pytest
import os
import csv
import asyncpg
from unittest.mock import patch
from core.function.postgres_ingest import func_postgres_csv_ingestion
from core.config import config_postgres_url

# Test constants
TEST_TABLE = "test_ingest_table"
TEST_CSV = "tmp/test_ingest_data.csv"

@pytest.fixture(scope="module")
async def setup_ingest_table():
    # Attempt to create a real table for testing
    try:
        conn = await asyncpg.connect(config_postgres_url, timeout=5)
        await conn.execute(f"DROP TABLE IF EXISTS {TEST_TABLE};")
        await conn.execute(f"""
            CREATE TABLE {TEST_TABLE} (
                id BIGINT PRIMARY KEY,
                name TEXT,
                age INT,
                status INT DEFAULT 0,
                category TEXT
            );
        """)
        await conn.close()
        is_mock = False
    except Exception as e:
        print(f"\n⚠️  Note: Connection to {config_postgres_url} failed ({e}). Falling back to Mocks/Skips.")
        is_mock = True
    
    # Create a base temporary CSV
    os.makedirs("tmp", exist_ok=True)
    with open(TEST_CSV, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["uid", "full_name", "user_age", "extra_info"])
        writer.writerow(["1", "Alice", "25", "extra1"])
        writer.writerow(["2", "Bob", "30", "extra2"])
    
    yield {"is_mock": is_mock}
    
    # Cleanup
    if not is_mock:
        try:
            conn = await asyncpg.connect(config_postgres_url, timeout=5)
            await conn.execute(f"DROP TABLE IF EXISTS {TEST_TABLE};")
            await conn.close()
        except Exception: pass
            
    if os.path.exists(TEST_CSV): os.remove(TEST_CSV)

@pytest.mark.asyncio
async def test_ingest_create_full_permutation(setup_ingest_table):
    """Test CREATE with rename, ignore, and const columns all at once."""
    if setup_ingest_table["is_mock"]: pytest.skip("DB unreachable")

    with patch('builtins.input', return_value='y'):
        await func_postgres_csv_ingestion(
            csv_path=TEST_CSV,
            pg_dsn=config_postgres_url,
            table=TEST_TABLE,
            crud_mode="create",
            validation_mode="strict",
            rename_column=[["uid", "id"], ["full_name", "name"], ["user_age", "age"]],
            ignore_column=["extra_info"],
            const_column=[["status", 1], ["category", "test_cat"]]
        )
    
    conn = await asyncpg.connect(config_postgres_url)
    row = await conn.fetchrow(f"SELECT * FROM {TEST_TABLE} WHERE id=1")
    assert row["name"] == "Alice"
    assert row["status"] == 1
    assert row["category"] == "test_cat"
    await conn.close()

@pytest.mark.asyncio
async def test_ingest_update_with_rename(setup_ingest_table):
    """Test UPDATE using a renamed ID column."""
    if setup_ingest_table["is_mock"]: pytest.skip("DB unreachable")

    update_csv = "tmp/test_update_rename.csv"
    with open(update_csv, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["external_id", "name"])
        writer.writerow(["1", "Alice Renamed"])
    
    with patch('builtins.input', return_value='y'):
        await func_postgres_csv_ingestion(
            csv_path=update_csv,
            pg_dsn=config_postgres_url,
            table=TEST_TABLE,
            crud_mode="update",
            validation_mode="strict",
            rename_column=[["external_id", "id"]],
            ignore_column=None,
            const_column=None
        )
    
    conn = await asyncpg.connect(config_postgres_url)
    name = await conn.fetchval(f"SELECT name FROM {TEST_TABLE} WHERE id=1")
    assert name == "Alice Renamed"
    await conn.close()
    os.remove(update_csv)

@pytest.mark.asyncio
async def test_ingest_delete_permutation(setup_ingest_table):
    """Test DELETE with renamed ID."""
    if setup_ingest_table["is_mock"]: pytest.skip("DB unreachable")

    delete_csv = "tmp/test_delete_rename.csv"
    with open(delete_csv, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["old_id"])
        writer.writerow(["2"]) # Delete Bob
    
    with patch('builtins.input', return_value='y'):
        await func_postgres_csv_ingestion(
            csv_path=delete_csv,
            pg_dsn=config_postgres_url,
            table=TEST_TABLE,
            crud_mode="delete",
            validation_mode="strict",
            rename_column=[["old_id", "id"]],
            ignore_column=None,
            const_column=None
        )
    
    conn = await asyncpg.connect(config_postgres_url)
    count = await conn.fetchval(f"SELECT COUNT(*) FROM {TEST_TABLE}")
    assert count == 1
    await conn.close()
    os.remove(delete_csv)

@pytest.mark.asyncio
async def test_ingest_strict_validation_failure(setup_ingest_table):
    """Verify STRICT mode fails on bad data."""
    if setup_ingest_table["is_mock"]: pytest.skip("DB unreachable")

    bad_csv = "tmp/test_bad_data.csv"
    with open(bad_csv, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["id", "age"])
        writer.writerow(["100", "not_a_number"])
    
    with patch('builtins.input', return_value='y'):
        with pytest.raises(ValueError, match="Column 'age' error"):
            await func_postgres_csv_ingestion(
                csv_path=bad_csv,
                pg_dsn=config_postgres_url,
                table=TEST_TABLE,
                crud_mode="create",
                validation_mode="strict",
                rename_column=None,
                ignore_column=None,
                const_column=None
            )
    os.remove(bad_csv)

@pytest.mark.asyncio
async def test_ingest_reject_validation(setup_ingest_table):
    """Verify REJECT mode skips bad rows and logs them."""
    if setup_ingest_table["is_mock"]: pytest.skip("DB unreachable")

    mixed_csv = "tmp/test_mixed_data.csv"
    with open(mixed_csv, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["id", "age"])
        writer.writerow(["101", "25"]) # Good
        writer.writerow(["102", "bad"]) # Bad
    
    with patch('builtins.input', return_value='y'):
        await func_postgres_csv_ingestion(
            csv_path=mixed_csv,
            pg_dsn=config_postgres_url,
            table=TEST_TABLE,
            crud_mode="create",
            validation_mode="reject",
            rename_column=None,
            ignore_column=None,
            const_column=None
        )
    
    conn = await asyncpg.connect(config_postgres_url)
    exists = await conn.fetchval(f"SELECT COUNT(*) FROM {TEST_TABLE} WHERE id=101")
    not_exists = await conn.fetchval(f"SELECT COUNT(*) FROM {TEST_TABLE} WHERE id=102")
    assert exists == 1
    assert not_exists == 0
    await conn.close()
    os.remove(mixed_csv)

@pytest.mark.asyncio
async def test_ingest_delete_constraints(setup_ingest_table):
    """Verify 'delete' mode constraints (const_column must be None)."""
    if setup_ingest_table["is_mock"]: pytest.skip("DB unreachable")

    with pytest.raises(ValueError, match="'const_column' must be None for 'delete' mode"):
        await func_postgres_csv_ingestion(
            csv_path=TEST_CSV,
            pg_dsn=config_postgres_url,
            table=TEST_TABLE,
            crud_mode="delete",
            validation_mode="strict",
            rename_column=None,
            ignore_column=None,
            const_column=[["status", 1]]
        )

@pytest.mark.asyncio
async def test_ingest_update_id_constraint(setup_ingest_table):
    """Verify 'update' mode fails if ID is ignored."""
    if setup_ingest_table["is_mock"]: pytest.skip("DB unreachable")

    with pytest.raises(ValueError, match="Cannot ignore 'id' column in 'update' mode"):
        await func_postgres_csv_ingestion(
            csv_path=TEST_CSV,
            pg_dsn=config_postgres_url,
            table=TEST_TABLE,
            crud_mode="update",
            validation_mode="strict",
            rename_column=None,
            ignore_column=["id"],
            const_column=None
        )
