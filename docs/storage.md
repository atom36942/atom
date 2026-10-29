# Blob storage: uploads, previews, SAS, and deletion

Atom supports AWS S3 (`service=s3`) and Azure Blob Storage (`service=azure`). This
guide describes the implemented routes and default settings. Examples use fake
URLs, signatures, and user ID `7`; replace them with your own values.

## Concepts

| Term | Meaning in Atom |
|------|-----------------|
| Blob/object | The stored file bytes. |
| Container/bucket | Azure calls it a container; S3 calls it a bucket. Both use the API parameter `container`. |
| Object key | The path within that container, such as `user_7/<uuid>.jpg`. |
| `file_url` | The stored object address without temporary authorization. It remains usable as an identifier while the object exists, but does not make a private object readable. |
| `upload_url` | Temporary cloud endpoint/credentials for uploading bytes. It is not a preview link. |
| Preview URL | Temporary signed read link for one object. Use it in the UI; request a new one after expiry. |
| SAS | Azure Shared Access Signature: permissions and expiry encoded in a signed query string. Blob SAS covers one blob; container SAS covers a container. |

Store `file_url` and `service` in application data. Treat signed URLs and SAS tokens
as temporary bearer credentials: anyone possessing them can perform the permitted
operation until they expire. A `public/` key prefix does not itself make a file
public; cloud permissions determine that.

## Setup and defaults

| Service | Configuration |
|---------|---------------|
| S3 | `config_aws_s3_region_name`, `config_aws_access_key_id`, `config_aws_secret_access_key` |
| Azure | `config_azure_account_name`, `config_azure_account_key` |
| Both upload methods | PostgreSQL and the `blob` table must be initialized for metadata recording. |

Keep credentials in your environment or secret management system. The built-in
S3 client uses AWS endpoints. MinIO/custom S3 endpoints require custom client and
URL construction; there is no built-in endpoint configuration in this code.

| Setting | Default | Applies to |
|---------|---------|------------|
| `config_blob_services` | `["s3", "azure"]` | Allowed service choices |
| `config_blob_limit_size_kb` | `500` | Server uploads and S3 presigned POST policy; bytes = value × 1024 |
| `config_blob_limit_upload` | `100` | Files per server-upload request / signed upload slots |
| `config_blob_expire_sec_upload` | `3600` (1 hour) | Upload authorization |
| `config_blob_expire_sec_preview` | `360000` (100 hours) | Preview authorization and container SAS |

Configured expiry is the requested lifetime; provider credentials and policies
can shorten it. Browser uploads need CORS configured on the cloud bucket/container
for the UI origin and the relevant methods/headers. Atom's API CORS settings do
not configure storage CORS.

## Endpoint map

Authenticated calls use `Authorization: Bearer <access_token>`. Defaults below
come from `config_api`; project configuration may further restrict access.

| Method and endpoint | Purpose | Access |
|---------------------|---------|--------|
| `POST /private/blob-upload-file` | Upload bytes through Atom | Logged-in user |
| `POST /private/blob-upload-presigned` | Obtain direct cloud upload credentials | Logged-in user |
| `POST /public/blob-upload-file` | Public variant of server upload | Disabled by default |
| `POST /public/blob-upload-presigned` | Public variant of signed upload | Disabled by default |
| `POST /my/blob-preview-urls` | Preview the caller's files | Own key prefix |
| `POST /admin/blob-preview-urls` | Preview files across users | Current database role `1` |
| `POST /admin/blob-container-sas` | Azure container-wide read token | Current database role `1` |
| `POST /my/blob-delete-url` | Delete specified owned objects | Own key prefix |
| `POST /my/blob-delete-all` | Delete a batch of the caller's recorded files | Authenticated user |
| `POST /admin/blob-delete-url` | Delete specified objects across users | Admin role `1` |
| `GET /admin/blob-container-read` | List buckets/containers | Admin role `1` |
| `POST /admin/blob-container-ops` | Create, make public, empty, or delete a container | Admin role `1` |

