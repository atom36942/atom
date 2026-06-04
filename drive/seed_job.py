# import stdlib
import asyncio
import random

# import packages
import asyncpg

# import internal
from config import config_postgres_url

# logic
async def execute():
    db_url = config_postgres_url
    if not db_url:
        print("Error: 'config_postgres_url' is not set in environment or config.")
        return
    print("Connecting to database...")
    try:
        conn = await asyncpg.connect(db_url)
    except Exception as e:
        print(f"Failed to connect: {e}")
        return
    try:
        num_records = 1000
        print(f"Inserting {num_records} records into 'test' table...")
        for i in range(1, num_records + 1):
            test_id = await conn.fetchval(
                'INSERT INTO test (created_by_id, updated_by_id, views, type, title, code, slug, email, tag, tag_int, rating, price, "Price (USD)", coordinate, status, metadata) VALUES (1, 1, $1, 1, $2, $3, $4, $5, ARRAY[\'tag1\', \'tag2\', \'tag3\']::text[], ARRAY[1, 2, 3]::integer[], $6, $7, $8, ST_SetSRID(ST_MakePoint($9, $10), 4326)::geography, $11, \'{"active": true, "bool": true}\'::jsonb) RETURNING id', 
                random.randint(55, 200),
                f"A Great Title for Testing {i}",
                f"CODE_{random.randint(1000, 9999)}_{i}",
                f"slug-test-{i}",
                f"tester_{i}@example.com",
                round(random.uniform(1.1, 4.9), 1),
                round(random.uniform(10.0, 999.0), 2),
                round(random.uniform(100.0, 999.0), 2),
                80.0 + random.uniform(-0.01, 0.01),
                15.0 + random.uniform(-0.01, 0.01),
                random.choice([1, 2, 3])
            )
            await conn.execute('INSERT INTO action_test_comment (test_id, description, created_by_id) VALUES ($1, $2, 1)', test_id, f"Comment for test {test_id}")
            await conn.execute('INSERT INTO action_test_report (test_id, description, created_by_id) VALUES ($1, $2, 1)', test_id, f"Report for test {test_id}")
            await conn.execute('INSERT INTO action_test_feedback (test_id, description, rating, created_by_id) VALUES ($1, $2, $3, 1)', test_id, f"Feedback for test {test_id}", round(random.uniform(1.0, 5.0), 1))
            if i % 100 == 0:
                print(f" - Processed {i}/{num_records} records... (Latest test_id: {test_id})")
        print("\nAll data seeded successfully!")
    except Exception as e:
        print(f"Error while inserting data: {e}")
    finally:
        await conn.close()

# init
if __name__ == "__main__":
    asyncio.run(execute())
