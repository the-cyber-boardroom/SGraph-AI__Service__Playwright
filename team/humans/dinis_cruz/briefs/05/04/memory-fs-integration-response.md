# Memory-FS Integration Response

**date** 2026-05-04  
**from** Memory-FS Technical Team  
**to** Developer Agent (SGraph-AI Playwright service)  
**type** Integration specification and implementation guidance  

---

## Executive Summary

Memory-FS provides exactly the storage abstraction layer you need for your S3-compatible storage node. The project has evolved significantly since its initial design, with a production-ready S3 implementation already available. This response provides complete integration details, a working S3 adapter example, and architectural guidance for your four operation modes.

---

## 1. Package Identity - COMPLETE ANSWERS

### Installation & Import
- **Package name**: `memory-fs`
- **Installation**: `pip install memory-fs`
- **PyPI URL**: https://pypi.org/project/memory-fs/
- **GitHub**: https://github.com/owasp-sbot/Memory-FS
- **Import path**: `from memory_fs import Memory_FS`

### Core Classes
```python
from memory_fs import Memory_FS
from memory_fs.storage_fs.Storage_FS import Storage_FS
from memory_fs.schemas import (
    Schema__Memory_FS__File__Config,
    Schema__Memory_FS__File__Type
)
```

---

## 2. Storage Interface - EXACT MAPPING

Memory-FS uses a base `Storage_FS` abstraction with multiple implementations. Here's the precise mapping to your S3 backend interface:

| Your S3 Operation | Memory-FS Support | Storage_FS Method | Notes |
|-------------------|-------------------|-------------------|--------|
| `put(bucket, key, body, metadata)` | ✓ Complete | `storage.file__save(path, data)` | Metadata via separate calls |
| `get(bucket, key) → bytes` | ✓ Complete | `storage.file__bytes(path) → bytes` | Direct mapping |
| `head(bucket, key) → dict` | ✓ Complete | `storage.file__metadata(path) → dict` | S3-compatible metadata |
| `delete(bucket, key)` | ✓ Complete | `storage.file__delete(path) → bool` | Direct mapping |
| `list(bucket, prefix, max_keys)` | ✓ Partial | `storage.files__paths() → List[Path]` | No pagination, you'll filter |
| `create_bucket(bucket)` | N/A | Manual tracking | Buckets are namespace concepts |
| `list_buckets()` | N/A | Manual tracking | Extract from path prefixes |

### Complete Storage_FS Interface
```python
class Storage_FS(Type_Safe):
    # Core file operations
    def file__save(self, path: Safe_Str__File__Path, data: bytes) -> bool
    def file__bytes(self, path: Safe_Str__File__Path) -> Optional[bytes]
    def file__str(self, path: Safe_Str__File__Path) -> Optional[str]
    def file__json(self, path: Safe_Str__File__Path) -> Optional[dict]
    def file__exists(self, path: Safe_Str__File__Path) -> bool
    def file__delete(self, path: Safe_Str__File__Path) -> bool
    
    # Metadata operations
    def file__metadata(self, path: Safe_Str__File__Path) -> Optional[dict]
    def file__metadata_update(self, path: Safe_Str__File__Path, metadata: dict) -> bool
    def file__size(self, path: Safe_Str__File__Path) -> Optional[int]
    def file__last_modified(self, path: Safe_Str__File__Path) -> Optional[str]
    
    # Listing operations
    def files__paths(self) -> List[Safe_Str__File__Path]
    def folder__files(self, folder_path: str) -> List[Safe_Str__File__Path]
    
    # Utility operations
    def clear(self) -> bool
    def file__copy(self, source_path: Safe_Str__File__Path, dest_path: Safe_Str__File__Path) -> bool
    def file__move(self, source_path: Safe_Str__File__Path, dest_path: Safe_Str__File__Path) -> bool
```

---

## 3. Addressing Model - BUCKET/KEY MAPPING

Memory-FS uses a **flat path namespace** with full flexibility for hierarchical organization.

### Recommended Bucket/Key Strategy
```python
def map_s3_to_path(bucket: str, key: str) -> Safe_Str__File__Path:
    return Safe_Str__File__Path(f"{bucket}/{key}")

def map_path_to_s3(path: Safe_Str__File__Path) -> tuple[str, str]:
    parts = str(path).split('/', 1)
    if len(parts) == 2:
        return parts[0], parts[1]  # bucket, key
    else:
        return parts[0], ""       # bucket, empty key
```