## File naming and ownership

Server uploads use `user_<id>/<uuid>.<extension>` for authenticated users. The UUID
is random; the extension is a short alphanumeric suffix, otherwise `bin`.
Presigned uploads use `user_<id>/<uuid>.bin`; this does not convert the file bytes.

```text
S3:    https://<bucket>.s3.<region>.amazonaws.com/user_7/<uuid>.jpg
Azure: https://<account>.blob.core.windows.net/<container>/user_7/<uuid>.jpg
```

Enabled public upload routes use `public/<uuid>...` when there is no authenticated
user. If a valid token is supplied, they use that user's `user_<id>/` prefix.
The private upload routes always take the user ID from the token, never the body.

`/my/` preview and URL deletion use key-prefix ownership, not a `blob` table
ownership lookup. `/my/` previews reject other users' and `public/` files, even
for an admin caller. Admins use `/admin/blob-preview-urls` for those files.

## Upload bytes through Atom

`POST /private/blob-upload-file` accepts multipart form fields:

| Field | Required | Meaning |
|-------|----------|---------|
| `service` | Yes | `s3` or `azure` |
| `container` | Yes | Destination bucket/container name |
| `file` | Yes | File field; repeat it for multiple files |

```bash
curl -X POST 'http://localhost:8000/private/blob-upload-file' \
  -H 'Authorization: Bearer <access_token>' \
  -F 'service=s3' -F 'container=my-bucket' \
  -F 'file=@./photo.jpg' -F 'file=@./invoice.pdf'
```

Success maps original filenames to stored file URLs:

```json
{
  "status": 1,
  "message": {
    "photo.jpg": "https://my-bucket.s3.ap-south-1.amazonaws.com/user_7/<uuid1>.jpg",
    "invoice.pdf": "https://my-bucket.s3.ap-south-1.amazonaws.com/user_7/<uuid2>.pdf"
  }
}
```

Use distinct filenames within a batch: duplicate names overwrite one another in
this response dictionary even though both uploads can occur. The server reads at
most the size limit plus one byte per file into application memory. Multipart
parsing happens earlier, so ingress request-body limits still matter. Uploads and
metadata writes are not one atomic transaction; a later failure can leave earlier
objects uploaded. Atom does not perform malware scanning or verify content type.

The public variant accepts the same fields and response shape when enabled.

## Upload directly from the browser to storage

First obtain upload credentials:

```bash
curl -X POST \
  'http://localhost:8000/private/blob-upload-presigned?service=s3&container=my-bucket&count=2' \
  -H 'Authorization: Bearer <access_token>'
```

`service` and `container` are required query parameters. `count` is an optional
positive integer, defaults to `1`, and cannot exceed `config_blob_limit_upload`.
No request body is needed. Creating credentials does not upload a file.

### S3: multipart POST

The response contains one object per upload slot. S3 signing fields are flattened
into each object, not nested under `fields`. Example fields are illustrative;
forward the actual returned fields because they vary with credentials/signing:

```json
{
  "status": 1,
  "message": [
    {
      "upload_url": "https://my-bucket.s3.amazonaws.com/",
      "key": "user_7/<uuid>.bin",
      "policy": "...",
      "x-amz-algorithm": "AWS4-HMAC-SHA256",
      "x-amz-credential": "...",
      "x-amz-date": "...",
      "x-amz-signature": "...",
      "file_url": "https://my-bucket.s3.ap-south-1.amazonaws.com/user_7/<uuid>.bin"
    }
  ]
}
```

```javascript
const { upload_url, file_url, ...fields } = response.message[0];
const form = new FormData();
for (const [key, value] of Object.entries(fields)) form.append(key, value);
form.append("file", selectedFile); // File must be the last form field.
const uploaded = await fetch(upload_url, { method: "POST", body: form });
if (!uploaded.ok) throw new Error("Cloud upload failed");
// Save/use file_url after cloud upload succeeds.
```

