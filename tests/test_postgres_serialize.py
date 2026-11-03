"""func_postgres_serialize: each column type converts values the same way (the converters are built once per call, so a repeated column must still convert every value)."""
import unittest
from datetime import date
from datetime import datetime
from datetime import UTC
from unittest.mock import MagicMock

from function import func_postgres_serialize


async def serialize(datatype, value, is_base=True):
    rows = await func_postgres_serialize(client_postgres=None, client_password_hasher=None, cache_postgres_schema={"t": {"c": {"datatype": datatype}}}, table="t", obj_list=[{"c": value}], is_base=is_base)
    return rows[0]["c"]


class PostgresSerializeTests(unittest.IsolatedAsyncioTestCase):
    async def test_each_type_converts_as_before(self):
        cases = [
            ("bigint", " 3 ", 3), ("integer", 7, 7), ("smallint", "", None), ("bigint", "NULL", None), ("interval", "5", 5),
            ("numeric(3,1)", "7.5", 7.5), ("double precision", 2, 2.0), ("real", "null", None),
            ("boolean", "yes", True), ("boolean", "off", False), ("boolean", True, True), ("_bool", "{t,f}", [True, False]),
            ("text", 5, 5), ("character varying(50)", " plain ", " plain "), ("uuid", "", None),
            ("date", "2026-01-02", date(2026, 1, 2)), ("timestamp with time zone", "2026-01-02T03:04:05Z", datetime(2026, 1, 2, 3, 4, 5, tzinfo=UTC)),
            ("text[]", "{a,b}", ["a", "b"]), ("integer[]", [1, "2", "null"], [1, 2, None]), ("_int8", "{}", []), ("_timestamptz", "{2026-01-02}", [datetime(2026, 1, 2)]),
            ("jsonb", {"k": 1}, '{"k":1}'), ("json", '{"k": 1}', '{"k": 1}'), ("geography(Point,4326)", "POINT(1 2)", "POINT(1 2)"), ("bytea", "x", "x"),
        ]
        for datatype, value, expected in cases:
            with self.subTest(datatype=datatype, value=value):
                self.assertEqual(await serialize(datatype, value), expected)

    async def test_read_mode_parses_json_and_encodes_bytea(self):
        self.assertEqual(await serialize("jsonb", '{"k": 1}', is_base=False), {"k": 1})
        self.assertEqual(await serialize("jsonb", "plain", is_base=False), "plain")
        self.assertEqual(await serialize("bytea", "x", is_base=False), b"x")

    async def test_bad_values_raise_the_same_errors(self):
        for datatype, value, error in (("boolean", "maybe", "invalid boolean value: maybe"), ("integer", "x", "invalid literal for int"), ("date", "02/01/2026", "Invalid isoformat")):
            with self.subTest(datatype=datatype), self.assertRaisesRegex(ValueError, error):
                await serialize(datatype, value)

    async def test_every_row_is_converted_with_its_column_type(self):
        schema = {"t": {"n": {"datatype": "integer"}, "j": {"datatype": "jsonb"}}}
        rows = await func_postgres_serialize(client_postgres=None, client_password_hasher=None, cache_postgres_schema=schema, table="t", obj_list=[{"n": str(i), "j": {"i": i}, "id": "9"} for i in range(3)], is_base=True)
        self.assertEqual(rows, [{"n": i, "j": f'{{"i":{i}}}', "id": "9"} for i in range(3)])
        with self.assertRaisesRegex(Exception, "column 'x' does not exist in table 't'"):
            await func_postgres_serialize(client_postgres=None, client_password_hasher=None, cache_postgres_schema=schema, table="t", obj_list=[{"x": 1}], is_base=True)

    async def test_users_password_is_hashed(self):
        hasher = MagicMock()
        hasher.hash.return_value = "hashed"
        rows = await func_postgres_serialize(client_postgres=None, client_password_hasher=hasher, cache_postgres_schema={"users": {"password": {"datatype": "text"}}}, table="users", obj_list=[{"password": "secret"}], is_base=True)
        self.assertEqual(rows, [{"password": "hashed"}])


if __name__ == "__main__":
    unittest.main()
