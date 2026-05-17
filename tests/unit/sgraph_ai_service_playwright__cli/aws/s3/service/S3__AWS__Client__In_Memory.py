# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — S3__AWS__Client__In_Memory
# In-memory fake boto3 S3 client for unit tests.
# No mocks. No patches. Dict-backed dispatch.
#
# Object store keyed by (bucket, key) → bytes body.
# Bucket store keyed by bucket_name → metadata dict.
# Presign returns a deterministic fake URL for assertion.
# ═══════════════════════════════════════════════════════════════════════════════

from datetime import datetime, timezone

from sgraph_ai_service_playwright__cli.aws.s3.service.S3__AWS__Client import S3__AWS__Client


class _Fake_S3_Client:
    """Minimal boto3-alike S3 client backed by in-memory stores."""

    def __init__(self, object_store: dict, bucket_store: dict):
        self._objects = object_store   # (bucket, key) → {'Body': bytes, 'ContentType': str, 'ETag': str, ...}
        self._buckets = bucket_store   # bucket → {'Region': str, 'Versioning': str, 'Created': str}

    # ── list_buckets ──────────────────────────────────────────────────────────

    def list_buckets(self):
        buckets = []
        for name, meta in self._buckets.items():
            buckets.append({'Name': name, 'CreationDate': meta.get('Created', '2026-01-01T00:00:00+00:00')})
        return {'Buckets': buckets}

    # ── list_objects_v2 paginator ─────────────────────────────────────────────

    def get_paginator(self, operation: str):
        return _Fake_Paginator(self._objects, self._buckets, operation)

    # ── head_object ───────────────────────────────────────────────────────────

    def head_object(self, Bucket: str, Key: str):
        record = self._objects.get((Bucket, Key))
        if record is None:
            raise Exception(f'NoSuchKey: {Bucket}/{Key}')
        body = record.get('Body', b'')
        return {
            'ContentLength'       : len(body),
            'ETag'                : record.get('ETag', '"abc"'),
            'LastModified'        : record.get('LastModified', '2026-01-01T00:00:00+00:00'),
            'StorageClass'        : record.get('StorageClass', 'STANDARD'),
            'ContentType'         : record.get('ContentType', 'application/octet-stream'),
            'ServerSideEncryption': record.get('Encryption', ''),
            'VersionId'           : record.get('VersionId', ''),
        }

    # ── get_object ────────────────────────────────────────────────────────────

    def get_object(self, Bucket: str, Key: str):
        record = self._objects.get((Bucket, Key))
        if record is None:
            raise Exception(f'NoSuchKey: {Bucket}/{Key}')
        body = record.get('Body', b'')
        import io
        return {'Body': io.BytesIO(body), 'ContentLength': len(body)}

    # ── put_object ────────────────────────────────────────────────────────────

    def put_object(self, Bucket: str, Key: str, Body: bytes,
                   ContentType: str = 'application/octet-stream',
                   IfMatch: str = '', **_):
        existing = self._objects.get((Bucket, Key))
        if IfMatch and existing:
            current_etag = existing.get('ETag', '').strip('"')
            check_etag   = IfMatch.strip('"')
            if current_etag != check_etag:
                raise Exception('PreconditionFailed: ETag mismatch (412)')
        import hashlib
        etag = '"' + hashlib.md5(Body).hexdigest() + '"'
        now  = datetime.now(timezone.utc).isoformat()
        self._objects[(Bucket, Key)] = {
            'Body'        : Body,
            'ContentType' : ContentType,
            'ETag'        : etag,
            'LastModified': now,
            'StorageClass': 'STANDARD',
        }

    # ── copy_object ───────────────────────────────────────────────────────────

    def copy_object(self, CopySource: dict, Bucket: str, Key: str, **_):
        src_bucket = CopySource['Bucket']
        src_key    = CopySource['Key']
        record     = self._objects.get((src_bucket, src_key))
        if record is None:
            raise Exception(f'NoSuchKey: {src_bucket}/{src_key}')
        import copy
        self._objects[(Bucket, Key)] = copy.deepcopy(record)

    # ── delete_object ─────────────────────────────────────────────────────────

    def delete_object(self, Bucket: str, Key: str):
        self._objects.pop((Bucket, Key), None)

    # ── create_bucket ─────────────────────────────────────────────────────────

    def create_bucket(self, Bucket: str, **_):
        if Bucket not in self._buckets:
            self._buckets[Bucket] = {
                'Created'   : datetime.now(timezone.utc).isoformat(),
                'Region'    : 'us-east-1',
                'Versioning': 'Enabled',
            }

    # ── bucket access-block / versioning stubs ────────────────────────────────

    def put_public_access_block(self, **_):                                       # no-op for tests
        pass

    def put_bucket_versioning(self, Bucket: str, VersioningConfiguration: dict, **_):
        if Bucket in self._buckets:
            self._buckets[Bucket]['Versioning'] = VersioningConfiguration.get('Status', 'Enabled')

    def get_bucket_location(self, Bucket: str):
        meta = self._buckets.get(Bucket, {})
        return {'LocationConstraint': meta.get('Region', 'us-east-1')}

    def get_bucket_versioning(self, Bucket: str):
        meta = self._buckets.get(Bucket, {})
        return {'Status': meta.get('Versioning', 'Disabled')}

    # ── presigned URL stub ────────────────────────────────────────────────────

    def generate_presigned_url(self, operation: str, Params: dict = None,
                               ExpiresIn: int = 3600, **_):
        params  = Params or {}
        bucket  = params.get('Bucket', '')
        key     = params.get('Key', '')
        return f'https://s3.amazonaws.com/{bucket}/{key}?fake-presigned&ttl={ExpiresIn}'


