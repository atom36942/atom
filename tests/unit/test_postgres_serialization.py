from core.app import app
import sys
from datetime import date, datetime, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))



class FakeAcquire:
    def __init__(self, conn):
        self.conn = conn

    async def __aenter__(self):
        return self.conn

    async def __aexit__(self, exc_type, exc, tb):
        return False


class FakePool:
    def __init__(self, rows):
        self.rows = rows

    def acquire(self):
        return FakeAcquire(self)

    async def fetch(self, sql):
        return self.rows


class FakePasswordHasher:
    def hash(self, value):
        return f"hashed:{value}"


def schema_for(types):
    return {"test": {name: {"datatype": datatype} for name, datatype in types.items()}}


@pytest.mark.parametrize(
    ("datatype", "raw", "expected"),
    [
        ("smallint", "1", 1),
        ("integer", "42", 42),
        ("bigint", "9007199254740991", 9007199254740991),
        ("bigserial", "7", 7),
        ("numeric(10,2)", "12.34", 12.34),
        ("real", "1.5", 1.5),
        ("double precision", "2.75", 2.75),
        ("boolean", "TRUE", True),
        ("boolean", "yes", True),
        ("boolean", "FaLsE", False),
        ("boolean", "off", False),
        ("text", "hello", "hello"),
        ("character varying", "hello", "hello"),
        ("character", "x", "x"),
        ("geography(Point, 4326)", "POINT(80 15)", "POINT(80 15)"),
    ],
)
async def test_postgres_serialize_casts_scalar_datatypes(datatype, raw, expected):
    serialized = await app.state.func_postgres_serialize(
        client_postgres_pool=None,
        client_password_hasher=None,
        cache_postgres_schema=schema_for({"value": datatype}),
        table="test",
        obj_list=[{"value": raw}],
        is_base=1,
    )

    assert serialized == [{"value": expected}]


@pytest.mark.parametrize("datatype", ["date", "timestamp", "timestamptz", "timestamp with time zone"])
async def test_postgres_serialize_casts_temporal_datatypes(datatype):
    raw = "2026-05-06T12:34:56+00:00" if "timestamp" in datatype or "timestamptz" in datatype else "2026-05-06"
    serialized = await app.state.func_postgres_serialize(
        client_postgres_pool=None,
        client_password_hasher=None,
        cache_postgres_schema=schema_for({"value": datatype}),
        table="test",
        obj_list=[{"value": raw}],
        is_base=1,
    )

    expected = datetime(2026, 5, 6, 12, 34, 56, tzinfo=timezone.utc) if "timestamp" in datatype or "timestamptz" in datatype else date(2026, 5, 6)
    assert serialized == [{"value": expected}]


@pytest.mark.parametrize(
    ("datatype", "raw", "expected"),
    [
        ("text[]", "{java,python}", ["java", "python"]),
        ("integer[]", "{9,14}", [9, 14]),
        ("bigint[]", "{9007199254740991,2}", [9007199254740991, 2]),
        ("numeric[]", "{1.5,2.75}", [1.5, 2.75]),
        ("double precision[]", "{1.5,2.75}", [1.5, 2.75]),
        ("boolean[]", "{true,off,1}", [True, False, True]),
        ("date[]", "{2026-05-06,2026-05-07}", [date(2026, 5, 6), date(2026, 5, 7)]),
        ("timestamp[]", "{2026-05-06T12:34:56+00:00}", [datetime(2026, 5, 6, 12, 34, 56, tzinfo=timezone.utc)]),
        ("integer[]", ["9", "14"], [9, 14]),
        ("integer[]", "{9,null,}", [9, None, None]),
        ("boolean[]", "{TRUE,FaLsE,y,n}", [True, False, True, False]),
    ],
)
async def test_postgres_serialize_casts_array_datatypes(datatype, raw, expected):
    serialized = await app.state.func_postgres_serialize(
        client_postgres_pool=None,
        client_password_hasher=None,
        cache_postgres_schema=schema_for({"value": datatype}),
        table="test",
        obj_list=[{"value": raw}],
        is_base=1,
    )

    assert serialized == [{"value": expected}]


@pytest.mark.parametrize("raw", ["abc", "protected", "enabled"])
async def test_postgres_serialize_rejects_invalid_boolean_strings(raw):
    with pytest.raises(ValueError, match="invalid boolean value"):
        await app.state.func_postgres_serialize(
            client_postgres_pool=None,
            client_password_hasher=None,
            cache_postgres_schema=schema_for({"value": "boolean"}),
            table="test",
            obj_list=[{"value": raw}],
            is_base=1,
        )


async def test_postgres_serialize_rejects_invalid_boolean_array_values():
    with pytest.raises(ValueError, match="invalid boolean value"):
        await app.state.func_postgres_serialize(
            client_postgres_pool=None,
            client_password_hasher=None,
            cache_postgres_schema=schema_for({"value": "boolean[]"}),
            table="test",
            obj_list=[{"value": "{true,abc}"}],
            is_base=1,
        )


