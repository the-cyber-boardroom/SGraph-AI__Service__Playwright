# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — S3__AWS__Client
# Sole boto3 boundary for S3 object and bucket operations.
#
# Credentials are resolved via Sg__Aws__Session.from_context() so that
# `sg credentials switch dev` is honoured by all S3 calls.
# Subclasses override client() to inject fakes for unit tests.
#
# Mutation guard: callers must set SG_AWS__S3__ALLOW_MUTATIONS=1 before calling
# cp, mv, rm, sync, edit, bucket_create, or bucket_config.
# ═══════════════════════════════════════════════════════════════════════════════

import io
import time
from datetime import datetime, timezone
from typing   import Optional, Iterator

from botocore.exceptions import ClientError

from osbot_utils.type_safe.Type_Safe                                              import Type_Safe

from sgraph_ai_service_playwright__cli.aws.s3.enums.Enum__S3__Storage__Class     import Enum__S3__Storage__Class
from sgraph_ai_service_playwright__cli.aws.s3.primitives.Safe_Str__S3__Bucket    import Safe_Str__S3__Bucket
from sgraph_ai_service_playwright__cli.aws.s3.primitives.Safe_Str__S3__ETag      import Safe_Str__S3__ETag
from sgraph_ai_service_playwright__cli.aws.s3.primitives.Safe_Str__S3__Key       import Safe_Str__S3__Key
from sgraph_ai_service_playwright__cli.aws.s3.schemas.Schema__S3__Bucket         import Schema__S3__Bucket
from sgraph_ai_service_playwright__cli.aws.s3.schemas.Schema__S3__List__Response import Schema__S3__List__Response
from sgraph_ai_service_playwright__cli.aws.s3.schemas.Schema__S3__Object         import Schema__S3__Object
from sgraph_ai_service_playwright__cli.aws.s3.schemas.Schema__S3__Stat           import Schema__S3__Stat
from sgraph_ai_service_playwright__cli.credentials.service.Sg__Aws__Session      import Sg__Aws__Session

_NOT_FOUND_CODES = {'NoSuchKey', 'NoSuchBucket', '404', 'NotFound'}               # ClientError codes treated as "not found"


