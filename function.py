async def function_extend_client():
   output={}
   return output

import sys
def function_check_required_env(config, required_keys):
    missing = [key for key in required_keys if not config.get(key)]
    if missing:
        print(f"Error: Missing required environment variables: {', '.join(missing)}", file=sys.stderr)
        sys.exit(1)
    return None

import os
def function_delete_files(folder_path=".", extension_list=None, file_prefix_list=None):
    if extension_list is None:
        extension_list = []
    if file_prefix_list is None:
        file_prefix_list = []
    skip_dirs = ('venv', 'env', '__pycache__', 'node_modules')
    for root, dirs, files in os.walk(folder_path):
        dirs[:] = [d for d in dirs if not (d.startswith('.') or d.lower() in skip_dirs)]
        for filename in files:
            if any(filename.endswith(ext) for ext in extension_list) or any(filename.startswith(prefix) for prefix in file_prefix_list):
                file_path = os.path.join(root, filename)
                os.remove(file_path)
    return None

import os
def function_export_directory_filename(dir_path=".",output_path="export_filename.txt"):
    skip_dirs = {"venv", "__pycache__", ".git", ".mypy_cache", ".pytest_cache", "node_modules"}
    dir_path = os.path.abspath(dir_path)
    with open(output_path, "w") as out_file:
        for root, dirs, files in os.walk(dir_path):
            dirs[:] = [d for d in dirs if d not in skip_dirs]
            for file in files:
                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, dir_path)
                out_file.write(rel_path + "\n")
    print(f"Saved to: {output_path}")
    return None

import sys
def function_variable_size_kb_read(namespace):
   result = {}
   for name, var in namespace.items():
      if not name.startswith("__"):
         key = f"{name} ({type(var).__name__})"
         size_kb = sys.getsizeof(var) / 1024
         result[key] = size_kb
   sorted_result = dict(sorted(result.items(), key=lambda item: item[1], reverse=True))
   return sorted_result

import os
from dotenv import load_dotenv, dotenv_values
import importlib.util
from pathlib import Path
import traceback
def function_config_read():
    base_dir = Path(__file__).resolve().parent
    def read_env_file():
        env_path = base_dir / ".env"
        if env_path.exists():
            load_dotenv(env_path)
            return {k.lower(): v for k, v in dotenv_values(env_path).items()}
        return {}
    def read_root_config_py_files():
        output = {}
        for file in os.listdir(base_dir):
            if file.startswith("config") and file.endswith(".py"):
                module_path = base_dir / file
                try:
                    module_name = os.path.splitext(file)[0]
                    spec = importlib.util.spec_from_file_location(module_name, module_path)
                    if spec and spec.loader:
                        module = importlib.util.module_from_spec(spec)
                        spec.loader.exec_module(module)
                        output.update({
                            k.lower(): getattr(module, k)
                            for k in dir(module) if not k.startswith("__")
                        })
                except Exception:
                    print(f"[WARN] Failed to load root config file: {module_path}")
                    traceback.print_exc()
        return output
    def read_config_folder_files():
        output = {}
        config_dir = base_dir / "config"
        if not config_dir.exists() or not config_dir.is_dir():
            return output
        for file in os.listdir(config_dir):
            if file.endswith(".py"):
                module_path = config_dir / file
                try:
                    rel_path = os.path.relpath(module_path, base_dir)
                    module_name = os.path.splitext(rel_path)[0].replace(os.sep, ".")
                    if not module_name.strip():
                        continue
                    spec = importlib.util.spec_from_file_location(module_name, module_path)
                    if spec and spec.loader:
                        module = importlib.util.module_from_spec(spec)
                        spec.loader.exec_module(module)
                        output.update({
                            k.lower(): getattr(module, k)
                            for k in dir(module) if not k.startswith("__")
                        })
                except Exception:
                    print(f"[WARN] Failed to load config folder file: {module_path}")
                    traceback.print_exc()
        return output
    output = {}
    output.update(read_env_file())
    output.update(read_root_config_py_files())
    output.update(read_config_folder_files())
    return output

async def function_postgres_drop_all_index(client_postgres_pool):
    query = """
    DO $$
    DECLARE r RECORD;
    BEGIN
        FOR r IN (SELECT indexname FROM pg_indexes WHERE schemaname = 'public' 
                  AND indexname LIKE 'index_%')
        LOOP
            EXECUTE 'DROP INDEX IF EXISTS public.' || quote_ident(r.indexname);
        END LOOP;
    END
    $$;
    """
    async with client_postgres_pool.acquire() as conn:
        await conn.execute(query)
    return None

async def function_postgres_query_runner(client_postgres_pool,mode,query):
    block_word = ["drop", "truncate"]
    for item in block_word:
        if item in query.lower():
            raise Exception(f"{item} keyword not allowed in query")
    async with client_postgres_pool.acquire() as conn:
        if mode == "read":
            return await conn.fetch(query)
        if mode == "write":
            if "returning" in query.lower():
                return await conn.fetch(query)
            else:
                return await conn.execute(query)
    return None

async def function_postgres_column_mapping_read(client_postgres_pool,table,column_1,column_2,limit,is_null,transformer):
   output={}
   where_clause="" if is_null else f"WHERE {column_2} IS NOT NULL"
   async with client_postgres_pool.acquire() as conn:
      stmt=await conn.prepare(f"SELECT {column_1},{column_2} FROM {table} {where_clause} ORDER BY {column_1} DESC")
      cursor=stmt.cursor()
      count=0
      while count<limit:
         batch=await cursor.fetch(10000)
         if not batch:break
         if transformer=="split_int":output.update({row[column_1]:[int(item.strip()) for item in row[column_2].split(",")] if row[column_2] else [] for row in batch})
         else:output.update({row[column_1]:row[column_2] for row in batch})
         count+=len(batch)
         if count>=limit:break
   return output

import datetime
async def function_postgres_clean(client_postgres_pool,config_postgres_clean):
   async with client_postgres_pool.acquire() as conn:
      for table_name,days in config_postgres_clean.items():
         threshold_date=datetime.datetime.utcnow()-datetime.timedelta(days=days)
         query=f"DELETE FROM {table_name} WHERE created_at < $1"
         await conn.execute(query,threshold_date)
   return None

import asyncpg
async def function_postgres_client_pool_read(config_postgres_url,config_postgres_min_connection=5,config_postgres_max_connection=20):
   client_postgres_pool=await asyncpg.create_pool(dsn=config_postgres_url,min_size=config_postgres_min_connection,max_size=config_postgres_max_connection)
   return client_postgres_pool

async def function_postgres_schema_read(client_postgres_pool):
    query = """
    WITH t AS (
        SELECT * FROM information_schema.tables
        WHERE table_schema='public' AND table_type='BASE TABLE'
    ),
    c AS (
        SELECT table_name, column_name, data_type,
               CASE WHEN is_nullable='YES' THEN 1 ELSE 0 END AS is_nullable,
               column_default
        FROM information_schema.columns
        WHERE table_schema='public'
    ),
    i AS (
        SELECT t.relname::text AS table_name, a.attname AS column_name,
               CASE WHEN idx.indisprimary OR idx.indisunique OR idx.indisvalid THEN 1 ELSE 0 END AS is_index
        FROM pg_attribute a
        JOIN pg_class t ON a.attrelid=t.oid
        JOIN pg_namespace ns ON t.relnamespace=ns.oid
        LEFT JOIN pg_index idx ON a.attrelid=idx.indrelid AND a.attnum=ANY(idx.indkey)
        WHERE ns.nspname='public' AND a.attnum > 0 AND t.relkind='r'
    )
    SELECT t.table_name AS table,
           c.column_name AS column,
           c.data_type AS datatype,
           c.column_default AS default,
           c.is_nullable AS is_null,
           COALESCE(i.is_index, 0) AS is_index
    FROM t
    LEFT JOIN c ON t.table_name=c.table_name
    LEFT JOIN i ON t.table_name=i.table_name AND c.column_name=i.column_name;
    """
    async with client_postgres_pool.acquire() as conn:
        output = await conn.fetch(query)
    postgres_schema = {}
    postgres_column_datatype = {}
    for obj in output:
        table, column = obj["table"], obj["column"]
        column_data = {
            "datatype": obj["datatype"],
            "default": obj["default"],
            "is_null": obj["is_null"],
            "is_index": obj["is_index"]
        }
        if table not in postgres_schema:
            postgres_schema[table] = {}
        postgres_schema[table][column] = column_data
    postgres_column_datatype = {col: data["datatype"] for table, cols in postgres_schema.items() for col, data in cols.items()}
    return postgres_schema, postgres_column_datatype

import csv, re
from io import StringIO
async def function_postgres_stream(client_postgres_pool, query, batch_size=1000, output_path=None):
    if not re.match(r"^\s*(SELECT|WITH|SHOW|EXPLAIN)\b", query, re.I):
        raise ValueError("Only read-only queries allowed")
    async with client_postgres_pool.acquire() as conn:
        f = open(output_path, "w", newline="") if output_path else None
        writer_file = csv.writer(f) if f else None
        stream = StringIO()
        writer_stream = csv.writer(stream)
        header_written = False
        async for row in conn.cursor(query):
            if not header_written:
                writer_stream.writerow(row.keys())
                if writer_file:
                    writer_file.writerow(row.keys())
                yield stream.getvalue()
                stream.seek(0)
                stream.truncate(0)
                header_written = True
            writer_stream.writerow(row.values())
            if writer_file:
                writer_file.writerow(row.values())
                f.flush()
            yield stream.getvalue()
            stream.seek(0)
            stream.truncate(0)
        if f:
            f.close()
            