@pytest.mark.parametrize(
    ("alias", "raw", "expected"),
    [
        ("_int2", "{1,2}", [1, 2]),
        ("_int4", "{9,14}", [9, 14]),
        ("_int8", "{9007199254740991,2}", [9007199254740991, 2]),
        ("_float4", "{1.5,2.75}", [1.5, 2.75]),
        ("_float8", "{1.5,2.75}", [1.5, 2.75]),
        ("_numeric", "{1.5,2.75}", [1.5, 2.75]),
        ("_bool", "{true,off}", [True, False]),
        ("_text", "{java,python}", ["java", "python"]),
        ("_varchar", "{java,python}", ["java", "python"]),
        ("_bpchar", "{a,b}", ["a", "b"]),
        ("_date", "{2026-05-06}", [date(2026, 5, 6)]),
        ("_timestamp", "{2026-05-06T12:34:56+00:00}", [datetime(2026, 5, 6, 12, 34, 56, tzinfo=timezone.utc)]),
        ("_timestamptz", "{2026-05-06T12:34:56+00:00}", [datetime(2026, 5, 6, 12, 34, 56, tzinfo=timezone.utc)]),
    ],
)
async def test_postgres_serialize_casts_postgres_array_alias_datatypes(alias, raw, expected):
    serialized = await app.state.func_postgres_serialize(
        client_postgres_pool=None,
        client_password_hasher=None,
        cache_postgres_schema=schema_for({"value": alias}),
        table="test",
        obj_list=[{"value": raw}],
        is_base=1,
    )

    assert serialized == [{"value": expected}]


async def test_postgres_serialize_handles_json_modes_bytea_unknowns_and_passwords():
    base_serialized = await app.state.func_postgres_serialize(
        client_postgres_pool=None,
        client_password_hasher=FakePasswordHasher(),
        cache_postgres_schema={
            "test": {
                "metadata": {"datatype": "jsonb"},
                "payload": {"datatype": "bytea"},
                "empty_int": {"datatype": "integer"},
            },
            "users": {"password": {"datatype": "text"}},
        },
        table="test",
        obj_list=[{"id": "5", "metadata": {"role": "admin"}, "payload": "abc", "empty_int": ""}],
        is_base=1,
    )
    with pytest.raises(Exception, match="column 'ignored' does not exist in table 'test'"):
        await app.state.func_postgres_serialize(
            client_postgres_pool=None,
            client_password_hasher=FakePasswordHasher(),
            cache_postgres_schema={
                "test": {
                    "metadata": {"datatype": "jsonb"},
                    "payload": {"datatype": "bytea"},
                    "empty_int": {"datatype": "integer"},
                },
            },
            table="test",
            obj_list=[{"ignored": "drop"}],
            is_base=1,
        )
    expanded_serialized = await app.state.func_postgres_serialize(
        client_postgres_pool=None,
        client_password_hasher=None,
        cache_postgres_schema={"test": {"metadata": {"datatype": "jsonb"}, "payload": {"datatype": "bytea"}}},
        table="test",
        obj_list=[{"metadata": "{\"role\":\"admin\"}", "payload": "abc"}],
        is_base=0,
    )
    password_serialized = await app.state.func_postgres_serialize(
        client_postgres_pool=None,
        client_password_hasher=FakePasswordHasher(),
        cache_postgres_schema={"users": {"password": {"datatype": "text"}}},
        table="users",
        obj_list=[{"password": "secret"}],
        is_base=1,
    )
    passthrough = await app.state.func_postgres_serialize(
        client_postgres_pool=None,
        client_password_hasher=None,
        cache_postgres_schema={},
        table="missing",
        obj_list=[{"value": "1"}],
        is_base=1,
    )

    assert base_serialized == [{"id": "5", "metadata": "{\"role\":\"admin\"}", "payload": "abc", "empty_int": None}]
    assert expanded_serialized == [{"metadata": {"role": "admin"}, "payload": b"abc"}]
    assert password_serialized == [{"password": "hashed:secret"}]
    assert passthrough == [{"value": "1"}]


async def test_postgres_schema_read_preserves_array_element_datatype():
    schema = await app.state.func_postgres_schema_read(
        client_postgres_pool=FakePool(
            [
                {
                    "table_name": "test",
                    "column_name": "tag_int",
                    "data_type": "integer[]",
                    "is_nullable": "YES",
                    "column_default": None,
                }
            ]
        )
    )

    assert schema["test"]["tag_int"]["datatype"] == "integer[]"


async def test_postgres_schema_read_maps_user_defined_datatype_to_udt_name():
    schema = await app.state.func_postgres_schema_read(
        client_postgres_pool=FakePool(
            [
                {
                    "table_name": "test",
                    "column_name": "coordinate",
                    "data_type": "geography",
                    "is_nullable": "YES",
                    "column_default": None,
                }
            ]
        )
    )

    assert schema["test"]["coordinate"]["datatype"] == "geography"


async def test_postgres_serialize_casts_integer_arrays_from_csv_values():
    serialized = await app.state.func_postgres_serialize(
        client_postgres_pool=None,
        client_password_hasher=None,
        cache_postgres_schema={"test": {"tag_int": {"datatype": "integer[]"}}},
        table="test",
        obj_list=[{"tag_int": "{9,14}"}],
        is_base=1,
    )

    assert serialized == [{"tag_int": [9, 14]}]


async def test_postgres_serialize_casts_postgres_array_aliases():
    serialized = await app.state.func_postgres_serialize(
        client_postgres_pool=None,
        client_password_hasher=None,
        cache_postgres_schema={"test": {"tag_int": {"datatype": "_int4"}}},
        table="test",
        obj_list=[{"tag_int": "{9,14}"}],
        is_base=1,
    )

    assert serialized == [{"tag_int": [9, 14]}]