class S3__AWS__Client(Type_Safe):
    session : Sg__Aws__Session = None                                             # cached session — injected or lazy-init via setup()
    region  : str              = ''                                               # override to target specific region

    def setup(self):                                                              # idempotent — noop if session already set
        if self.session is None:
            self.session = Sg__Aws__Session.from_context()
        return self

    def client(self):                                                             # single boto3 seam — subclass overrides to inject fake
        self.setup()
        return self.session.boto3_client_from_context('s3', region=self.region)

    # ── list operations ───────────────────────────────────────────────────────

    def list_buckets(self) -> list:                                               # returns list[Schema__S3__Bucket]
        resp    = self.client().list_buckets()
        buckets = []
        for b in resp.get('Buckets', []):
            name    = b.get('Name', '')
            created = str(b.get('CreationDate', ''))
            buckets.append(Schema__S3__Bucket(
                name         = Safe_Str__S3__Bucket(name) if name else Safe_Str__S3__Bucket(''),
                creation_date= created,
            ))
        return buckets

    def list_objects(self, bucket: str, prefix: str = '',
                     recursive: bool = False) -> Schema__S3__List__Response:
        s3        = self.client()
        objects   = []
        prefixes  = []
        delimiter = '' if recursive else '/'
        kwargs    = {'Bucket': bucket, 'Prefix': prefix}
        if delimiter:
            kwargs['Delimiter'] = delimiter
        paginator = s3.get_paginator('list_objects_v2')
        for page in paginator.paginate(**kwargs):
            for obj in page.get('Contents', []):
                key   = obj.get('Key', '')
                etag  = obj.get('ETag', '').strip('"')
                sc    = obj.get('StorageClass', 'STANDARD')
                mtime = str(obj.get('LastModified', ''))
                size  = obj.get('Size', 0)
                try:
                    storage_class = Enum__S3__Storage__Class(sc)
                except ValueError:
                    storage_class = Enum__S3__Storage__Class.UNKNOWN
                try:
                    safe_etag = Safe_Str__S3__ETag(f'"{etag}"') if etag else Safe_Str__S3__ETag('')
                except Exception:
                    safe_etag = Safe_Str__S3__ETag('')
                objects.append(Schema__S3__Object(
                    bucket        = Safe_Str__S3__Bucket(bucket) if bucket else Safe_Str__S3__Bucket(''),
                    key           = Safe_Str__S3__Key(key)        if key    else Safe_Str__S3__Key(''),
                    size          = size,
                    last_modified = mtime,
                    etag          = safe_etag,
                    storage_class = storage_class,
                ))
            for cp in page.get('CommonPrefixes', []):
                pfx = cp.get('Prefix', '')
                if pfx:
                    prefixes.append(pfx)
        return Schema__S3__List__Response(
            bucket   = Safe_Str__S3__Bucket(bucket) if bucket else Safe_Str__S3__Bucket(''),
            prefix   = prefix,
            objects  = objects,
            prefixes = prefixes,
        )

    # ── object read ───────────────────────────────────────────────────────────

    def head_object(self, bucket: str, key: str) -> Optional[Schema__S3__Stat]:
        try:
            resp  = self.client().head_object(Bucket=bucket, Key=key)
        except ClientError as exc:
            code = exc.response.get('Error', {}).get('Code', '')
            if code in _NOT_FOUND_CODES:
                return None
            raise
        size  = resp.get('ContentLength', 0)
        etag  = resp.get('ETag', '').strip('"')
        mtime = str(resp.get('LastModified', ''))
        sc    = resp.get('StorageClass', 'STANDARD')
        ct    = resp.get('ContentType', '')
        enc   = resp.get('ServerSideEncryption', '')
        ver   = resp.get('VersionId', '')
        try:
            storage_class = Enum__S3__Storage__Class(sc)
        except ValueError:
            storage_class = Enum__S3__Storage__Class.STANDARD
        try:
            safe_etag = Safe_Str__S3__ETag(f'"{etag}"') if etag else Safe_Str__S3__ETag('')
        except Exception:
            safe_etag = Safe_Str__S3__ETag('')
        return Schema__S3__Stat(
            bucket        = Safe_Str__S3__Bucket(bucket) if bucket else Safe_Str__S3__Bucket(''),
            key           = Safe_Str__S3__Key(key)        if key    else Safe_Str__S3__Key(''),
            size          = size,
            last_modified = mtime,
            etag          = safe_etag,
            storage_class = storage_class,
            content_type  = ct,
            encryption    = enc,
            version_id    = ver,
        )

    def get_object_body(self, bucket: str, key: str) -> bytes:                   # full download; use stream for large objects
        resp = self.client().get_object(Bucket=bucket, Key=key)
        return resp['Body'].read()

    def stream_object(self, bucket: str, key: str,
                      chunk_size: int = 65536) -> Iterator[bytes]:                # streaming download — avoids full buffer
        resp = self.client().get_object(Bucket=bucket, Key=key)
        body = resp['Body']
        while True:
            chunk = body.read(chunk_size)
            if not chunk:
                break
            yield chunk

    def generate_presigned_url(self, bucket: str, key: str,
                                ttl_seconds: int = 3600) -> str:
        return self.client().generate_presigned_url(
            'get_object',
            Params     = {'Bucket': bucket, 'Key': key},
            ExpiresIn  = ttl_seconds,
        )

    # ── search / grep ─────────────────────────────────────────────────────────

    def search_objects(self, bucket: str, prefix: str,
                       pattern: str) -> list:                                     # returns list[Schema__S3__Object] whose keys match pattern
        import fnmatch
        resp    = self.list_objects(bucket, prefix, recursive=True)
        matches = []
        for obj in resp.objects:
            key = str(obj.key)
            if fnmatch.fnmatch(key, pattern) or pattern in key:
                matches.append(obj)
        return matches

    # ── mutations ─────────────────────────────────────────────────────────────

    def put_object(self, bucket: str, key: str, body: bytes,
                   content_type: str = 'application/octet-stream',
                   if_match_etag: str = '') -> None:
        kwargs = {
            'Bucket'     : bucket,
            'Key'        : key,
            'Body'       : body,
            'ContentType': content_type,
        }
        if if_match_etag:
            kwargs['IfMatch'] = if_match_etag                                     # conditional PUT — raises 412 on ETag mismatch
        self.client().put_object(**kwargs)

    def copy_object(self, src_bucket: str, src_key: str,
                    dst_bucket: str, dst_key: str) -> None:
        self.client().copy_object(
            CopySource = {'Bucket': src_bucket, 'Key': src_key},
            Bucket     = dst_bucket,
            Key        = dst_key,
        )

    def delete_object(self, bucket: str, key: str) -> None:
        self.client().delete_object(Bucket=bucket, Key=key)

    def create_bucket(self, bucket: str, region: str = '') -> None:
        s3     = self.client()
        kwargs = {'Bucket': bucket}
        eff_region = region or self.region or 'us-east-1'
        if eff_region and eff_region != 'us-east-1':
            kwargs['CreateBucketConfiguration'] = {
                'LocationConstraint': eff_region,
            }
        s3.create_bucket(**kwargs)
        s3.put_public_access_block(                                               # block all public access by default
            Bucket                         = bucket,
            PublicAccessBlockConfiguration = {
                'BlockPublicAcls'      : True,
                'IgnorePublicAcls'     : True,
                'BlockPublicPolicy'    : True,
                'RestrictPublicBuckets': True,
            },
        )
        s3.put_bucket_versioning(                                                 # enable versioning by default
            Bucket                   = bucket,
            VersioningConfiguration  = {'Status': 'Enabled'},
        )

    # ── bucket metadata ───────────────────────────────────────────────────────

    def get_bucket_region(self, bucket: str) -> str:
        resp   = self.client().get_bucket_location(Bucket=bucket)
        region = resp.get('LocationConstraint') or 'us-east-1'
        return region

    def get_bucket_versioning(self, bucket: str) -> str:
        resp = self.client().get_bucket_versioning(Bucket=bucket)
        return resp.get('Status', 'Disabled')

    def get_bucket_size_estimate(self, bucket: str) -> dict:                      # returns {object_count, total_bytes}
        s3        = self.client()
        count     = 0
        total     = 0
        paginator = s3.get_paginator('list_objects_v2')
        for page in paginator.paginate(Bucket=bucket):
            for obj in page.get('Contents', []):
                count += 1
                total += obj.get('Size', 0)
        return {'object_count': count, 'total_bytes': total}