async def function_postgres_init(client_postgres_pool, config_postgres_schema, function_postgres_schema_read):
    if not config_postgres_schema:
        raise Exception("config_postgres_schema null")
    async def function_init_extension(conn):
        for extension in ["postgis", "pg_trgm"]:
            await conn.execute(f"create extension if not exists {extension};")
        return None
    async def function_init_table(conn, config_postgres_schema, function_postgres_schema_read):
        postgres_schema, postgres_column_datatype = await function_postgres_schema_read(conn)
        for table, column_list in config_postgres_schema["table"].items():
            is_table = postgres_schema.get(table, {})
            if not is_table:
                query = f"create table if not exists {table} (id bigint primary key generated by default as identity not null);"
                await conn.execute(query)
        return None
    async def function_init_column(conn, config_postgres_schema, function_postgres_schema_read):
        postgres_schema, postgres_column_datatype = await function_postgres_schema_read(conn)
        for table, column_list in config_postgres_schema["table"].items():
            for column in column_list:
                column_name, column_datatype, column_is_mandatory, column_index_type = column.split("-")
                is_column = postgres_schema.get(table, {}).get(column_name, {})
                if not is_column:
                    query = f"alter table {table} add column if not exists {column_name} {column_datatype};"
                    await conn.execute(query)
        return None
    async def function_init_nullable(conn, config_postgres_schema, function_postgres_schema_read):
        postgres_schema, postgres_column_datatype = await function_postgres_schema_read(conn)
        for table, column_list in config_postgres_schema["table"].items():
            for column in column_list:
                column_name, column_datatype, column_is_mandatory, column_index_type = column.split("-")
                is_null = postgres_schema.get(table, {}).get(column_name, {}).get("is_null", None)
                if column_is_mandatory == "0" and is_null == 0:
                    query = f"alter table {table} alter column {column_name} drop not null;"
                    await conn.execute(query)
                if column_is_mandatory == "1" and is_null == 1:
                    query = f"alter table {table} alter column {column_name} set not null;"
                    await conn.execute(query)
        return None
    async def function_init_index(conn, config_postgres_schema):
        rows = await conn.fetch("SELECT indexname FROM pg_indexes WHERE schemaname='public';")
        index_name_list = [r["indexname"] for r in rows]
        for table, column_list in config_postgres_schema["table"].items():
            for column in column_list:
                column_name, column_datatype, column_is_mandatory, column_index_type = column.split("-")
                if column_index_type == "0":
                    query = f"""
                    DO $$
                    DECLARE r RECORD;
                    BEGIN
                        FOR r IN (SELECT indexname FROM pg_indexes WHERE schemaname = 'public' 
                                  AND indexname ILIKE 'index_{table}_{column_name}_%')
                        LOOP
                            EXECUTE 'DROP INDEX IF EXISTS public.' || quote_ident(r.indexname);
                        END LOOP;
                    END
                    $$;
                    """
                    await conn.execute(query)
                else:
                    index_type_list = column_index_type.split(",")
                    for index_type in index_type_list:
                        index_name = f"index_{table}_{column_name}_{index_type}"
                        if index_name not in index_name_list:
                            if index_type == "gin" and column_datatype == "text":
                                col_def = f"{column_name} gin_trgm_ops"
                            else:
                                col_def = column_name
                            query = f"create index concurrently if not exists {index_name} on {table} using {index_type} ({col_def});"
                            await conn.execute(query)
        return None
    async def function_init_query(conn, config_postgres_schema):
        rows = await conn.fetch("select constraint_name from information_schema.constraint_column_usage;")
        constraint_name_list = {r["constraint_name"].lower() for r in rows}
        for query in config_postgres_schema["query"].values():
            if query.split()[0] == "0":
                continue
            if "add constraint" in query.lower() and query.split()[5].lower() in constraint_name_list:
                continue
            await conn.execute(query)
        return None
    async with client_postgres_pool.acquire() as conn:
        await function_init_extension(conn)
        await function_init_table(conn, config_postgres_schema, function_postgres_schema_read)
        await function_init_column(conn, config_postgres_schema, function_postgres_schema_read)
        await function_init_nullable(conn, config_postgres_schema, function_postgres_schema_read)
        await function_init_index(conn, config_postgres_schema)
        await function_init_query(conn, config_postgres_schema)
    return None
  
import asyncpg, csv, re
async def function_postgres_export(postgres_url, query, batch_size=1000, output_path="export_postgres.csv"):
    if not re.match(r"^\s*(SELECT|WITH|SHOW|EXPLAIN)\b", query, re.I): raise ValueError("Only read-only queries allowed")
    conn = await asyncpg.connect(postgres_url)
    try:
        async with conn.transaction():
            writer = None
            f = None
            async for record in conn.cursor(query, prefetch=batch_size):
                if writer is None:
                    f = open(output_path, "w", newline="")
                    writer = csv.writer(f)
                    writer.writerow(record.keys())
                writer.writerow(record.values())
            if f: f.close()
    finally: await conn.close()
    return f"saved to {output_path}"

