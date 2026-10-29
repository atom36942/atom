# Security audit: SQL, storage, and credential handling

Reviewed local source and reachable Git history on 2026-09-23. No configured
database, storage account, or external telemetry service was contacted. Severity
below reflects the code's default access policies, not a verified deployment.

## Confirmed findings and changes

| Severity | Finding | Change |
|----------|---------|--------|
| High | Any authenticated user could mint a container-wide Azure read SAS through `/admin/blob-container-sas`. | The handler checks the caller's current database role and requires role `1`; the default route policy also requires it. |
| High | Private blob previews signed arbitrary object keys without checking the caller's ownership prefix. | The route passes the authenticated user ID; S3 and Azure signing reject keys outside that user's `user_<id>/` prefix. This intentionally prevents cross-user and public-prefix previews through this endpoint. |
| Medium | MSSQL read/export runners accepted permission-changing batches such as a SELECT followed by GRANT. | Both paths use a shared conservative guard rejecting batches and permission, administration, and external-provider commands before acquiring a connection. |
| Medium | Uploads read the complete file into application memory before checking size. | Reads are bounded to the configured limit plus one byte; oversized files are rejected before upload. Multipart parsing/ingress limits remain separate. |
| Medium | API logs stored credential-bearing query parameters verbatim; database/client exception messages could disclose connection or query details. | Sensitive query keys and opaque payload fields are redacted, PostgreSQL/HTTP transport errors use generic messages, and recognizable credentials are scrubbed from other response and console messages. |
| Medium | Relation joins allowed restricted columns as join keys; the relation helper did not honor a wildcard table block. | Restricted source/target join columns and wildcard-blocked target tables are rejected before querying. |

Additional hardening: ClickHouse read/export calls request `readonly=1` and a
30-second execution limit. Upload extensions are restricted to short alphanumeric
suffixes, and signed-upload counts must be positive integers. S3 signing now awaits
the asynchronous client methods, fixing the existing coroutine-return bug.

## Protections checked

- PostgreSQL read runners already use read-only transactions, statement timeouts,
  and bounded results. This behavior is preserved and covered by regression tests.
- Default admin SQL runners require authenticated role `1`. Atom's startup config
  check requires explicit configuration for registered routes. Custom config can
  still change access policies.
- CRUD filter values use bound parameters; regression tests verify that sample
  SQL payloads remain parameter values rather than being inserted into query text.
  This is not an exhaustive proof for every SQL-building path.
- Blob “upload URL” endpoints mint cloud upload credentials; they do not download
  a user-supplied URL, so no server-side URL-fetch SSRF path was found there.
- Current tracked files and 6,978 reachable historical blobs were scanned for
  private-key markers, AWS access-key IDs, and selected GitHub/OpenAI token
  formats. No matches were found. No nonempty credential-like string assignments
  were found in tracked non-test Python source. This limited pattern scan cannot
  rule out every secret format; local `.env` values were not displayed or tested.

## Remaining limits and deployment checks

- MSSQL keyword checks are not a database authorization boundary and can reject
  legitimate literals containing blocked words. Use a database login with only
  the necessary read permissions for read-only access; this audit did not inspect
  deployed grants or add a separate read pool. MSSQL server-side query timeouts
  remain a deployment/client configuration concern.
- ClickHouse and PostgreSQL read-only execution do not replace least-privilege
  database grants. Query settings can interact with server settings profiles;
  verify them against the deployed server. See the official
  [ClickHouse permissions documentation](https://clickhouse.com/docs/concepts/features/configuration/settings/permissions-for-queries)
  and [PostgreSQL transaction restrictions](https://www.postgresql.org/docs/17/sql-set-transaction.html).
- Blob access uses the framework's key-prefix ownership convention, not a database
  ownership lookup. Restrict cloud credentials to intended buckets/containers;
  do not share those credentials across unrelated applications. Generic blob
  helpers do not perform malware or content-type validation. Azure direct-upload
  SAS does not enforce Atom's application upload-size limit.
- `/pgweb` relies on a localhost check. Keep it behind an appropriate network
  boundary; a local reverse proxy can affect the apparent peer address. Proxy
  configuration and browser-origin policy were not validated in this review.
- Sentry still receives original exceptions when enabled. Review telemetry
  scrubbing and retention separately. Redaction is not a guarantee that arbitrary
  custom exception text or unfamiliar credential names contain no sensitive data.
- Existing logs and already-issued signed URLs are unchanged by these fixes.

## Verification

`venv/bin/python -m unittest discover -s tests -v` passes all 64 tests, including
13 security regression tests. Application import registers 151 functions and 78
routes. Git whitespace checks pass. Database and cloud calls are mocked; no live
SQL execution, HTTP penetration testing, or cloud-policy validation was performed.