class _Fake_Paginator:
    def __init__(self, objects: dict, buckets: dict, operation: str):
        self._objects   = objects
        self._buckets   = buckets
        self._operation = operation

    def paginate(self, Bucket: str = '', Prefix: str = '',
                 Delimiter: str = '', **_):
        if self._operation == 'list_objects_v2':
            contents = []
            common   = set()
            for (b, k), rec in self._objects.items():
                if b != Bucket:
                    continue
                if Prefix and not k.startswith(Prefix):
                    continue
                if Delimiter:
                    rest = k[len(Prefix):]
                    idx  = rest.find(Delimiter)
                    if idx != -1:
                        common.add(Prefix + rest[:idx + 1])
                        continue
                body = rec.get('Body', b'')
                contents.append({
                    'Key'         : k,
                    'Size'        : len(body),
                    'LastModified': rec.get('LastModified', '2026-01-01T00:00:00+00:00'),
                    'ETag'        : rec.get('ETag', '"abc"'),
                    'StorageClass': rec.get('StorageClass', 'STANDARD'),
                })
            common_prefixes = [{'Prefix': p} for p in sorted(common)]
            yield {'Contents': contents, 'CommonPrefixes': common_prefixes}
        elif self._operation in ('list_role_policies', 'list_attached_role_policies'):
            yield {}


class S3__AWS__Client__In_Memory(S3__AWS__Client):

    def __init__(self, object_store: dict = None, bucket_store: dict = None):
        super().__init__()
        self._object_store = object_store if object_store is not None else {}
        self._bucket_store = bucket_store if bucket_store is not None else {}
        self._fake         = _Fake_S3_Client(self._object_store, self._bucket_store)

    def client(self):
        return self._fake

    # ── test helpers ──────────────────────────────────────────────────────────

    def add_bucket(self, name: str, region: str = 'us-east-1',
                   versioning: str = 'Enabled') -> 'S3__AWS__Client__In_Memory':
        self._bucket_store[name] = {
            'Created'   : '2026-01-01T00:00:00+00:00',
            'Region'    : region,
            'Versioning': versioning,
        }
        return self

    def add_object(self, bucket: str, key: str, body: bytes,
                   content_type: str = 'application/octet-stream',
                   storage_class: str = 'STANDARD',
                   etag: str = '') -> 'S3__AWS__Client__In_Memory':
        import hashlib
        computed_etag = etag if etag else ('"' + hashlib.md5(body).hexdigest() + '"')
        self._object_store[(bucket, key)] = {
            'Body'        : body,
            'ContentType' : content_type,
            'ETag'        : computed_etag,
            'LastModified': '2026-05-17T12:00:00+00:00',
            'StorageClass': storage_class,
        }
        return self
