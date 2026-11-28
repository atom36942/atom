# Full-text search

Search words in a table's text the way people search: words in any order, word forms ("working" finds "works"), phrases, excluded words, and the best matches first. Built into Postgres, so no extra service. Part of [crud](crud.md).

| Tool | Use for |
|---|---|
| `title ilike %ann%` with a `gin_trgm` index | Parts of a word, names, codes, emails |
| `search @@ <words>` (this page) | Words in titles, descriptions, comments |

## 1. Add a search column

One generated column per table, from the text columns it covers, with a GIN index. Postgres fills it on every insert and update; nobody writes it.

```python
# config_extend.py, in the table's columns
{"name": "search", "datatype": "tsvector", "generated": "setweight(to_tsvector('english', coalesce(title, '')), 'A') || setweight(to_tsvector('english', coalesce(description, '')), 'B')", "index": ["gin(search)"]},
```

- **Weights** `A` to `D`: a match in `A` (the title) ranks above one in `B` (the description).
- **Language**: `english` knows word forms; `simple` matches exact words (names, codes, other languages such as Hindi). Searches read the column's own language, so they always match.

## 2. Search

Any read route (`/my/object-read`, `/private/object-read`, `/public/object-read`, `/admin/object-read` and their exports) takes the filter, with the words as a search box would:

| You type | Finds |
|---|---|
| `printer working` | Both words, any order, any form |
| `"printer stopped"` | The phrase |
| `printer -toner` | printer, without toner |
| `scanner or printer` | Either |

```
GET /admin/object-read?table=task&filter=["search @@ printer working -toner"]&order=search desc
```

- `order=search desc`: best match first (`ts_rank`), paged after a cursor like any order; it needs the `search @@` filter.
- Other filters and orders work alongside it (`["search @@ printer", "status = 1"]`, `order=id desc`).

## Rules

- The search column is never returned or exported; naming it in `column` is a 400, and it takes only `@@`.
- Change the `generated` expression and the next start rebuilds the column (it holds no data of its own), which computes it for every row once. A plain column with data never becomes generated: rename or drop it first.
- Space: about 20–40% of the text it covers, plus its index.