import asyncpg,random
from mimesis import Person,Address,Food,Text,Code,Datetime
async def function_postgres_create_fake_data(postgres_url,TOTAL_ROWS,BATCH_SIZE):
   conn = await asyncpg.connect(postgres_url)
   person = Person()
   address = Address()
   food = Food()
   text_gen = Text()
   code = Code()
   dt = Datetime()
   TABLES = {
   "customers": [("name", "TEXT", lambda: person.full_name()), ("email", "TEXT", lambda: person.email()), ("city", "TEXT", lambda: address.city()), ("country", "TEXT", lambda: address.country()), ("birth_date", "DATE", lambda: dt.date()), ("signup_code", "TEXT", lambda: code.imei()), ("loyalty_points", "INT", lambda: random.randint(0, 10000)), ("favorite_fruit", "TEXT", lambda: food.fruit())],
   "orders": [("order_number", "TEXT", lambda: code.imei()), ("customer_name", "TEXT", lambda: person.full_name()), ("order_date", "DATE", lambda: dt.date()), ("shipping_city", "TEXT", lambda: address.city()), ("total_amount", "INT", lambda: random.randint(10, 5000)), ("status", "TEXT", lambda: random.choice(["pending", "shipped", "delivered", "cancelled"])), ("item_count", "INT", lambda: random.randint(1, 20)), ("shipping_country", "TEXT", lambda: address.country())],
   "products": [("product_name", "TEXT", lambda: food.fruit()), ("category", "TEXT", lambda: random.choice(["electronics", "clothing", "food", "books"])), ("price", "INT", lambda: random.randint(5, 1000)), ("supplier_city", "TEXT", lambda: address.city()), ("stock_quantity", "INT", lambda: random.randint(0, 500)), ("manufacture_date", "DATE", lambda: dt.date()), ("expiry_date", "DATE", lambda: dt.date()), ("sku_code", "TEXT", lambda: code.imei())],
   "employees": [("full_name", "TEXT", lambda: person.full_name()), ("email", "TEXT", lambda: person.email()), ("department", "TEXT", lambda: random.choice(["HR", "Engineering", "Sales", "Support"])), ("city", "TEXT", lambda: address.city()), ("salary", "INT", lambda: random.randint(30000, 150000)), ("hire_date", "DATE", lambda: dt.date()), ("employee_id", "TEXT", lambda: code.imei())],
   "suppliers": [("supplier_name", "TEXT", lambda: person.full_name()), ("contact_email", "TEXT", lambda: person.email()), ("city", "TEXT", lambda: address.city()), ("country", "TEXT", lambda: address.country()), ("phone_number", "TEXT", lambda: person.telephone()), ("rating", "INT", lambda: random.randint(1, 5))],
   "invoices": [("invoice_number", "TEXT", lambda: code.imei()), ("customer_name", "TEXT", lambda: person.full_name()), ("invoice_date", "DATE", lambda: dt.date()), ("amount_due", "INT", lambda: random.randint(100, 10000)), ("due_date", "DATE", lambda: dt.date()), ("status", "TEXT", lambda: random.choice(["paid", "unpaid", "overdue"]))],
   "payments": [("payment_id", "TEXT", lambda: code.imei()), ("invoice_number", "TEXT", lambda: code.imei()), ("payment_date", "DATE", lambda: dt.date()), ("amount", "INT", lambda: random.randint(50, 10000)), ("payment_method", "TEXT", lambda: random.choice(["credit_card", "paypal", "bank_transfer"])), ("status", "TEXT", lambda: random.choice(["completed", "pending", "failed"]))],
   "departments": [("department_name", "TEXT", lambda: random.choice(["HR", "Engineering", "Sales", "Support"])), ("manager", "TEXT", lambda: person.full_name()), ("location", "TEXT", lambda: address.city()), ("budget", "INT", lambda: random.randint(50000, 1000000))],
   "projects": [("project_name", "TEXT", lambda: text_gen.word()), ("start_date", "DATE", lambda: dt.date()), ("end_date", "DATE", lambda: dt.date()), ("budget", "INT", lambda: random.randint(10000, 500000)), ("department", "TEXT", lambda: random.choice(["HR", "Engineering", "Sales", "Support"]))],
   "inventory": [("item_name", "TEXT", lambda: food.spices()), ("quantity", "INT", lambda: random.randint(0, 1000)), ("warehouse_location", "TEXT", lambda: address.city()), ("last_restock_date", "DATE", lambda: dt.date())],
   "shipments": [("shipment_id", "TEXT", lambda: code.imei()), ("order_number", "TEXT", lambda: code.imei()), ("shipment_date", "DATE", lambda: dt.date()), ("delivery_date", "DATE", lambda: dt.date()), ("status", "TEXT", lambda: random.choice(["in_transit", "delivered", "delayed"]))],
   "reviews": [("review_id", "TEXT", lambda: code.imei()), ("product_name", "TEXT", lambda: food.fruit()), ("customer_name", "TEXT", lambda: person.full_name()), ("rating", "INT", lambda: random.randint(1, 5)), ("review_date", "DATE", lambda: dt.date()), ("comments", "TEXT", lambda: text_gen.sentence())],
   "tasks": [("task_name", "TEXT", lambda: text_gen.word()), ("assigned_to", "TEXT", lambda: person.full_name()), ("due_date", "DATE", lambda: dt.date()), ("priority", "TEXT", lambda: random.choice(["low", "medium", "high"])), ("status", "TEXT", lambda: random.choice(["pending", "in_progress", "completed"]))],
   "assets": [("asset_tag", "TEXT", lambda: code.imei()), ("asset_name", "TEXT", lambda: food.fruit()), ("purchase_date", "DATE", lambda: dt.date()), ("warranty_expiry", "DATE", lambda: dt.date()), ("value", "INT", lambda: random.randint(100, 10000))],
   "locations": [("location_name", "TEXT", lambda: address.city()), ("address", "TEXT", lambda: address.address()), ("country", "TEXT", lambda: address.country()), ("postal_code", "TEXT", lambda: address.postal_code())],
   "meetings": [("meeting_id", "TEXT", lambda: code.imei()), ("topic", "TEXT", lambda: text_gen.word()), ("meeting_date", "DATE", lambda: dt.date()), ("organizer", "TEXT", lambda: person.full_name()), ("location", "TEXT", lambda: address.city())],
   "tickets": [("ticket_id", "TEXT", lambda: code.imei()), ("issue", "TEXT", lambda: text_gen.sentence()), ("reported_by", "TEXT", lambda: person.full_name()), ("status", "TEXT", lambda: random.choice(["open", "closed", "in_progress"])), ("priority", "TEXT", lambda: random.choice(["low", "medium", "high"]))],
   "subscriptions": [("subscription_id", "TEXT", lambda: code.imei()), ("customer_name", "TEXT", lambda: person.full_name()), ("start_date", "DATE", lambda: dt.date()), ("end_date", "DATE", lambda: dt.date()), ("plan_type", "TEXT", lambda: random.choice(["basic", "premium", "enterprise"]))],
   }
   async def create_tables(conn,TABLES):
      for table_name, columns in TABLES.items():
         await conn.execute(f"DROP TABLE IF EXISTS {table_name};")
         columns_def = ", ".join(f"{name} {dtype}" for name, dtype, _ in columns)
         query = f"CREATE TABLE IF NOT EXISTS {table_name} (id bigint primary key generated always as identity not null, {columns_def});"
         await conn.execute(query)
   async def insert_batch(conn, table_name, columns, batch_values):
      cols = ", ".join(name for name, _, _ in columns)
      placeholders = ", ".join(f"${i+1}" for i in range(len(columns)))
      query = f"INSERT INTO {table_name} ({cols}) VALUES ({placeholders})"
      await conn.executemany(query, batch_values)
   async def generate_data(conn,insert_batch,TABLES,TOTAL_ROWS,BATCH_SIZE):
      for table_name, columns in TABLES.items():
         print(f"Inserting data into {table_name}...")
         batch_values = []
         for _ in range(TOTAL_ROWS):
               row = tuple(gen() for _, _, gen in columns)
               batch_values.append(row)
               if len(batch_values) == BATCH_SIZE:
                  await insert_batch(conn, table_name, columns, batch_values)
                  batch_values.clear()
         if batch_values:await insert_batch(conn, table_name, columns, batch_values)
         print(f"Completed inserting {TOTAL_ROWS} rows into {table_name}")
   await create_tables(conn,TABLES)
   await generate_data(conn,insert_batch,TABLES,TOTAL_ROWS,BATCH_SIZE)
   await conn.close()
   return None

async def function_update_ids(client_postgres_pool,table,ids,column,value,updated_by_id,created_by_id=None):
   query=f"update {table} set {column}=$1,updated_by_id=$2 where id in ({ids}) and (created_by_id=$3 or $3 is null);"
   async with client_postgres_pool.acquire() as conn:
      await conn.execute(query,value,updated_by_id,created_by_id)
   return None

async def function_delete_ids(client_postgres_pool,table,ids,created_by_id=None):
   query=f"delete from {table} where id in ({ids}) and (created_by_id=$1 or $1 is null);"
   async with client_postgres_pool.acquire() as conn:
      await conn.execute(query,created_by_id)
   return None

async def function_parent_object_read(client_postgres_pool,table,parent_column,parent_table,order,limit,offset,created_by_id=None):
   query=f'''
   with x as (
      select {parent_column} from {table} 
      where (created_by_id=$1 or $1 is null) 
      order by {order} limit {limit} offset {offset}
   ) select ct.* from x left join {parent_table} as ct on x.{parent_column}=ct.id;
   '''
   async with client_postgres_pool.acquire() as conn:
      rows=await conn.fetch(query,created_by_id)
   return rows

import datetime
async def function_update_last_active_at(client_postgres_pool, user_id):
    try:
        query = "UPDATE users SET last_active_at=$1 WHERE id=$2;"
        async with client_postgres_pool.acquire() as conn:
            await conn.execute(query, datetime.datetime.now(), user_id)
    except Exception as e:
        print(str(e))
    return None

async def function_read_user_single(client_postgres_pool, user_id):
    query = "SELECT * FROM users WHERE id=$1;"
    async with client_postgres_pool.acquire() as conn:
        row = await conn.fetchrow(query, user_id)
    user = dict(row) if row else None
    if not user:
        raise Exception("user not found")
    return user

async def function_delete_user_single(mode, client_postgres_pool, user_id):
    if mode == "soft":
        query = "UPDATE users SET is_deleted=1 WHERE id=$1;"
    elif mode == "hard":
        query = "DELETE FROM users WHERE id=$1;"
    else:
        raise Exception("Invalid mode")
    async with client_postgres_pool.acquire() as conn:
        await conn.execute(query, user_id)
    return None

async def function_add_creator_data(client_postgres_pool, object_list, user_key_list):
    if not object_list:
        return object_list
    object_list = [dict(obj) for obj in object_list]
    created_by_ids = {str(obj["created_by_id"]) for obj in object_list if obj.get("created_by_id")}
    users = {}
    if created_by_ids:
        query = f"SELECT * FROM users WHERE id = ANY($1);"
        rows = await client_postgres_pool.fetch(query, list(map(int, created_by_ids)))
        users = {str(user["id"]): dict(user) for user in rows}
    for obj in object_list:
        created_by_id = str(obj.get("created_by_id"))
        if created_by_id in users:
            for key in user_key_list:
                obj[f"creator_{key}"] = users[created_by_id].get(key)
        else:
            for key in user_key_list:
                obj[f"creator_{key}"] = None
    return object_list

async def function_ownership_check(client_postgres_pool, table, id, user_id):
    if table == "users":
        if id != user_id:
            raise Exception("obj ownership issue")
    else:
        query = f"SELECT created_by_id FROM {table} WHERE id = $1;"
        row = await client_postgres_pool.fetchrow(query, id)
        if not row:
            raise Exception("no obj")
        if row["created_by_id"] != user_id:
            raise Exception("obj ownership issue")
    return None

import random
async def function_otp_generate(mode, data, client_postgres_pool):
    otp = random.randint(100000, 999999)
    query = f"INSERT INTO otp (otp, {mode}) VALUES ($1, $2)"
    async with client_postgres_pool.acquire() as conn:
        await conn.execute(query, otp, data.strip().lower())
    return otp

async def function_otp_verify(mode, data, otp, client_postgres_pool):
    query = f"SELECT otp FROM otp WHERE created_at > current_timestamp - interval '10 minutes' AND {mode} = $1 ORDER BY id DESC LIMIT 1"
    async with client_postgres_pool.acquire() as conn:
        rows = await conn.fetch(query, data.strip().lower())
    if not rows or int(rows[0]["otp"]) != int(otp):
        raise Exception("otp mismatch or not found")
    return None

async def function_read_user_count(client_postgres_pool,config_user_count_query,user_id):
   output={}
   async with client_postgres_pool.acquire() as conn:
      for key,query in config_user_count_query.items():
         rows=await conn.fetch(query,user_id)
         row=rows[0] if rows else None
         output[key]=row[0] if row else 0
   return output

