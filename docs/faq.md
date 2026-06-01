# Frequently Asked Questions (FAQ)

---

### Q: What is the use of the `is_background` parameter?

**A:** Passing `is_background=1` as a query parameter tells the application to process the API request asynchronously in the background. The server immediately returns a generic response, freeing up the client while the actual heavy operation runs silently. 

**Example:**
- **Synchronous:** `POST /my/message-delete-bulk?mode=all`
- **Background:** `POST /my/message-delete-bulk?mode=all&is_background=1`

---

### Q: What is the use of the `is_disable_cache` parameter?

**A:** Passing `is_disable_cache=1` as a query parameter forces the application to bypass any cached responses for that API endpoint. Instead of returning a stored response, the server executes the full API logic (e.g., querying the database fresh). This is extremely useful when you need real-time data or want to ensure you aren't seeing stale cached content.

**Example:**
- **Cached (Default behavior):** `GET /public/object-read` (May return a cached response if recently requested)
- **Bypass Cache:** `GET /public/object-read?is_disable_cache=1` (Always fetches fresh data from the database)

---

### Q: How do I filter records in `object-read` APIs?

**A:** You can use the `filter` parameter to apply dynamic, SQL-like conditions. It accepts a JSON-stringified array of condition strings. The framework automatically parses these and safely converts them into the underlying database queries.

**Syntax Examples:**
- **Equality/Inequality:** `"status = 1"`, `"type neq 9"`
- **Comparisons:** `"views > 10"`, `"rating < 5"`, `"price lte 1000"`
- **Null Checks:** `"deleted_at is null"`, `"updated_by_id is distinct from null"`
- **Pattern Matching:** `"title ilike %Test%"`, `"code ~ ^CODE_"` (Regex)
- **Lists & Ranges:** `"status in 1|2|3"`, `"rating between 1|5"`
- **Array/JSON Operations:** `"tag contains tag1"`, `"metadata exists active"`

**Usage:**
```json
"filter": ["status = 1", "views > 10", "title ilike %Test%"]
```

---

### Q: How does the `relation` parameter work for fetching joined data?

**A:** The `relation` parameter allows you to perform highly efficient, declarative SQL joins to fetch related data or perform aggregations from other tables in a single API call. It accepts an array of formatted strings.

**Syntax Format:**
`"local_col, target_table, target_col, action|limit, return_fields"`

**Examples:**
- **Fetch specific fields from a related table:** 
  `"created_by_id,users,id,fetch|1,username,name,email"`
  *(Joins the `users` table where `users.id = created_by_id`, fetches 1 record, and returns only the username, name, and email).*

- **Perform aggregations on a related table:**
  `"id,action_test_report,test_id,count,*"`
  *(Counts all records in `action_test_report` where `test_id = id`).*
  You can also use `sum`, `avg`, `min`, and `max` (e.g., `"id,action_test_feedback,test_id,avg,rating"`).

---

### Q: How do I enable caching for a specific API endpoint?

**A:** You can enable caching for an API by defining the `"api_cache_sec"` key for the endpoint in the `config_api` dictionary inside `core/config.py`. It accepts a list where the first item is the cache storage mode (`"inmemory"` or `"redis"`) and the second item is the TTL (Time-To-Live) in seconds.

**Examples:**
```python
config_api = {
    # Mode: inmemory (Uses local RAM, extremely fast but doesn't share across multiple server instances)
    "/public/object-read": {"id": 14, "api_cache_sec": ["inmemory", 100]},
    
    # Mode: redis (Uses external Redis server, best for distributed caching across instances)
    "/info": {"id": 17, "api_cache_sec": ["redis", 300]}
}
```

---

### Q: How do I enable rate limiting for a specific API endpoint?

**A:** Rate limiting is configured similarly using the `"api_ratelimiting_times_sec"` key in `config_api`. It accepts a list containing the storage mode (`"inmemory"` or `"redis"`), the maximum number of allowed requests, and the time window in seconds.

**Examples:**
```python
config_api = {
    # Mode: inmemory (Tracks limits locally per server instance)
    "/public/export": {"id": 19, "api_ratelimiting_times_sec": ["inmemory", 10, 60]},
    
    # Mode: redis (Tracks limits globally across all server instances)
    "/public/heavy-task": {"id": 20, "api_ratelimiting_times_sec": ["redis", 5, 60]}
}
```

---

