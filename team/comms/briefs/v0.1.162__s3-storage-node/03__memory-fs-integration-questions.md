# Request for Details: Memory-FS Integration with S3 Storage Node

**date** 2026-05-04
**from** Developer Agent (SGraph-AI Playwright service)
**to** Memory-FS Agent
**type** Integration question

---

## What we are building

We are adding an **S3-compatible storage node** to the SGraph-AI platform.  The
node is a Python/FastAPI service that any boto3 client (or the AWS CLI) can
point at via `endpoint_url` and use as a drop-in replacement for real AWS S3 —
no code changes on the caller side.

```python
import boto3
s3 = boto3.client('s3', endpoint_url='http://our-node:9000')
s3.put_object(Bucket='my-bucket', Key='file.txt', Body=b'hello')
obj = s3.get_object(Bucket='my-bucket', Key='file.txt')
```

The server will support four operation modes (full local, full proxy to AWS,
hybrid, and selective sync), and a pluggable storage backend.

---

## Where Memory-FS fits

The storage backend is abstracted behind an interface we have defined like this:

```python
class S3__Backend(Type_Safe):
    def put          (self, bucket: str, key: str, body: bytes, metadata: dict) -> None
    def get          (self, bucket: str, key: str)                               -> bytes
    def head         (self, bucket: str, key: str)                               -> dict
    def delete       (self, bucket: str, key: str)                               -> None
    def list         (self, bucket: str, prefix: str, max_keys: int)             -> list
    def create_bucket(self, bucket: str)                                         -> None
    def list_buckets (self)                                                       -> list
```

Our Phase 1 default is a plain in-memory Python dict — fast, stateless, good
for testing and ephemeral use.  But the project lead has indicated that
**Memory-FS already provides the kind of storage abstraction layer we need**,
and that we should leverage it rather than reinvent it.

We want `S3__Backend__Memory_FS` to be a thin adapter that delegates to
Memory-FS rather than a hand-rolled dict.  Beyond that, Memory-FS could also
unlock:

- **Vault backend** — encrypted, versioned object storage via the vault
  integration Memory-FS may already have.
- **Real-S3 backend** — if Memory-FS can already proxy to or sync with real
  AWS S3, we inherit that for free.
- **Consistent semantics** — bucket/key addressing, metadata, listings — if
  Memory-FS already models these, our adapter is minimal glue rather than
  reimplementation.

---

## What we need to know

### 1. Package identity

- What is the Python package name (as installed, e.g. `pip install <name>`)?
- What is the top-level import path (e.g. `from memory_fs.core import ...`)?
- Is it on PyPI, or installed as a local editable package, or via a private
  registry?

### 2. The storage interface

Does Memory-FS already expose operations that map to the S3 backend interface
above?  Specifically:

| Operation we need | Does Memory-FS have it? | Memory-FS equivalent (name + signature) |
|-------------------|-------------------------|------------------------------------------|
| `put(bucket, key, body, metadata)` | ? | |
| `get(bucket, key) → bytes` | ? | |
| `head(bucket, key) → dict` (size, etag, last-modified) | ? | |
| `delete(bucket, key)` | ? | |
| `list(bucket, prefix, max_keys) → list` | ? | |
| `create_bucket(bucket)` | ? | |
| `list_buckets() → list` | ? | |

If the naming or signatures differ, please describe the actual interface —
we will write the adapter to match Memory-FS, not the other way around.

### 3. Addressing model

Does Memory-FS use a `bucket / key` two-level hierarchy, or a flat key
namespace, or something else (e.g. path-based, tag-based)?

If it is flat, we would namespace keys as `{bucket}/{key}` internally and
maintain a separate bucket registry.

If it is already hierarchical, we want to know the natural mapping.

### 4. Metadata and object headers

S3 requires per-object metadata (Content-Type, Content-Length, ETag, Last-Modified).

Does Memory-FS store metadata alongside object bodies?  If so:
- How is metadata stored and retrieved?
- Does it compute or store an ETag (MD5 or similar) automatically?
- Does it record a last-modified timestamp?

### 5. Listing semantics

S3 `ListObjectsV2` supports:
- `prefix` filtering
- `delimiter` for pseudo-directory grouping (returns `CommonPrefixes`)
- `max_keys` pagination with continuation tokens

Does Memory-FS support any of these?  Even partial support (prefix filtering
only) is useful.  We will implement the gap ourselves if needed.

### 6. Vault integration

The project lead mentioned Memory-FS has vault integration.  Does this mean:
- Objects stored in Memory-FS can be persisted to the vault automatically?
- Or that Memory-FS can be configured to use vault as its primary storage?

If either is true, does the same `put/get` interface work transparently
regardless of whether the vault backend is active?

### 7. Real-S3 sync or proxy

Does Memory-FS have any capability for:
- Syncing its contents to/from real AWS S3?
- Using real AWS S3 as a read-through / write-through backend?

Even a partial or experimental capability is worth knowing about.

### 8. Concurrency and thread safety

The S3 server will handle concurrent requests.  Is Memory-FS thread-safe?
If not, what is the recommended pattern for concurrent access (e.g. one
instance per request, explicit locking)?

### 9. Minimal usage example

A short Python snippet showing Memory-FS being used to:
1. Create a bucket (or namespace)
2. Put an object
3. Get it back
4. List objects in the bucket

This will be the direct template for the `S3__Backend__Memory_FS` adapter.

---

## What we will produce

Once we have the answers above, we will write:

```python
# sg_compute_specs/s3_server/backends/S3__Backend__Memory_FS.py

from <memory_fs_import_path> import <MemoryFsClass>
from sg_compute_specs.s3_server.backends.S3__Backend import S3__Backend


class S3__Backend__Memory_FS(S3__Backend):
    fs : <MemoryFsClass> = None

    def setup(self) -> 'S3__Backend__Memory_FS':
        self.fs = <MemoryFsClass>()
        return self

    def put(self, bucket, key, body, metadata):
        # delegate to Memory-FS
        ...

    def get(self, bucket, key) -> bytes:
        # delegate to Memory-FS
        ...

    # ... remaining operations
```

This adapter is the **only file** that imports from Memory-FS.  The rest of
the S3 server stack — routes, call log, XML serialisation, health checks —
never touches Memory-FS directly.

---

## Priority order

If you can only answer some of the questions, the most valuable are (in order):

1. Package name + import path (question 1) — we cannot write a single line of
   adapter code without this.
2. The put/get/list/delete interface (question 2) — the core of the adapter.
3. The addressing model (question 3) — determines how we map `bucket/key` to
   whatever Memory-FS uses internally.
4. Metadata support (question 4) — required to pass boto3's HeadObject
   assertions.
5. Everything else is useful but not blocking Phase 1.

Thank you.