async def function_message_inbox(client_postgres_pool,user_id,order,limit,offset,is_unread=None):
   if not is_unread:
      query=f'''
      with x as (
         select id,abs(created_by_id-user_id) as unique_id 
         from message 
         where (created_by_id=$1 or user_id=$1)
      ),y as (select max(id) as id from x group by unique_id),
      z as (select m.* from y left join message as m on y.id=m.id)
      select * from z order by {order} limit {limit} offset {offset};
      '''
   else:
      query=f'''
      with x as (
         select id,abs(created_by_id-user_id) as unique_id 
         from message 
         where (created_by_id=$1 or user_id=$1)
      ),y as (select max(id) as id from x group by unique_id),
      z as (select m.* from y left join message as m on y.id=m.id),
      a as (select * from z where user_id=$1 and (is_read!=1 or is_read is null))
      select * from a order by {order} limit {limit} offset {offset};
      '''
   async with client_postgres_pool.acquire() as conn:
      return await conn.fetch(query,user_id)

async def function_message_received(client_postgres_pool,user_id,order,limit,offset,is_unread=None):
   if not is_unread:
      query=f"select * from message where user_id=$1 order by {order} limit {limit} offset {offset};"
   else:
      query=f"select * from message where user_id=$1 and is_read is distinct from 1 order by {order} limit {limit} offset {offset};"
   async with client_postgres_pool.acquire() as conn:
      return await conn.fetch(query,user_id)

async def function_message_thread(client_postgres_pool,user_id_1,user_id_2,order,limit,offset):
   query=f'''
   select * from message 
   where ((created_by_id=$1 and user_id=$2) or (created_by_id=$2 and user_id=$1)) 
   order by {order} limit {limit} offset {offset};
   '''
   async with client_postgres_pool.acquire() as conn:
      return await conn.fetch(query,user_id_1,user_id_2)

async def function_message_thread_mark_read(client_postgres_pool,user_id_1,user_id_2):
   query="update message set is_read=1 where created_by_id=$1 and user_id=$2;"
   async with client_postgres_pool.acquire() as conn:
      await conn.execute(query,user_id_2,user_id_1)
   return None

async def function_message_object_mark_read(client_postgres_pool,object_list):
   try:
      ids=','.join(str(item['id']) for item in object_list)
      query=f"update message set is_read=1 where id in ({ids});"
      async with client_postgres_pool.acquire() as conn:
         await conn.execute(query)
   except Exception as e:
      print(str(e))
   return None

async def function_message_delete_single(client_postgres_pool,user_id,message_id):
   query="delete from message where id=$1 and (created_by_id=$2 or user_id=$2);"
   async with client_postgres_pool.acquire() as conn:
      await conn.execute(query,message_id,user_id)
   return None

async def function_message_delete_bulk(mode,client_postgres_pool,user_id):
   if mode=="created":
      query="delete from message where created_by_id=$1;"
   elif mode=="received":
      query="delete from message where user_id=$1;"
   elif mode=="all":
      query="delete from message where (created_by_id=$1 or user_id=$1);"
   async with client_postgres_pool.acquire() as conn:
      await conn.execute(query,user_id)
   return None

import hashlib
async def function_auth_signup_username_password(client_postgres_pool,type,username,password):
    query="insert into users (type,username,password) values ($1,$2,$3) returning *;"
    async with client_postgres_pool.acquire() as conn:
        output = await conn.fetch(query,type,username,hashlib.sha256(str(password).encode()).hexdigest())
    return output[0]

async def function_auth_signup_username_password_bigint(client_postgres_pool,type,username_bigint,password_bigint):
    query="insert into users (type,username_bigint,password_bigint) values ($1,$2,$3) returning *;"
    async with client_postgres_pool.acquire() as conn:
        output = await conn.fetch(query,type,username_bigint,password_bigint)
    return output[0]

import hashlib
async def function_auth_login_password_username(client_postgres_pool,type,password,username,function_token_encode,config_key_jwt,config_token_expire_sec,config_token_user_key_list):
    query="select * from users where type=$1 and username=$2 and password=$3 order by id desc limit 1;"
    async with client_postgres_pool.acquire() as conn:
        output = await conn.fetch(query,type,username,hashlib.sha256(str(password).encode()).hexdigest())
    user = output[0] if output else None
    if not user: raise Exception("user not found")
    token = await function_token_encode(config_key_jwt,config_token_expire_sec,config_token_user_key_list,user)
    return token

async def function_auth_login_password_username_bigint(client_postgres_pool,type,password_bigint,username_bigint,function_token_encode,config_key_jwt,config_token_expire_sec,config_token_user_key_list):
    query="select * from users where type=$1 and username_bigint=$2 and password_bigint=$3 order by id desc limit 1;"
    async with client_postgres_pool.acquire() as conn:
        output = await conn.fetch(query,type,username_bigint,password_bigint)
    user = output[0] if output else None
    if not user: raise Exception("user not found")
    token = await function_token_encode(config_key_jwt,config_token_expire_sec,config_token_user_key_list,user)
    return token

import hashlib
async def function_auth_login_password_email(client_postgres_pool,type,password,email,function_token_encode,config_key_jwt,config_token_expire_sec,config_token_user_key_list):
    query="select * from users where type=$1 and email=$2 and password=$3 order by id desc limit 1;"
    async with client_postgres_pool.acquire() as conn:
        output = await conn.fetch(query,type,email,hashlib.sha256(str(password).encode()).hexdigest())
    user = output[0] if output else None
    if not user: raise Exception("user not found")
    token = await function_token_encode(config_key_jwt,config_token_expire_sec,config_token_user_key_list,user)
    return token

import hashlib
async def function_auth_login_password_mobile(client_postgres_pool,type,password,mobile,function_token_encode,config_key_jwt,config_token_expire_sec,config_token_user_key_list):
    query="select * from users where type=$1 and mobile=$2 and password=$3 order by id desc limit 1;"
    async with client_postgres_pool.acquire() as conn:
        output = await conn.fetch(query,type,mobile,hashlib.sha256(str(password).encode()).hexdigest())
    user = output[0] if output else None
    if not user: raise Exception("user not found")
    token = await function_token_encode(config_key_jwt,config_token_expire_sec,config_token_user_key_list,user)
    return token

async def function_auth_login_otp_email(client_postgres_pool,type,email,function_otp_verify,otp,function_token_encode,config_key_jwt,config_token_expire_sec,config_token_user_key_list):
    await function_otp_verify("email",otp,email,client_postgres_pool)
    async with client_postgres_pool.acquire() as conn:
        output = await conn.fetch("select * from users where type=$1 and email=$2 order by id desc limit 1;",type,email)
        user = output[0] if output else None
        if not user:
            output = await conn.fetch("insert into users (type,email) values ($1,$2) returning *;",type,email)
            user = output[0] if output else None
    token = await function_token_encode(config_key_jwt,config_token_expire_sec,config_token_user_key_list,user)
    return token

async def function_auth_login_otp_mobile(client_postgres_pool,type,mobile,function_otp_verify,otp,function_token_encode,config_key_jwt,config_token_expire_sec,config_token_user_key_list):
    await function_otp_verify("mobile",otp,mobile,client_postgres_pool)
    async with client_postgres_pool.acquire() as conn:
        output = await conn.fetch("select * from users where type=$1 and mobile=$2 order by id desc limit 1;",type,mobile)
        user = output[0] if output else None
        if not user:
            output = await conn.fetch("insert into users (type,mobile) values ($1,$2) returning *;",type,mobile)
            user = output[0] if output else None
    token = await function_token_encode(config_key_jwt,config_token_expire_sec,config_token_user_key_list,user)
    return token

import json
from google.oauth2 import id_token
from google.auth.transport import requests as google_request
async def function_auth_login_google(client_postgres_pool, type, google_token, config_google_login_client_id, function_token_encode, config_key_jwt, config_token_expire_sec, config_token_user_key_list):
    request = google_request.Request()
    id_info = id_token.verify_oauth2_token(google_token, request, config_google_login_client_id)
    google_user = {"sub": id_info.get("sub"), "email": id_info.get("email"), "name": id_info.get("name"), "picture": id_info.get("picture"), "email_verified": id_info.get("email_verified")}
    async with client_postgres_pool.acquire() as conn:
        output = await conn.fetch("SELECT * FROM users WHERE type=$1 AND google_id=$2 ORDER BY id DESC LIMIT 1", type, google_user["sub"])
        user = output[0] if output else None
        if not user:
            output = await conn.fetch("INSERT INTO users (type, google_id, google_data) VALUES ($1, $2, $3) RETURNING *", type, google_user["sub"], json.dumps(google_user))
            user = output[0] if output else None
    token = await function_token_encode(config_key_jwt, config_token_expire_sec, config_token_user_key_list, user)
    return token

from fastapi import FastAPI
def function_fastapi_app_read(is_debug,lifespan):
   app=FastAPI(debug=is_debug,lifespan=lifespan)
   return app

import uvicorn
async def function_server_start(app):
   config=uvicorn.Config(app,host="0.0.0.0",port=8000,log_level="info")
   server=uvicorn.Server(config)
   await server.serve()
   
from fastapi.middleware.cors import CORSMiddleware
def function_add_cors(app,cors_origin,cors_method,cors_headers,cors_allow_credentials):
   app.add_middleware(CORSMiddleware,allow_origins=cors_origin,allow_methods=cors_method,allow_headers=cors_headers,allow_credentials=cors_allow_credentials)
   return None

