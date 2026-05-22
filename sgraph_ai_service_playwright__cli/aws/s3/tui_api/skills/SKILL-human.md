# S3 TUI API — for humans

Read-only access to Amazon S3 from the TUI API. Reach for this when you want to **see**
what's in S3 without leaving the chat/explorer and without shell-ing out to `aws s3`.

It exposes three actions, all `READ_ONLY` (always safe, never mutates):

- **list_buckets** — every bucket in the account.
- **list_objects** — objects under a bucket, optionally filtered by a key prefix.
- **head_object** — the metadata of one object (size, etag, content-type, storage class).

It deliberately does **not** write, copy, or delete — those are a separate, gated tier
(arriving with the execution center). Credentials come from the active `sg credentials`
context, so what you can see is exactly what that identity can see.
