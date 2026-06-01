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