from prometheus_fastapi_instrumentator import Instrumentator
def function_add_prometheus(app):
   Instrumentator().instrument(app).expose(app)
   return None

def function_add_app_state(var_dict,app,prefix_tuple):
    for k, v in var_dict.items():
        if k.startswith(prefix_tuple):
            setattr(app.state, k, v)

import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
def function_add_sentry(config_sentry_dsn):
   sentry_sdk.init(dsn=config_sentry_dsn,integrations=[FastApiIntegration()],traces_sample_rate=1.0,profiles_sample_rate=1.0,send_default_pii=True)
   return None

import os
import importlib.util
from pathlib import Path
import traceback
def function_add_router(app,pattern):
   base_dir = Path(__file__).parent
   def load_module(module_path):
      try:
         rel_path = os.path.relpath(module_path, base_dir)
         module_name = os.path.splitext(rel_path)[0].replace(os.sep, ".")
         if not module_name.strip():
            return
         spec = importlib.util.spec_from_file_location(module_name, module_path)
         if spec and spec.loader:
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            if hasattr(module, pattern):
               app.include_router(module.router)
      except Exception as e:
         print(f"[WARN] Failed to load router module: {module_path}")
         traceback.print_exc()
   def add_root_pattern_files():
      for file in os.listdir(base_dir):
         if file.startswith(pattern) and file.endswith(".py"):
            module_path = base_dir / file
            load_module(module_path)
   def add_pattern_folder_files():
      router_dir = base_dir / pattern
      if router_dir.exists() and router_dir.is_dir():
         for file in os.listdir(router_dir):
            if file.endswith(".py"):
               module_path = router_dir / file
               load_module(module_path)
   add_root_pattern_files()
   add_pattern_folder_files()
   return None

async def function_check_ratelimiter(request,client_redis_ratelimiter,config_api):
   if not client_redis_ratelimiter:raise Exception("config_redis_url_ratelimiter missing")
   limit,window=config_api.get(request.url.path).get("ratelimiter_times_sec")
   identifier=request.state.user.get("id") if request.state.user else request.client.host
   ratelimiter_key=f"ratelimiter:{request.url.path}:{identifier}"
   current_count=await client_redis_ratelimiter.get(ratelimiter_key)
   if current_count and int(current_count)+1>limit:raise Exception("ratelimiter exceeded")
   pipe=client_redis_ratelimiter.pipeline()
   pipe.incr(ratelimiter_key)
   if not current_count:pipe.expire(ratelimiter_key,window)
   await pipe.execute()
   return None

async def function_check_api_access(config_mode_check_api_access,request,cache_users_api_access,client_postgres_pool,config_api):
   if config_mode_check_api_access=="token":
      user_api_access_list=[int(item.strip()) for item in request.state.user["api_access"].split(",")] if request.state.user["api_access"] else []
   elif config_mode_check_api_access=="cache":
      user_api_access_list=cache_users_api_access.get(request.state.user["id"],"absent")
   if user_api_access_list=="absent":
      async with client_postgres_pool.acquire() as conn:
         rows=await conn.fetch("select id,api_access from users where id=$1",request.state.user["id"])
      user=rows[0] if rows else None
      if not user:raise Exception("user not found")
      api_access_str=user["api_access"]
      if not api_access_str:raise Exception("api access denied")
      user_api_access_list=[int(item.strip()) for item in api_access_str.split(",")]
   api_id=config_api.get(request.url.path,{}).get("id")
   if not api_id:raise Exception("api id not mapped")
   if api_id not in user_api_access_list:raise Exception("api access denied")
   return None

async def function_check_is_active(config_mode_check_is_active,request,cache_users_is_active,client_postgres_pool):
   if config_mode_check_is_active=="token":user_is_active=request.state.user["is_active"]
   elif config_mode_check_is_active=="cache":user_is_active=cache_users_is_active.get(request.state.user["id"],"absent")
   if user_is_active=="absent":
      async with client_postgres_pool.acquire() as conn:
         rows=await conn.fetch("select id,is_active from users where id=$1",request.state.user["id"])
      user=rows[0] if rows else None
      if not user:raise Exception("user not found")
      user_is_active=user["is_active"]
   if user_is_active==0:raise Exception("user not active")
   return None

from fastapi import Response
import gzip,base64,time
inmemory_cache={}
async def function_api_response_cache(mode,request,response,client_redis,config_api):
   query_param_sorted="&".join(f"{k}={v}" for k, v in sorted(request.query_params.items()))
   identifier=request.state.user.get("id") if "my/" in request.url.path else 0
   cache_key=f"cache:{request.url.path}?{query_param_sorted}:{identifier}"
   cache_mode,expire_sec=config_api.get(request.url.path,{}).get("cache_sec",(None,None))
   if mode=="get":
      response=None
      cached_response=None
      if cache_mode=="redis":
         cached_response=await client_redis.get(cache_key)
         if cached_response:response=Response(content=gzip.decompress(base64.b64decode(cached_response)).decode(),status_code=200,media_type="application/json")
      if cache_mode=="inmemory":
         cache_item=inmemory_cache.get(cache_key)
         if cache_item and cache_item["expire_at"]>time.time():response=Response(content=gzip.decompress(base64.b64decode(cache_item["data"])).decode(),status_code=200,media_type="application/json")
   if mode=="set":
      body=b"".join([chunk async for chunk in response.body_iterator])
      if cache_mode=="redis":
         await client_redis.setex(cache_key,expire_sec,base64.b64encode(gzip.compress(body)).decode())
      if cache_mode=="inmemory":
         inmemory_cache[cache_key]={"data":base64.b64encode(gzip.compress(body)).decode(),"expire_at":time.time()+expire_sec}
      response=Response(content=body, status_code=response.status_code, media_type=response.media_type)
   return response

from fastapi import Request,responses
from starlette.background import BackgroundTask
async def function_api_response_background(request,api_function):
   body=await request.body()
   async def receive():return {"type":"http.request","body":body}
   async def api_function_new():
      request_new=Request(scope=request.scope,receive=receive)
      await api_function(request_new)
   response=responses.JSONResponse(status_code=200,content={"status":1,"message":"added in background"})
   response.background=BackgroundTask(api_function_new)
   return response

async def function_log_api_usage(client_postgres_pool,days,created_by_id=None):
   query=f"select api,count(*) from log_api where created_at >= now() - interval '{days} days' and (created_by_id=$1 or $1 is null) group by api limit 1000;"
   async with client_postgres_pool.acquire() as conn:
      rows=await conn.fetch(query,created_by_id)
   return {r["api"]:r["count"] for r in rows}

import csv,io
async def function_file_to_object_list(file):
   content=await file.read()
   content=content.decode("utf-8")
   reader=csv.DictReader(io.StringIO(content))
   object_list=[row for row in reader]
   await file.close()
   return object_list

import os
async def function_stream_file(path,chunk_size=1024*1024):
   with open(path, "rb") as f:
      while chunk := f.read(chunk_size):
         yield chunk

import os
def function_render_html(name: str):
    if ".." in name: 
        raise Exception("invalid name")
    match = None
    for root, dirs, files in os.walk("."):
        dirs[:] = [d for d in dirs if not d.startswith(".") and d != "venv"]
        if f"{name}.html" in files:
            match = os.path.join(root, f"{name}.html")
            break
    if not match: 
        raise Exception("file not found")
    with open(match, "r", encoding="utf-8") as file:
        return file.read()
    
async def function_param_read(request, mode, config):
    if mode == "query":
        param = dict(request.query_params)
    elif mode == "form":
        form_data = await request.form()
        param = {k: v for k, v in form_data.items() if isinstance(v, str)}
        param.update({
            k: [f for f in form_data.getlist(k) if getattr(f, "filename", None)]
            for k in form_data.keys()
            if any(getattr(f, "filename", None) for f in form_data.getlist(k))
        })
    elif mode == "body":
        param = await request.json()
    else:
        raise Exception(f"Invalid mode: {mode}")
    def cast(value, dtype):
        if dtype == "int":
            return int(value)
        if dtype == "float":
            return float(value)
        if dtype == "bool":
            return str(value).lower() in ("1", "true", "yes", "on")
        if dtype == "list":
            if isinstance(value, str):
                return [v.strip() for v in value.split(",")]
            if isinstance(value, list):
                return value
            return [value]
        if dtype == "file":
            return value if isinstance(value, list) else [value]
        return value
    for key, dtype, mandatory, default in config:
        if mandatory and key not in param:
            raise Exception(f"{key} missing from {mode} param")
        value = param.get(key, default)
        if dtype and value is not None:
            try:
                value = cast(value, dtype)
            except Exception:
                raise Exception(f"{key} must be of type {dtype}")
        param[key] = value
    return param

import jwt,json
async def function_token_decode(token,config_key_jwt):
   user=json.loads(jwt.decode(token,config_key_jwt,algorithms="HS256")["data"])
   return user

import jwt,json,time
async def function_token_encode(config_key_jwt,config_token_expire_sec,key_list,obj):
   data=dict(obj)
   payload={k:data.get(k) for k in key_list}
   payload=json.dumps(payload,default=str)
   token=jwt.encode({"exp":time.time()+config_token_expire_sec,"data":payload},config_key_jwt)
   return token

