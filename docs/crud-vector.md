# Vector search

Find rows by meaning ("tickets like this one", "candidates for this job") with [pgvector](https://github.com/pgvector/pgvector): store an embedding per row, then read the nearest rows first. Part of [crud](crud.md).

Atom stores and searches vectors. Your code or worker makes them, with an AI model such as Gemini or OpenAI (`config_gemini_key`, `config_openai_key`).

## 1. The extension

`vector` is in Atom's `config_postgres_schema_master` `extension` list, so startup installs it where it can. Every extension is optional: one this server lacks, or this user may not install (Azure: allow it in the server's `azure.extensions` first), prints a warning and startup goes on. Nothing uses it until a table has a vector column.

## 2. Add a vector column

```python
# config_extend.py, in the table's columns
{"name": "embedding", "datatype": "vector(768)", "index": "hnsw(embedding)"},
```

- The size is the model's output (Gemini `gemini-embedding-001` with `output_dimensionality=768`, OpenAI `text-embedding-3-small`: 1536).
- `hnsw` is the index for nearest rows (cosine distance); a vector column takes no other index.
- If the extension is missing, startup stops naming the column.

## 3. Fill it

Write a list of numbers like any value (`/my/object-create`, `/admin/object-update`, `func_postgres_update`). Rows still to fill: `filter=["embedding is null"]`.

```python
vector = client_gemini.models.embed_content(model="gemini-embedding-001", contents=ticket["title"], config={"output_dimensionality": 768}).embeddings[0].values
await func_postgres_update(..., table="ticket", obj_list=[{"id": ticket["id"], "embedding": vector}], ...)
```

## 4. Nearest rows

Any read route (`/my/object-read`, `/permission/object-read`, `/public/object-read`, `/admin/object-read`):

```
GET /permission/object-read?table=ticket&filter=["embedding <=> [0.12,-0.4,...]"]&order=embedding&limit=5
```

- The filter takes the vector to compare with and keeps the rows that have one; `order=embedding` puts the closest first, paged after a cursor like any order. It needs the filter.
- Other filters work alongside it (`["embedding <=> [...]", "status = 1"]`).

## Rules

- A vector column is left out of `column=*` and exports; name it in `column` to get it back, as a list of numbers.
- A vector must be a list of numbers of the column's size; anything else is a 400.
