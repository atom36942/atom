import os
import asyncio
import asyncpg
import random

async def main():
    # Try to load from .env file if it exists in the root directory
    env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')
    if os.path.exists(env_path):
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    k, v = line.split('=', 1)
                    if k.strip() == "config_postgres_url":
                        os.environ[k.strip()] = v.strip().strip("'").strip('"')

    db_url = os.environ.get("config_postgres_url")
    if not db_url:
        print("Error: 'config_postgres_url' environment variable is not set.")
        print("Please set it. Example: export config_postgres_url='postgresql://user:pass@localhost:5432/dbname'")
        return
        
    print(f"Connecting to database...")
    try:
        conn = await asyncpg.connect(db_url)
    except Exception as e:
        print(f"Failed to connect: {e}")
        return

    try:
        # We assume User ID=1 already exists as per your guarantee.
        
        # Insert 1000 distinct records into the 'test' table
        num_records = 1000
        print(f"Inserting {num_records} records into 'test' table...")
        
        for i in range(1, num_records + 1):
            test_id = await conn.fetchval("""
                INSERT INTO test (
                    created_by_id,
                    updated_by_id,
                    views,
                    type,
                    title,
                    code,
                    slug,
                    email,
                    tag,
                    tag_int,
                    rating,
                    price,
                    "Price (USD)",
                    coordinate,
                    status,
                    metadata
                ) VALUES (
                    1,
                    1,
                    $1,
                    1,
                    $2,
                    $3,
                    $4,
                    $5,
                    ARRAY['tag1', 'tag2', 'tag3']::text[],
                    ARRAY[1, 2, 3]::integer[],
                    $6,
                    $7,
                    $8,
                    ST_SetSRID(ST_MakePoint($9, $10), 4326)::geography,
                    $11,
                    '{"active": true, "bool": true}'::jsonb
                ) RETURNING id
            """, 
            random.randint(55, 200),  # views > 50
            f"A Great Title for Testing {i}", # title ilike %Title%
            f"CODE_{random.randint(1000, 9999)}_{i}", # code ~ ^CODE_
            f"slug-test-{i}", # slug ~* ^slug-
            f"tester_{i}@example.com", # email ilike %@example.com
            round(random.uniform(1.1, 4.9), 1), # rating between 1 and 5
            round(random.uniform(10.0, 999.0), 2), # price <= 1000
            round(random.uniform(100.0, 999.0), 2), # Price (USD) >= 100
            80.0 + random.uniform(-0.01, 0.01), # Longitude near 80.0
            15.0 + random.uniform(-0.01, 0.01), # Latitude near 15.0
            random.choice([1, 2, 3]) # status in 1|2|3
            )
            
            # Action tables have a unique constraint on (test_id, created_by_id), so we can only insert 1 per user
            await conn.execute("""
                INSERT INTO action_test_comment (test_id, description, created_by_id)
                VALUES ($1, $2, 1)
            """, test_id, f"Comment for test {test_id}")
            
            await conn.execute("""
                INSERT INTO action_test_report (test_id, description, created_by_id)
                VALUES ($1, $2, 1)
            """, test_id, f"Report for test {test_id}")
            
            await conn.execute("""
                INSERT INTO action_test_feedback (test_id, description, rating, created_by_id)
                VALUES ($1, $2, $3, 1)
            """, test_id, f"Feedback for test {test_id}", round(random.uniform(1.0, 5.0), 1))
                
            if i % 100 == 0:
                print(f" - Processed {i}/{num_records} records... (Latest test_id: {test_id})")
        
        print("\nAll data seeded successfully! The curl command will now return plenty of results.")
        
    except Exception as e:
        print(f"Error while inserting data: {e}")
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(main())