async def function_token_check(request,config_key_root,config_key_jwt,config_api,function_token_decode):
   user={}
   api=request.url.path
   token=request.headers.get("Authorization").split("Bearer ",1)[1] if request.headers.get("Authorization") and request.headers.get("Authorization").startswith("Bearer ") else None
   if api.startswith("/root"):
      if token!=config_key_root:raise Exception("token root mismatch")
   else:
      if token:user=await function_token_decode(token,config_key_jwt)
      if api.startswith("/my") and not token:raise Exception("token missing")
      elif api.startswith("/private") and not token:raise Exception("token missing")
      elif api.startswith("/admin") and not token:raise Exception("token missing")
      elif config_api.get(api,{}).get("is_token")==1 and not token:raise Exception("token missing")
   return user

def function_converter_numeric(mode,x):
   MAX_LEN = 30
   CHARS = "abcdefghijklmnopqrstuvwxyz0123456789-_.@#"
   BASE = len(CHARS)
   CHAR_TO_NUM = {ch: i for i, ch in enumerate(CHARS)}
   NUM_TO_CHAR = {i: ch for i, ch in enumerate(CHARS)}
   if mode=="encode":
      if len(x) > MAX_LEN:raise Exception(f"String too long (max {MAX_LEN} characters)")
      num = 0
      for ch in x:
         if ch not in CHAR_TO_NUM:raise Exception(f"Unsupported character: '{ch}'")
         num = num * BASE + CHAR_TO_NUM[ch]
      output=len(x) * (BASE ** MAX_LEN) + num
   if mode=="decode":
      length = x // (BASE ** MAX_LEN)
      num = x % (BASE ** MAX_LEN)
      chars = []
      for _ in range(length):
         num, rem = divmod(num, BASE)
         chars.append(NUM_TO_CHAR[rem])
      output=''.join(reversed(chars))
   return output

def function_converter_bigint(mode,x):
   MAX_LENGTH = 11
   CHARSET = 'abcdefghijklmnopqrstuvwxyz0123456789_'
   BASE = len(CHARSET)
   LENGTH_BITS = 6
   VALUE_BITS = 64 - LENGTH_BITS
   CHAR_TO_INDEX = {c: i for i, c in enumerate(CHARSET)}
   INDEX_TO_CHAR = {i: c for i, c in enumerate(CHARSET)}
   if mode=="encode":
      if len(x) > MAX_LENGTH:raise Exception(f"text length exceeds {MAX_LENGTH} characters.")
      value = 0
      for char in x:
         if char not in CHAR_TO_INDEX:raise Exception(f"Invalid character: {char}")
         value = value * BASE + CHAR_TO_INDEX[char]
      output=(len(x) << VALUE_BITS) | value
   if mode=="decode":
      length = x >> VALUE_BITS
      value = x & ((1 << VALUE_BITS) - 1)
      chars = []
      for _ in range(length):
         value, index = divmod(value, BASE)
         chars.append(INDEX_TO_CHAR[index])
      output=''.join(reversed(chars))
   return output

import gspread
from google.oauth2.service_account import Credentials
async def function_gsheet_client_read(config_gsheet_service_account_json_path,config_gsheet_scope_list):
   client_gsheet=gspread.authorize(Credentials.from_service_account_file(config_gsheet_service_account_json_path,scopes=config_gsheet_scope_list))
   return client_gsheet

async def function_gsheet_object_create(client_gsheet,spreadsheet_id,sheet_name,object_list):
   for obj in object_list:
      row=[obj[key] for key in sorted(obj.keys())]
      output=client_gsheet.open_by_key(spreadsheet_id).worksheet(sheet_name).append_row(row)
   return output

async def function_gsheet_object_read(client_gsheet,spreadsheet_id,sheet_name,cell_boundary):
   worksheet=client_gsheet.open_by_key(spreadsheet_id).worksheet(sheet_name)
   if cell_boundary:output=worksheet.get(cell_boundary)
   else:output=worksheet.get_all_records()
   return output

import pandas
async def function_gsheet_object_read_pandas(spreadsheet_id,gid):
   url=f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/export?format=csv&gid={gid}"
   df=pandas.read_csv(url)
   output=df.to_dict(orient="records")
   return output

from posthog import Posthog
async def function_posthog_client_read(config_posthog_project_host,config_posthog_project_key):
   client_posthog=Posthog(config_posthog_project_key,host=config_posthog_project_host)
   return client_posthog

import motor.motor_asyncio
async def function_mongodb_client_read(config_mongodb_url):
   client_mongodb=motor.motor_asyncio.AsyncIOMotorClient(config_mongodb_url)
   return client_mongodb

async def function_mongodb_object_create(client_mongodb,database,table,object_list):
   mongodb_client_database=client_mongodb[database]
   output=await mongodb_client_database[table].insert_many(object_list)
   return str(output)

import pytesseract
from PIL import Image
from pdf2image import convert_from_path
def function_export_ocr_tesseract(file_path, output_path="export_ocr.txt"):
    if file_path.lower().endswith('.pdf'):
        images = convert_from_path(file_path)
        text = ''
        for img in images:
            text += pytesseract.image_to_string(img, lang='eng') + '\n'
    else:
        image = Image.open(file_path)
        text = pytesseract.image_to_string(image, lang='eng')
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(text)
    print(f"Saved to: {output_path}")
    return None
 
from celery import Celery
async def function_celery_client_read_producer(config_celery_broker_url,config_celery_backend_url):
   client_celery_producer=Celery("producer",broker=config_celery_broker_url,backend=config_celery_backend_url)
   return client_celery_producer

from celery import Celery
def function_celery_client_read_consumer(config_celery_broker_url,config_celery_backend_url):
   client_celery_consumer=Celery("worker",broker=config_celery_broker_url,backend=config_celery_backend_url)
   return client_celery_consumer

async def function_celery_producer(client_celery_producer,function,param_list):
   output=client_celery_producer.send_task(function,args=param_list)
   return output.id

import aio_pika
async def function_rabbitmq_client_read_producer(config_rabbitmq_url):
   client_rabbitmq=await aio_pika.connect_robust(config_rabbitmq_url)
   client_rabbitmq_producer=await client_rabbitmq.channel()
   return client_rabbitmq,client_rabbitmq_producer

import aio_pika
async def function_rabbitmq_client_read_consumer(config_rabbitmq_url,config_channel_name):
   client_rabbitmq=await aio_pika.connect_robust(config_rabbitmq_url)
   client_rabbitmq_channel=await client_rabbitmq.channel()
   client_rabbitmq_consumer=await client_rabbitmq_channel.declare_queue(config_channel_name,auto_delete=False)
   return client_rabbitmq,client_rabbitmq_consumer

import json,aio_pika
async def function_rabbitmq_producer(client_rabbitmq_producer,channel_name,payload):
    body=json.dumps(payload).encode()
    message=aio_pika.Message(body=body)
    output=await client_rabbitmq_producer.default_exchange.publish(message,routing_key=channel_name)
    return output

from aiokafka import AIOKafkaProducer
async def function_kafka_client_read_producer(config_kafka_url,config_kafka_username,config_kafka_password):
    client_kafka_producer=AIOKafkaProducer(bootstrap_servers=config_kafka_url,security_protocol="SASL_PLAINTEXT",sasl_mechanism="PLAIN",sasl_plain_username=config_kafka_username,sasl_plain_password=config_kafka_password,)
    await client_kafka_producer.start()
    return client_kafka_producer
 
from aiokafka import AIOKafkaConsumer
async def function_kafka_client_read_consumer(config_kafka_url,config_kafka_username,config_kafka_password,topic_name,group_id,enable_auto_commit):
    client_kafka_consumer=AIOKafkaConsumer(topic_name,bootstrap_servers=config_kafka_url,group_id=group_id, security_protocol="SASL_PLAINTEXT",sasl_mechanism="PLAIN",sasl_plain_username=config_kafka_username,sasl_plain_password=config_kafka_password,auto_offset_reset="earliest",enable_auto_commit=enable_auto_commit)
    await client_kafka_consumer.start()
    return client_kafka_consumer
 
import json
async def function_kafka_producer(client_kafka_producer,channel_name,payload):
   output=await client_kafka_producer.send_and_wait(channel_name,json.dumps(payload,indent=2).encode('utf-8'),partition=0)
   return output

import redis.asyncio as redis
async def function_redis_client_read(config_redis_url):
   client_redis=redis.Redis.from_pool(redis.ConnectionPool.from_url(config_redis_url))
   return client_redis

async def function_redis_client_read_consumer(client_redis,channel_name):
   client_redis_consumer=client_redis.pubsub()
   await client_redis_consumer.subscribe(channel_name)
   return client_redis_consumer

import json
async def function_redis_producer(client_redis,channel_name,payload):
   output=await client_redis.publish(channel_name,json.dumps(payload))
   return output

import json
async def function_redis_object_read(client_redis,key):
   output=await client_redis.get(key)
   if output:output=json.loads(output)
   return output

async def function_redis_object_create(client_redis,key_list,object_list,expiry_sec):
   async with client_redis.pipeline(transaction=True) as pipe:
      for index,obj in enumerate(object_list):
         key=key_list[index]
         if not expiry_sec:pipe.set(key,json.dumps(obj))
         else:pipe.setex(key,expiry_sec,json.dumps(obj))
      await pipe.execute()
   return None

