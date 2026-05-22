# S3 TUI API — machine spec (the model reads this)

API slug: `sg-aws.s3` · tool: `sg-aws` · tier: `READ_ONLY` · scope: `sg-aws.s3:read`

## Actions

### list_buckets
List all buckets. No params.
Returns `{ result: [ { name, creation_date, region, versioning } ] }`.

### list_objects
List objects under a bucket. Params:
- `bucket` (string, **required**) — the bucket name.
- `prefix` (string, optional) — key prefix; default `''` (root).
- `recursive` (boolean, optional) — default `false`; when `false`, common prefixes
  (folders) are returned separately and the listing is one level deep.
Returns `{ result: { bucket, prefix, objects: [ { key, size, last_modified, etag,
storage_class } ], prefixes: [ ... ] } }`.

### head_object
Stat a single object. Params:
- `bucket` (string, **required**).
- `key` (string, **required**) — full object key.
Returns `{ result: { key, size, etag, content_type, storage_class, ... } }`, or
`{ result: {} }` if the object does not exist.

## Notes
- All actions are idempotent and never mutate.
- Errors return `{ ok: false, error: "<Type>: <message>" }` (e.g. missing/denied bucket).
- Input is validated against each action's JSON Schema before dispatch.
