"""Filter mini-language and relation-string contracts with a mocked database."""
import unittest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
from function import func_postgres_relation, func_postgres_serialize, func_postgres_where_build


class FilterLanguageTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        columns = [("id", "bigint"), ("name", "text"), ("rating", "numeric"), ("tags", "text[]"), ("nums", "integer[]"),
                   ("meta", "jsonb"), ("is_on", "boolean"), ("created_at", "timestamp with time zone"),
                   ("created_by_id", "bigint"), ("password", "text"), ("coordinate", "geography")]
        self.common = dict(client_postgres=None, client_password_hasher=None, func_postgres_serialize=func_postgres_serialize,
                           cache_postgres_schema={"t": {name: {"datatype": dtype} for name, dtype in columns}}, table="t")

    async def where(self, *filters):
        return await func_postgres_where_build(**self.common, filter=list(filters))

    async def test_comparison_operators_and_aliases_bind_typed_values(self):
        for item, sql, values in [
            ("id = 5", '"id" = $1', [5]), ("id == 5", '"id" = $1', [5]), ("id != 5", '"id" != $1', [5]),
            ("id <> 5", '"id" != $1', [5]), ("id >= 5", '"id" >= $1', [5]), ("id gte 5", '"id" >= $1', [5]),
            ("rating < 2.5", '"rating" < $1', [2.5]), ("is_on = true", '"is_on" = $1', [True]),
            ('"name" = x', '"name" = $1', ["x"]),
            ("created_at > 2026-01-01T00:00:00Z", '"created_at" > $1', [datetime(2026, 1, 1, tzinfo=timezone.utc)]),
        ]:
            with self.subTest(item=item):
                self.assertEqual(await self.where(item), ("WHERE " + sql, values))

    async def test_list_and_range_operators_bind_one_placeholder_per_value(self):
        for item, sql, values in [
            ("id in 1,2,3", '"id" IN ($1,$2,$3)', [1, 2, 3]), ("id in (1,2,3)", '"id" IN ($1,$2,$3)', [1, 2, 3]),
            ("id not in 1,2", '"id" NOT IN ($1,$2)', [1, 2]), ("id between 1 AND 9", '"id" BETWEEN $1 AND $2', [1, 9]),
        ]:
            with self.subTest(item=item):
                self.assertEqual(await self.where(item), ("WHERE " + sql, values))

    async def test_null_checks_bind_nothing(self):
        self.assertEqual(await self.where("name is null"), ('WHERE "name" IS NULL', []))
        self.assertEqual(await self.where("name is not null"), ('WHERE "name" IS NOT NULL', []))

    async def test_type_specific_operators(self):
        for item, sql, values in [
            ("name like a%", '"name" LIKE $1', ["a%"]), ("name ilike %Atl%", '"name" ILIKE $1', ["%Atl%"]),
            ("name ~ ^a", '"name" ~ $1', ["^a"]), ("tags contains api,db", '"tags" @> $1', [["api", "db"]]),
            ("tags overlap api,db", '"tags" && $1', [["api", "db"]]), ("nums any 4", '$1 = ANY("nums")', [4]),
            ("meta contains k|v", '"meta" @> $1::jsonb', ['{"k":"v"}']), ("meta contains k|3|int", '"meta" @> $1::jsonb', ['{"k":3}']),
            ('meta contains {"a":1}', '"meta" @> $1::jsonb', ['{"a":1}']), ("meta exists k", '"meta" ? $1', ["k"]),
            ("coordinate point 77.1|28.6|0|500", 'ST_Distance("coordinate", ST_Point($1, $2)::geography) BETWEEN $3 AND $4', [77.1, 28.6, 0.0, 500.0]),
        ]:
            with self.subTest(item=item):
                self.assertEqual(await self.where(item), ("WHERE " + sql, values))

    async def test_operators_are_restricted_by_column_type(self):
        for item in ("id ilike 5", "id like 5", "rating contains 1", "name overlap a,b", "id exists k"):
            with self.subTest(item=item), self.assertRaisesRegex(Exception, "invalid operator"):
                await self.where(item)

    async def test_values_must_match_the_column_type(self):
        for item in ("id = abc", "is_on = maybe", "rating > high"):
            with self.subTest(item=item), self.assertRaises(ValueError):
                await self.where(item)

    async def test_combinations_number_placeholders_in_order(self):
        for filters, sql, values in [
            (["id = 1", "name = x"], 'WHERE "id" = $1 AND "name" = $2', [1, "x"]),
            (["id > 1", "id < 9"], 'WHERE ("id" > $1  AND  "id" < $2)', [1, 9]),
            (["id = 1 OR id = 2"], 'WHERE ("id" = $1  OR  "id" = $2)', [1, 2]),
            ([{"_or": [{"id": "eq,1"}, {"name": "eq,x"}]}], 'WHERE ("id" = $1  OR  "name" = $2)', [1, "x"]),
            ([{"_and": [{"id": "gt,1"}, {"_or": [{"name": "eq,a"}, {"name": "eq,b"}]}]}],
             'WHERE ("id" > $1  AND  ("name" = $2  OR  "name" = $3))', [1, "a", "b"]),
        ]:
            with self.subTest(filters=filters):
                self.assertEqual(await self.where(*filters), (sql, values))

    async def test_user_filters_cannot_widen_an_appended_ownership_predicate(self):
        owner = "created_by_id = 42"
        for user_filter in (["created_by_id = 99"], [{"created_by_id": "eq,99"}], ["created_by_id = 99 OR id > 0"],
                            [{"_or": [{"created_by_id": "eq,99"}, {"id": "gt,0"}]}], [{"_and": [{"id": "gt,0"}]}],
                            ["created_by_id is not null"]):
            with self.subTest(user_filter=user_filter):
                sql, values = await self.where(*user_filter, owner)
                self.assertEqual(values[-1], 42)
                self.assertRegex(sql, rf'AND\s+"created_by_id" = \${len(values)}\)?$')

    async def test_malformed_filters_raise(self):
        for filters, message in [([{"id": "5"}], "Expected 'operator,value'"), ([{"_or": {"id": "eq,1"}}], "must be a list"),
                                 (["nope = 1"], "invalid filter column"), (["password = x"], "blocked")]:
            with self.subTest(filters=filters), self.assertRaisesRegex(Exception, message):
                await self.where(*filters)


class RelationStringTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.client = MagicMock()
        self.client.fetch = AsyncMock(return_value=[])
        self.rows = [{"id": 1, "owner_id": 7}, {"id": 2, "owner_id": None}, {"id": 3, "owner_id": 7}]

    async def relate(self, relation, rows=None, limit_max=10):
        return await func_postgres_relation(client_postgres=self.client, obj_list=rows or self.rows, relation=[relation],
                                            config_sql_read_relation_fetch_limit_max=limit_max)

    async def test_count_batches_ids_and_defaults_missing_to_zero(self):
        self.client.fetch.return_value = [{"id": 1, "value": 4}]
        result = await self.relate("id,comment,task_id,count,*")
        sql, ids = self.client.fetch.await_args.args
        self.assertEqual(sql, 'SELECT "task_id" AS id, count(*) AS value FROM "comment" WHERE "task_id" = ANY($1) GROUP BY "task_id";')
        self.assertEqual(sorted(ids), [1, 2, 3])
        self.assertEqual([r["comment_count"] for r in result], [4, 0, 0])

    async def test_other_aggregates_default_missing_to_none(self):
        self.client.fetch.return_value = [{"id": 1, "value": 9}]
        result = await self.relate("id,comment,task_id,sum,score")
        self.assertIn('sum("score")', self.client.fetch.await_args.args[0])
        self.assertEqual([r["comment_sum"] for r in result], [9, None, None])

    async def test_fetch_attaches_bounded_child_lists(self):
        self.client.fetch.return_value = [{"id": 10, "body": "a", "relation_id": 1, "rn": 1}, {"id": 11, "body": "b", "relation_id": 1, "rn": 2}]
        result = await self.relate("id,comment,task_id,fetch|2,id,body")
        sql, ids, limit = self.client.fetch.await_args.args
        self.assertIn("ROW_NUMBER() OVER(PARTITION BY \"task_id\"", sql)
        self.assertEqual((sorted(ids), limit), ([1, 2, 3], 2))
        self.assertEqual([r["comment"] for r in result], [[{"id": 10, "body": "a"}, {"id": 11, "body": "b"}], [], []])

    async def test_fetch_on_target_id_attaches_one_object_and_skips_null_sources(self):
        self.client.fetch.return_value = [{"id": 7, "username": "u", "relation_id": 7, "rn": 1}]
        result = await self.relate("owner_id,users,id,fetch|1,id,username")
        self.assertEqual(self.client.fetch.await_args.args[1], [7])
        self.assertEqual([r["users"] for r in result], [{"id": 7, "username": "u"}, None, {"id": 7, "username": "u"}])

    async def test_fetch_strips_blocked_columns_from_child_rows(self):
        self.client.fetch.return_value = [{"id": 10, "password": "secret", "relation_id": 1, "rn": 1}]
        result = await self.relate("id,comment,task_id,fetch|2,*")
        self.assertEqual(result[0]["comment"], [{"id": 10}])

    async def test_no_source_ids_means_no_query(self):
        result = await self.relate("id,comment,task_id,count,*", rows=[{"id": None}])
        self.assertEqual(result, [{"id": None}])
        self.client.fetch.assert_not_awaited()

    async def test_malformed_relations_raise_before_querying(self):
        for relation, message in [
            ("id,comment,task_id,count", "5 parts"), ("id,comment,task_id,fetch,*", "explicit limit required"),
            ("id,comment,task_id,fetch|99,*", "exceeds maximum"), ("id,comment,task_id,drop,*", "invalid operator"),
            ("id,comment;drop,task_id,count,*", "invalid identifier"), ("missing,comment,task_id,count,*", "source column missing"),
            ("id,comment,task_id,fetch|2,body;x", "invalid value"), ("id,comment,task_id,sum,password", "restricted column"),
        ]:
            with self.subTest(relation=relation), self.assertRaisesRegex(Exception, message):
                await self.relate(relation)
        self.client.fetch.assert_not_awaited()


if __name__ == "__main__":
    unittest.main()