async def function_redis_object_delete(client_redis,object_list):
   async with client_redis.pipeline(transaction=True) as pipe:
      for obj in object_list:
         pipe.delete(obj["key"])
      await pipe.execute()
   return None

import boto3
async def function_ses_client_read(config_aws_access_key_id,config_aws_secret_access_key,config_ses_region_name):
   client_ses=boto3.client("ses",region_name=config_ses_region_name,config_aws_access_key_id=config_aws_access_key_id,config_aws_secret_access_key=config_aws_secret_access_key)
   return client_ses

async def function_ses_send_email(client_ses,email_from,email_to_list,title,body):
   client_ses.send_email(Source=email_from,Destination={"ToAddresses":email_to_list},Message={"Subject":{"Charset":"UTF-8","Data":title},"Body":{"Text":{"Charset":"UTF-8","Data":body}}})
   return None

import boto3
async def function_sns_client_read(config_aws_access_key_id,config_aws_secret_access_key,config_sns_region_name):
   client_sns=boto3.client("sns",region_name=config_sns_region_name,config_aws_access_key_id=config_aws_access_key_id,config_aws_secret_access_key=config_aws_secret_access_key)
   return client_sns

import boto3
async def function_s3_client_read(config_aws_access_key_id,config_aws_secret_access_key,config_s3_region_name):
   client_s3=boto3.client("s3",region_name=config_s3_region_name,config_aws_access_key_id=config_aws_access_key_id,config_aws_secret_access_key=config_aws_secret_access_key)
   client_s3_resource=boto3.resource("s3",region_name=config_s3_region_name,config_aws_access_key_id=config_aws_access_key_id,config_aws_secret_access_key=config_aws_secret_access_key)
   return client_s3,client_s3_resource

async def function_s3_bucket_create(config_s3_region_name,client_s3,bucket):
   output=client_s3.create_bucket(Bucket=bucket,CreateBucketConfiguration={'LocationConstraint':config_s3_region_name})
   return output

async def function_s3_bucket_public(client_s3,bucket):
   client_s3.put_public_access_block(Bucket=bucket,PublicAccessBlockConfiguration={'BlockPublicAcls':False,'IgnorePublicAcls':False,'BlockPublicPolicy':False,'RestrictPublicBuckets':False})
   policy='''{"Version":"2012-10-17","Statement":[{"Sid":"PublicRead","Effect":"Allow","Principal":"*","Action":"s3:GetObject","Resource":["arn:aws:s3:::bucket_name/*"]}]}'''
   output=client_s3.put_bucket_policy(Bucket=bucket,Policy=policy.replace("bucket_name",bucket))
   return output

async def function_s3_bucket_empty(client_s3_resource,bucket):
   output=client_s3_resource.Bucket(bucket).objects.all().delete()
   return output

async def function_s3_bucket_delete(client_s3,bucket):
   output=client_s3.delete_bucket(Bucket=bucket)
   return output

async def function_s3_url_delete(client_s3_resource,url):
   bucket=url.split("//",1)[1].split(".",1)[0]
   key=url.rsplit("/",1)[1]
   output=client_s3_resource.Object(bucket,key).delete()
   return output

async def function_sns_send_mobile_message(client_sns,mobile,message):
   client_sns.publish(PhoneNumber=mobile,Message=message)
   return None

async def function_sns_send_mobile_message_template(client_sns,mobile,message,template_id,entity_id,sender_id):
   client_sns.publish(PhoneNumber=mobile, Message=message,MessageAttributes={"AWS.MM.SMS.EntityId":{"DataType":"String","StringValue":entity_id},"AWS.MM.SMS.TemplateId":{"DataType":"String","StringValue":template_id},"AWS.SNS.SMS.SenderID":{"DataType":"String","StringValue":sender_id},"AWS.SNS.SMS.SMSType":{"DataType":"String","StringValue":"Transactional"}})
   return None

import uuid
from io import BytesIO
async def function_s3_upload_file(bucket,key,file,client_s3,config_s3_region_name,config_limit_s3_kb=100):
    if not key:
        if "." not in file.filename:raise Exception("file must have extension")
        key=f"{uuid.uuid4().hex}.{file.filename.rsplit('.',1)[1]}"
    if "." not in key:raise Exception("extension must")
    file_content=await file.read()
    file.file.close()
    file_size_kb=round(len(file_content)/1024)
    if file_size_kb>config_limit_s3_kb:raise Exception("file size issue")
    client_s3.upload_fileobj(BytesIO(file_content),bucket,key)
    output={file.filename:f"https://{bucket}.s3.{config_s3_region_name}.amazonaws.com/{key}"}
    return output

import uuid
async def function_s3_upload_presigned(bucket,key,client_s3,config_s3_region_name,config_limit_s3_kb=100,config_s3_presigned_expire_sec=60):
   if not key:key=f"{uuid.uuid4().hex}.bin"
   if "." not in key:raise Exception("extension must")
   output=client_s3.generate_presigned_post(Bucket=bucket,Key=key,ExpiresIn=config_s3_presigned_expire_sec,Conditions=[['content-length-range',1,config_limit_s3_kb*1024]])
   for k,v in output["fields"].items():output[k]=v
   del output["fields"]
   output["url_final"]=f"https://{bucket}.s3.{config_s3_region_name}.amazonaws.com/{key}"
   return output

import httpx
async def function_resend_send_email(config_resend_url,config_resend_key,email_from,email_to_list,title,body):
   payload={"from":email_from,"to":email_to_list,"subject":title,"html":body}
   headers={"Authorization":f"Bearer {config_resend_key}","Content-Type": "application/json"}
   async with httpx.AsyncClient() as client:
      output=await client.post(config_resend_url,json=payload,headers=headers)
   if output.status_code!=200:raise Exception(f"{output.text}")
   return None

import requests
async def function_fast2sms_send_otp_mobile(config_fast2sms_url,config_fast2sms_key,mobile,otp):
   response=requests.get(config_fast2sms_url,params={"authorization":config_fast2sms_key,"numbers":mobile,"variables_values":otp,"route":"otp"})
   output=response.json()
   if output.get("return") is not True:raise Exception(f"{output.get('message')}")
   return output

from openai import OpenAI
def function_openai_client_read(config_openai_key):
   client_openai=OpenAI(api_key=config_openai_key)
   return client_openai

async def function_openai_prompt(client_openai,model,prompt,is_web_search,previous_response_id):
   if not client_openai or not model or not prompt:raise Exception("param missing")
   params={"model":model,"input":prompt}
   if is_web_search==1:params["tools"]=[{"type":"web_search"}]
   if previous_response_id:params["previous_response_id"]=previous_response_id
   output=client_openai.responses.create(**params)
   return output

import base64
async def function_openai_ocr(client_openai,model,file,prompt):
   contents=await file.read()
   b64_image=base64.b64encode(contents).decode("utf-8")
   output=client_openai.responses.create(model=model,input=[{"role":"user","content":[{"type":"input_text","text":prompt},{"type":"input_image","image_url":f"data:image/png;base64,{b64_image}"},],}],)
   return output

import os, json, requests
def function_export_grafana_dashboard(host, username, password, max_limit, output_path="export_grafana"):
    session = requests.Session()
    session.auth = (username, password)
    def sanitize(name):return "".join(c if c.isalnum() or c in " _-()" else "_" for c in name)
    def ensure_dir(path):os.makedirs(path, exist_ok=True)
    def get_organizations():
        r = session.get(f"{host}/api/orgs")
        r.raise_for_status()
        return r.json()
    def switch_org(org_id):return session.post(f"{host}/api/user/using/{org_id}").status_code == 200
    def get_dashboards(org_id):
        headers = {"X-Grafana-Org-Id": str(org_id)}
        r = session.get(f"{host}/api/search?type=dash-db&limit={max_limit}", headers=headers)
        if r.status_code == 422:
            return []
        r.raise_for_status()
        return r.json()
    def get_dashboard_json(uid):
        r = session.get(f"{host}/api/dashboards/uid/{uid}")
        r.raise_for_status()
        return r.json()
    def export_dashboard(org_name, folder_name, dashboard_meta):
        uid = dashboard_meta["uid"]
        data = get_dashboard_json(uid)
        dashboard_only = data["dashboard"]
        path = os.path.join(output_path, sanitize(org_name), sanitize(folder_name or "General"))
        ensure_dir(path)
        file_path = os.path.join(path, f"{sanitize(dashboard_meta['title'])}.json")
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(dashboard_only, f, indent=2)
        print(f"✅ {org_name}/{folder_name}/{dashboard_meta['title']}")
    try:
        orgs = get_organizations()
    except Exception as e:
        print("❌ Failed to get organizations:", e)
        return
    for org in orgs:
        if not switch_org(org["id"]):
            continue
        try:
            dashboards = get_dashboards(org["id"])
        except Exception as e:
            print("❌ Failed to get dashboards:", e)
            continue
        for dash in dashboards:
            try:
                export_dashboard(org["name"], dash.get("folderTitle", "General"), dash)
            except Exception as e:
                print("❌ Failed to export", dash.get("title"), ":", e)
    print(f"Saved to: {output_path}")
    return None