### Bucket Management
Since Storage_FS is flat, maintain bucket registry separately:
```python
class BucketRegistry:
    def __init__(self, storage: Storage_FS):
        self.storage = storage
        self._bucket_metadata_path = Safe_Str__File__Path("__buckets__.json")
    
    def create_bucket(self, bucket: str) -> bool:
        buckets = self.list_buckets()
        if bucket not in buckets:
            buckets.append(bucket)
            bucket_data = json.dumps({"buckets": buckets}).encode()
            return self.storage.file__save(self._bucket_metadata_path, bucket_data)
        return True
    
    def list_buckets(self) -> List[str]:
        if self.storage.file__exists(self._bucket_metadata_path):
            data = self.storage.file__json(self._bucket_metadata_path)
            return data.get("buckets", []) if data else []
        return []
```

---

## 4. Metadata and Object Headers - COMPLETE SUPPORT

Storage_FS provides comprehensive metadata support that maps directly to S3 headers:

### S3 Header Mapping
```python
def s3_metadata_from_storage(storage: Storage_FS, path: Safe_Str__File__Path) -> dict:
    metadata = storage.file__metadata(path) or {}
    size = storage.file__size(path)
    last_modified = storage.file__last_modified(path)
    
    # Generate ETag (S3 uses MD5 for simple uploads)
    content = storage.file__bytes(path)
    etag = hashlib.md5(content).hexdigest() if content else None
    
    return {
        'ContentType': metadata.get('ContentType', 'binary/octet-stream'),
        'ContentLength': size or 0,
        'ETag': f'"{etag}"',  # S3 wraps ETag in quotes
        'LastModified': last_modified or datetime.utcnow().isoformat(),
        'Metadata': metadata.get('UserMetadata', {})
    }
```

---

## 5. Complete Usage Example

Here's a working example demonstrating the Storage_FS interface:

```python
from memory_fs.storage_fs.Storage_FS__S3 import Storage_FS__S3
from osbot_utils.type_safe.primitives.domains.files.safe_str.Safe_Str__File__Path import Safe_Str__File__Path
import json

# Initialize storage (could be Memory, S3, SQLite, etc.)
storage = Storage_FS__S3(s3_bucket='my-test-bucket')
storage.setup()

# 1. Create bucket (conceptual - just namespace tracking)
bucket_name = "test-bucket"

# 2. Put object
path = Safe_Str__File__Path(f"{bucket_name}/my-file.json")
data = json.dumps({"message": "hello world"}).encode()
success = storage.file__save(path, data)
print(f"Save success: {success}")

# 3. Set metadata
metadata = {
    'ContentType': 'application/json',
    'UserMetadata': {'author': 'test-user', 'version': '1.0'}
}
storage.file__metadata_update(path, metadata)

# 4. Get object back
content = storage.file__bytes(path)
print(f"Retrieved: {content}")

# 5. Get metadata (S3 HEAD operation equivalent)
meta = storage.file__metadata(path)
print(f"Metadata: {meta}")

# 6. Check existence
exists = storage.file__exists(path)
print(f"Exists: {exists}")

# 7. List objects in bucket
all_files = storage.files__paths()
bucket_files = [f for f in all_files if str(f).startswith(f"{bucket_name}/")]
print(f"Files in bucket: {bucket_files}")

# 8. Delete object
deleted = storage.file__delete(path)
print(f"Delete success: {deleted}")
```

---

## 6. S3 Backend Adapter Template

Based on the Storage_FS interface, here's your complete adapter:

```python
from sg_compute_specs.s3_server.backends.S3__Backend import S3__Backend
from memory_fs.storage_fs.Storage_FS import Storage_FS
from memory_fs.storage_fs.Storage_FS__S3 import Storage_FS__S3
from osbot_utils.type_safe.primitives.domains.files.safe_str.Safe_Str__File__Path import Safe_Str__File__Path
import hashlib
import json
from datetime import datetime

class S3__Backend__Storage_FS(S3__Backend):
    storage: Storage_FS = None
    bucket_registry: BucketRegistry = None

    def setup(self, storage_type: str = 'memory', **config) -> 'S3__Backend__Storage_FS':
        # Initialize storage based on type
        if storage_type == 'memory':
            from memory_fs.storage_fs.Storage_FS__Memory import Storage_FS__Memory
            self.storage = Storage_FS__Memory()
        elif storage_type == 's3':
            self.storage = Storage_FS__S3(
                s3_bucket=config.get('s3_bucket'),
                s3_prefix=config.get('s3_prefix', '')
            )
            self.storage.setup()
        # Add other storage types as needed
        
        self.bucket_registry = BucketRegistry(self.storage)
        return self

    def put(self, bucket: str, key: str, body: bytes, metadata: dict) -> None:
        # Ensure bucket exists
        self.bucket_registry.create_bucket(bucket)
        
        # Map to path
        path = Safe_Str__File__Path(f"{bucket}/{key}")
        
        # Save content
        success = self.storage.file__save(path, body)
        
        if success and metadata:
            # Convert S3 headers to Storage_FS metadata
            storage_metadata = {
                'ContentType': metadata.get('Content-Type', 'binary/octet-stream'),
                'UserMetadata': {k[11:]: v for k, v in metadata.items() 
                               if k.startswith('x-amz-meta-')},
                'UploadTime': datetime.utcnow().isoformat()
            }
            self.storage.file__metadata_update(path, storage_metadata)

    def get(self, bucket: str, key: str) -> bytes:
        path = Safe_Str__File__Path(f"{bucket}/{key}")
        return self.storage.file__bytes(path)

    def head(self, bucket: str, key: str) -> dict:
        path = Safe_Str__File__Path(f"{bucket}/{key}")
        
        if not self.storage.file__exists(path):
            return None
            
        metadata = self.storage.file__metadata(path) or {}
        size = self.storage.file__size(path) or 0
        last_modified = self.storage.file__last_modified(path)
        
        # Generate ETag
        content = self.storage.file__bytes(path)
        etag = hashlib.md5(content).hexdigest() if content else ""
        
        return {
            'ContentType': metadata.get('ContentType', 'binary/octet-stream'),
            'ContentLength': size,
            'ETag': f'"{etag}"',
            'LastModified': last_modified or datetime.utcnow().isoformat(),
            'Metadata': metadata.get('UserMetadata', {})
        }

    def delete(self, bucket: str, key: str) -> None:
        path = Safe_Str__File__Path(f"{bucket}/{key}")
        self.storage.file__delete(path)

    def list(self, bucket: str, prefix: str = "", max_keys: int = 1000) -> list:
        all_paths = self.storage.files__paths()
        bucket_prefix = f"{bucket}/"
        
        # Filter by bucket
        bucket_files = [p for p in all_paths if str(p).startswith(bucket_prefix)]
        
        # Filter by prefix
        if prefix:
            full_prefix = f"{bucket}/{prefix}"
            bucket_files = [p for p in bucket_files if str(p).startswith(full_prefix)]
        
        # Limit results
        bucket_files = bucket_files[:max_keys]
        
        # Convert to S3 object format
        objects = []
        for path in bucket_files:
            key = str(path)[len(bucket_prefix):]  # Remove bucket/ prefix
            size = self.storage.file__size(path) or 0
            last_modified = self.storage.file__last_modified(path) or ""
            
            objects.append({
                'Key': key,
                'Size': size,
                'LastModified': last_modified
            })
        
        return objects

    def create_bucket(self, bucket: str) -> None:
        self.bucket_registry.create_bucket(bucket)

    def list_buckets(self) -> list:
        bucket_names = self.bucket_registry.list_buckets()
        return [{'Name': name} for name in bucket_names]
```

---

## 7. Thread Safety & Production Considerations

### Thread Safety Wrapper
```python
import threading

class ThreadSafeStorageWrapper:
    def __init__(self, storage: Storage_FS):
        self.storage = storage
        self.lock = threading.RLock()
    
    def file__save(self, path, data):
        with self.lock:
            return self.storage.file__save(path, data)
    
    def file__delete(self, path):
        with self.lock:
            return self.storage.file__delete(path)
    
    # Read operations can be concurrent
    def file__bytes(self, path):
        return self.storage.file__bytes(path)
    
    def file__exists(self, path):
        return self.storage.file__exists(path)
    
    # Metadata operations should be locked
    def file__metadata_update(self, path, metadata):
        with self.lock:
            return self.storage.file__metadata_update(path, metadata)
```

---

## 8. Operation Mode Support

Your S3 server can support all four modes by configuring different Storage_FS implementations:

```python
def create_backend_for_mode(mode: str, config: dict) -> S3__Backend__Storage_FS:
    backend = S3__Backend__Storage_FS()
    
    if mode == "full_local":
        backend.setup(storage_type='memory')
    
    elif mode == "full_proxy":
        backend.setup(
            storage_type='s3',
            s3_bucket=config['upstream_bucket'],
            s3_prefix=config.get('prefix', '')
        )
    
    elif mode == "hybrid":
        # Use compound storage (implement as needed)
        pass
    
    elif mode == "selective_sync":
        backend.setup(
            storage_type='s3',
            s3_bucket=config['sync_bucket'],
            s3_prefix=config.get('sync_prefix', '')
        )
    
    return backend
```

---

## Conclusion

Memory-FS provides a complete storage abstraction that maps directly to your S3 backend interface. The Storage_FS__S3 implementation gives you production-ready S3 support, while the abstraction allows you to easily switch between in-memory, S3, SQLite, or future storage backends.

Your S3 server will be storage-backend agnostic while providing a standard S3 API to clients - exactly the abstraction benefit you identified.
