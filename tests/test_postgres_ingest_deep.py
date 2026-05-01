import pytest
import asyncio
import os
from unittest.mock import MagicMock, AsyncMock, patch

# ---------------------------------------------------------------------------
# Postgres Ingest Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_func_postgres_csv_ingestion_create():
    from core.function.postgres_ingest import func_postgres_csv_ingestion
    
    # Create a temporary CSV
    csv_path = "tmp/test_ingest.csv"
    os.makedirs("tmp", exist_ok=True)
    with open(csv_path, "w") as f:
        f.write("id,name\n1,foo\n2,bar")
    
    mock_conn = AsyncMock()
    # Mock transaction context manager
    mock_conn.transaction = MagicMock()
    mock_conn.transaction.return_value.__aenter__ = AsyncMock()
    mock_conn.transaction.return_value.__aexit__ = AsyncMock()
    
    # Mocking asyncpg.connect
    with patch("asyncpg.connect", return_value=mock_conn):
        # Mock schema fetch
        mock_conn.fetchval.side_effect = [True, None] # table exists, staging doesn't
        mock_conn.fetch.return_value = [
            {"column_name": "id", "data_type": "bigint", "udt_name": "int8", "is_nullable": "NO", "column_default": None},
            {"column_name": "name", "data_type": "text", "udt_name": "text", "is_nullable": "YES", "column_default": None}
        ]
        
        # Mock input() to proceed
        with patch("builtins.input", return_value="y"):
            # Mock subprocess for wc -l
            with patch("subprocess.check_output", return_value=b"3 test_ingest.csv"):
                await func_postgres_csv_ingestion(
                    csv_path=csv_path,
                    pg_dsn="postgresql://user:pass@localhost/db",
                    table="test_table",
                    crud_mode="create",
                    validation_mode="strict",
                    rename_column=None,
                    ignore_column=None,
                    const_column=None
                )
    
    # Verify it tried to copy records
    mock_conn.copy_records_to_table.assert_called_once()
    if os.path.exists(csv_path): os.remove(csv_path)

@pytest.mark.asyncio
async def test_func_postgres_csv_ingestion_cancel():
    from core.function.postgres_ingest import func_postgres_csv_ingestion
    csv_path = "tmp/test_cancel.csv"
    os.makedirs("tmp", exist_ok=True)
    with open(csv_path, "w") as f: f.write("id\n1")
    
    mock_conn = AsyncMock()
    with patch("asyncpg.connect", return_value=mock_conn):
        mock_conn.fetchval.return_value = True
        mock_conn.fetch.return_value = [{"column_name": "id", "data_type": "int", "udt_name": "int4", "is_nullable": "NO", "column_default": None}]
        
        # Mock input() to cancel
        with patch("builtins.input", return_value="n"):
            await func_postgres_csv_ingestion(
                csv_path=csv_path, pg_dsn="dsn", table="t", crud_mode="create", 
                validation_mode="strict", rename_column=None, ignore_column=None, const_column=None
            )
    
    # Should not have copied anything
    mock_conn.copy_records_to_table.assert_not_called()
    if os.path.exists(csv_path): os.remove(csv_path)