from jira import JIRA
import pandas as pd
from datetime import date
import calendar
def function_export_jira_worklog(jira_base_url, jira_email, jira_token, start_date=None, end_date=None, output_path="export_jira_worklog.csv"):
    today = date.today()
    if not start_date:
        start_date = today.replace(day=1).strftime("%Y-%m-%d")
    if not end_date:
        last_day = calendar.monthrange(today.year, today.month)[1]
        end_date = today.replace(day=last_day).strftime("%Y-%m-%d")
    jira = JIRA(server=jira_base_url, basic_auth=(jira_email, jira_token))
    issues = jira.search_issues(f"worklogDate >= {start_date} AND worklogDate <= {end_date}", maxResults=False, expand="worklog")
    data, assignees = [], set()
    for i in issues:
        if i.fields.assignee:
            assignees.add(i.fields.assignee.displayName)
        for wl in i.fields.worklog.worklogs:
            wl_date = wl.started[:10]
            if start_date <= wl_date <= end_date:
                data.append((wl.author.displayName, wl_date, wl.timeSpentSeconds / 3600))
    df = pd.DataFrame(data, columns=["author","date","hours"])
    df_pivot = df.pivot_table(index="author", columns="date", values="hours", aggfunc="sum", fill_value=0)
    df_pivot = df_pivot.reindex(assignees, fill_value=0).round(0).astype(int)
    df_pivot.to_csv(output_path)
    return f"saved to {output_path}"

import requests, csv
from requests.auth import HTTPBasicAuth
def function_export_jira_filter_count(jira_base_url, jira_email, jira_token, output_path="export_jira_filter_count.csv"):
    auth = HTTPBasicAuth(jira_email, jira_token)
    headers = {"Accept": "application/json"}
    resp = requests.get(f"{jira_base_url}/rest/api/3/filter/my", headers=headers, auth=auth, params={"maxResults": 1000})
    if resp.status_code != 200:
        return f"error {resp.status_code}: {resp.text}"
    data = resp.json()
    filters = sorted(data, key=lambda x: x.get("name", "").lower())
    with open(output_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["filter_name", "issue_count"])
        for flt in filters:
            jql_url = f"{jira_base_url}/rest/api/3/search"
            jql_params = {"jql": flt.get("jql", ""), "maxResults": 0}
            jql_resp = requests.get(jql_url, headers=headers, auth=auth, params=jql_params)
            count = jql_resp.json().get("total", 0) if jql_resp.status_code == 200 else f"error {jql_resp.status_code}"
            writer.writerow([flt.get("name", ""), count])
    return f"saved to {output_path}"

import requests, datetime, re
from collections import defaultdict, Counter
from openai import OpenAI
def function_export_jira_summary(jira_base_url,jira_email,jira_token,jira_project_key_list,jira_max_issues_per_status,openai_key,output_path="export_jira_summary.txt"):
    client = OpenAI(api_key=openai_key)
    headers = {"Accept": "application/json"}
    auth = (jira_email, jira_token)
    def fetch_issues(jql):
        url = f"{jira_base_url}/rest/api/3/search"
        params = {
            "jql": jql,
            "fields": "summary,project,duedate,assignee,worklog,issuetype,parent,resolutiondate,updated",
            "maxResults": jira_max_issues_per_status
        }
        r = requests.get(url, headers=headers, params=params, auth=auth)
        r.raise_for_status()
        return r.json().get("issues", [])
    def fetch_comments(issue_key):
      url = f"{jira_base_url}/rest/api/3/issue/{issue_key}/comment"
      r = requests.get(url, headers=headers, auth=auth)
      r.raise_for_status()
      comments_data = r.json().get("comments", [])
      comment_texts = []
      for c in comments_data:
         try:
               content = c["body"].get("content", [])
               if content and "content" in content[0]:
                  text = content[0]["content"][0].get("text", "")
                  comment_texts.append(text)
         except (KeyError, IndexError, TypeError):
               continue
      return comment_texts
    def group_by_project(issues):
        grouped = defaultdict(list)
        for i in issues:
            name = i["fields"]["project"]["name"]
            grouped[name].append(i)
        return grouped
    def summarize_with_ai(prompt):
        try:
            res = client.chat.completions.create(
                model="gpt-4-0125-preview",
                messages=[{"role": "user", "content": prompt}]
            )
            lines = res.choices[0].message.content.strip().split("\n")
            return [l.strip("-•* \n") for l in lines if l.strip()]
        except Exception as e:
            return [f"AI summary failed: {e}"]
    def build_prompt(issues_by_project, status_label):
        report, seen = [], set()
        now = datetime.datetime.now()
        for project, issues in issues_by_project.items():
            for i in issues:
                f = i["fields"]
                title = f.get("summary", "").strip()
                if title in seen:
                    continue
                seen.add(title)
                comments = fetch_comments(i["key"])
                last_comment = comments[-1][:100] if comments else ""
                updated_days_ago = "N/A"
                try:
                    updated_field = f.get("updated")
                    if updated_field:
                        updated_dt = datetime.datetime.strptime(updated_field[:10], "%Y-%m-%d")
                        updated_days_ago = (now - updated_dt).days
                except:
                    pass
                time_spent = sum(w.get("timeSpentSeconds", 0) for w in f.get("worklog", {}).get("worklogs", [])) // 3600
                line = f"{project} - {title}. Comment: {last_comment}. Hours: {time_spent}. Last Updated: {updated_days_ago}d ago. [{status_label}]"
                report.append(line.strip())
        return "\n".join(report)
    def calculate_activity_and_performance(issues_done):
        activity_counter = Counter()
        on_time_closures = defaultdict(list)
        for issue in issues_done:
            f = issue["fields"]
            assignee = f["assignee"]["displayName"] if f.get("assignee") else "Unassigned"
            comments = fetch_comments(issue["key"])
            worklogs = f.get("worklog", {}).get("worklogs", [])
            activity_counter[assignee] += len(comments) + len(worklogs)
            if f.get("duedate") and f.get("resolutiondate"):
                try:
                    due = datetime.datetime.strptime(f["duedate"], "%Y-%m-%d")
                    resolved = datetime.datetime.strptime(f["resolutiondate"][:10], "%Y-%m-%d")
                    if resolved <= due:
                        on_time_closures[assignee].append(issue["key"])
                except:
                    continue
        top_active = activity_counter.most_common(3)
        best_ontime = sorted(on_time_closures.items(), key=lambda x: len(x[1]), reverse=True)[:3]
        return top_active, best_ontime
    def clean_lines(lines, include_project=False):
        cleaned = []
        for line in lines:
            if len(line.split()) < 3:
                continue
            if include_project and "-" not in line:
                continue
            line = re.sub(r"[^\w\s\-.,/()]", "", line).strip()
            line = re.sub(r'\s+', ' ', line)
            cleaned.append(f"- {line}")
        return cleaned
    def save_summary_to_file(blockers, improvements, top_active, on_time, filename=output_path):
        def numbered(lines):
            return [f"{i+1}. {line}" for i, line in enumerate(lines)]
        with open(filename, "w", encoding="utf-8") as f:
            f.write("Key Blockers\n")
            for line in numbered(clean_lines(blockers, include_project=True)):
                f.write(f"{line}\n")
            f.write("\nSuggested Improvements\n")
            for line in numbered(clean_lines(improvements)):
                f.write(f"{line}\n")
            f.write("\nTop 3 Active Assignees\n")
            for i, (name, count) in enumerate(top_active, 1):
                f.write(f"{i}. {name} ({count} updates)\n")
            f.write("\nBest On-Time Assignees\n")
            for i, (name, items) in enumerate(on_time, 1):
                f.write(f"{i}. {name} - {len(items)} issues closed on or before due date\n")
    issues_todo, issues_inprog, issues_done = [], [], []
    for key in jira_project_key_list:
        issues_todo += fetch_issues(f'project = {key} AND statusCategory = "To Do" ORDER BY updated DESC')
        issues_inprog += fetch_issues(f'project = {key} AND statusCategory = "In Progress" ORDER BY updated DESC')
        issues_done += fetch_issues(f'project = {key} AND statusCategory = "Done" ORDER BY resolutiondate DESC')
    todo_grouped = group_by_project(issues_todo)
    inprog_grouped = group_by_project(issues_inprog)
    done_grouped = group_by_project(issues_done)
    all_prompt_text = (
        build_prompt(todo_grouped, "To Do") + "\n" +
        build_prompt(inprog_grouped, "In Progress") + "\n" +
        build_prompt(done_grouped, "Done")
    )
    prompt_blockers = (
        "From the Jira issues below, list actual blockers that can delay progress. "
        "Each line must begin with the project name. Be specific and short. Max 100 characters per bullet."
    )
    prompt_improvement = (
        "You are a Jira productivity assistant. Based on the following Jira issue summaries, "
        "give exactly 5 specific, actionable process improvements to improve execution quality and velocity. "
        "Each point should be a short bullet (one line, max 100 characters). "
        "Return only the 5 bullet points. Do not include any introduction, summary, explanation, or heading."
    )
    blockers = summarize_with_ai(prompt_blockers + "\n" + all_prompt_text)
    improvements = summarize_with_ai(prompt_improvement + "\n" + all_prompt_text)
    top_active, on_time = calculate_activity_and_performance(issues_done)
    save_summary_to_file(blockers, improvements, top_active, on_time)
    return f"saved to {output_path}"