Do not send Atom's Bearer token to S3, and let the browser set the multipart
Content-Type boundary. The signed policy enforces 1 byte through the configured
maximum. This is S3's [presigned POST flow](https://docs.aws.amazon.com/botocore/latest/reference/services/s3/client/generate_presigned_post.html);
AWS requires the [file field last](https://docs.aws.amazon.com/AmazonS3/latest/developerguide/RESTObjectPOST.html).

### Azure: PUT to the blob SAS URL

Use the same Atom request with `service=azure`. Its response shape is:

```json
{
  "status": 1,
  "message": [
    {
      "upload_url": "https://account.blob.core.windows.net/documents/user_7/<uuid>.bin?sv=...&sp=...&sig=...",
      "key": "user_7/<uuid>.bin",
      "file_url": "https://account.blob.core.windows.net/documents/user_7/<uuid>.bin"
    }
  ]
}
```

```javascript
const { upload_url, file_url } = response.message[0];
const uploaded = await fetch(upload_url, {
  method: "PUT",
  headers: { "x-ms-blob-type": "BlockBlob" },
  body: selectedFile
});
if (!uploaded.ok) throw new Error("Cloud upload failed");
```

Azure's [Put Blob API](https://learn.microsoft.com/en-us/rest/api/storageservices/put-blob)
requires the blob-type header. The SAS grants create/write access to the generated
blob, not a preview permission. Atom's file-size check does not apply to this
cloud-direct path; use server uploads when that application limit must be enforced.

The public signed-upload endpoint has the same service-specific response formats
when enabled. Uploaded content metadata affects whether browsers display or
download a file; Atom does not guarantee inline rendering from a signed URL alone.

## Preview files in the UI

Use `POST /my/blob-preview-urls` for a user's own files, or
`POST /admin/blob-preview-urls` for any file accessible to Atom's storage credentials.
The admin handler checks role `1` against the database, so stale admin token claims
are insufficient. Both services use the same API shape.

Headers: `Authorization: Bearer <access_token>` and `Content-Type: application/json`.
Required body fields are `service` and `urls` (a list of stored file URLs). No query
parameters or caller-supplied user ID are needed. One service per request.

```json
{
  "service": "s3",
  "urls": [
    "https://my-bucket.s3.ap-south-1.amazonaws.com/user_7/photo.jpg",
    "https://my-bucket.s3.ap-south-1.amazonaws.com/user_7/invoice.pdf"
  ]
}
```

Response, with shortened illustrative signatures:

```json
{
  "status": 1,
  "message": [
    "https://my-bucket.s3.ap-south-1.amazonaws.com/user_7/photo.jpg?X-Amz-Signature=...",
    "https://my-bucket.s3.ap-south-1.amazonaws.com/user_7/invoice.pdf?X-Amz-Signature=..."
  ]
}
```

`message[i]` corresponds to request `urls[i]`. Order and duplicates are preserved;
invalid or unauthorized entries fail the whole request rather than being skipped.
Signing does not verify that the object exists. To display an image or link:

```javascript
image.src = response.message[0];
downloadLink.href = response.message[1];
```

For mixed-service lists, group requests by service and retain their original UI
indexes. Refresh expired preview links using stored file URLs. Do not replace
stored file URLs with signed URLs. A signed read URL grants access to the object
bytes; it does not transform a document into an image preview.

## Azure container SAS for admins

`POST /admin/blob-container-sas` is for container-wide read access, not ordinary
single-file previews. It requires current database role `1`.

| Query parameter | Required | Value |
|-----------------|----------|-------|
| `service` | Yes | `azure`; S3 is rejected |
| `container` | Yes | Azure container name |

```bash
curl -X POST \
  'http://localhost:8000/admin/blob-container-sas?service=azure&container=documents' \
  -H 'Authorization: Bearer <access_token>'
```

No body is required. Response:

```json
{
  "status": 1,
  "message": {
    "sas_token": "sv=...&sp=r&se=...&sig=...",
    "expiry_sec": 360000
  }
}
```

Append this token to a blob's URL in that container:

```text
https://account.blob.core.windows.net/documents/user_8/file.pdf?<sas_token>
```

It permits reading blobs, including other users' files, but not listing,
uploading, or deleting them. `expiry_sec` uses `config_blob_expire_sec_preview`.
There is no equivalent container SAS endpoint for S3; use per-object admin preview
URLs for both providers.

## Metadata and finding uploaded files

Atom records uploads in PostgreSQL's `blob` table:

| Column | Meaning |
|--------|---------|
| `id` | Metadata row ID |
| `created_at`, `created_by_id` | Creation time and user ID; anonymous uploads have no owner |
| `service` | Storage provider |
| `type` | `1` for server upload; `2` for issued direct-upload credentials |
| `file_url` | Stored object URL |
| `deleted_at`, `deleted_by_id` | Cleanup markers |

Type `2` rows are recorded when credentials are issued, before browser upload.
Their existence does not prove that bytes reached storage. There is no upload
completion verification endpoint in the current implementation.

Subject to your table policies, list your metadata using:

```text
GET /my/object-read?table=blob&filter=deleted_at%20is%20null&limit=20&page=1
```

The response is `{"status": 1, "message": {"obj_list": [...], "has_more": false,
"has_next_page": false}}`. Use each row's `service` and `file_url` to request
previews. Admins can use `/admin/object-read?table=blob` subject to admin policies.

## Deleting files

`POST /my/blob-delete-url` and `POST /admin/blob-delete-url` take a JSON body:

```json
{
  "service": "s3",
  "url": ["https://my-bucket.s3.ap-south-1.amazonaws.com/user_7/photo.jpg"]
}
```

The field is **`url`**, singular, containing a list; preview requests use `urls`.
At most 500 URLs are accepted per call. The `/my/` helper skips keys outside the
caller's prefix; the admin helper does not apply that prefix restriction.
The success message is `{"status": 1, "message": "1 s3 URLs processed"}`. This
counts submitted URLs, not confirmed deletions. These URL-delete routes do not
mark the corresponding metadata rows deleted.

`POST /my/blob-delete-all` takes no body or query parameters. It processes up to
500 undeleted metadata rows belonging to the caller, deletes their cloud objects,
and marks those rows with deletion fields. Both services are handled from the
recorded metadata:

```json
{
  "status": 1,
  "message": {"deleted_count": 500, "has_more": true, "has_next_page": true}
}
```

Call again while `has_more` is true. The count is processed metadata rows; object
storage failures can interrupt cleanup. Provider retention/versioning rules still
apply to physical deletion.

## Container administration

`GET /admin/blob-container-read?service=s3` returns bucket names; `service=azure`
returns container names. Example: `{"status": 1, "message": ["documents", "images"]}`.

`POST /admin/blob-container-ops?service=azure&container=documents&mode=create`
uses required query parameters `service`, `container`, and `mode`:

| Mode | Effect |
|------|--------|
| `create` | Create the bucket/container |
| `public` | Enable anonymous object-read access where provider policy allows |
| `empty` | Delete objects in the container |
| `delete` | Delete the bucket/container; provider preconditions apply |

All operations require admin access. Results are wrapped in `status`/`message`,
but the message payload varies by provider and operation. These operations do not
synchronize the `blob` metadata table. They are separate from signed previews;
previewing private files does not require making a container public.

## Errors and operational limits

Atom validation failures normally return HTTP 400 with this shape:

```json
{"status": 0, "message": "blob preview allowed only for own files"}
```

Other examples include `file size exceeds 500kb`, `count must be a positive
integer`, `access denied`, and `blob client not initialized`. A signed URL can
also fail later at the cloud provider because of expiry, missing objects,
permissions, or CORS; that response is not Atom's JSON envelope.

Keep cloud grants limited to intended containers. Upload APIs accept a container
name but do not enforce a separate per-user container allowlist. Do not share the
same storage credentials/key namespace across unrelated applications. See the
[security audit](audit.md) for the reviewed protections and remaining limits.

[Back to README](../readme.md)
