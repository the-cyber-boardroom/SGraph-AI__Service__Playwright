# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — S3__Source__Adapter
# Implements Source__Contract so S3 buckets/objects appear as an observability
# source alongside CloudWatch Logs and CloudTrail.
#
# Streams = buckets; tail() iterates lines of a log-like object appended to
# over time; query() filters objects by key prefix + optional text pattern.
# ═══════════════════════════════════════════════════════════════════════════════

import io
import gzip
import time
from datetime import datetime, timezone

from sgraph_ai_service_playwright__cli.aws._shared.schemas.Schema__AWS__Source__Event   import Schema__AWS__Source__Event
from sgraph_ai_service_playwright__cli.aws._shared.source_contract.Source__Contract     import Source__Contract
from sgraph_ai_service_playwright__cli.aws._shared.source_contract.Source__Query        import Source__Query
from sgraph_ai_service_playwright__cli.aws._shared.source_contract.Source__Result__Page import Source__Result__Page
from sgraph_ai_service_playwright__cli.aws._shared.source_contract.Source__Stream       import Source__Stream
from sgraph_ai_service_playwright__cli.aws.s3.service.S3__AWS__Client                   import S3__AWS__Client


class S3__Source__Adapter(Source__Contract):
    s3_client : S3__AWS__Client                                                   # injected — allows in-memory fake in tests

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if self.s3_client is None:
            self.s3_client = S3__AWS__Client()

    # ── Source__Contract implementation ───────────────────────────────────────

    def connect(self) -> bool:                                                    # verify S3 access by listing buckets
        try:
            buckets = self.s3_client.list_buckets()
            return isinstance(buckets, list)
        except Exception:
            return False

    def list_streams(self) -> list:                                               # bucket names are the streams
        buckets = self.s3_client.list_buckets()
        return [str(b.name) for b in buckets]

    def tail(self, stream: str, since: str) -> Source__Stream:
        # stream = "bucket/prefix/key" — tail lines from the object
        bucket, key = self._split_stream(stream)
        if not bucket or not key:
            return Source__Stream(source='s3', stream=stream)

        since_ts = self._parse_since(since)

        def _gen():
            seen_lines = 0
            while True:
                try:
                    data  = self.s3_client.get_object_body(bucket, key)
                    lines = self._decode_lines(data)
                    new_lines = lines[seen_lines:]
                    for line in new_lines:
                        seen_lines += 1
                        yield Schema__AWS__Source__Event(
                            timestamp = datetime.now(timezone.utc).isoformat(),
                            source    = 's3',
                            stream    = stream,
                            message   = line.rstrip('\n'),
                            raw       = {'bucket': bucket, 'key': key, 'line': line},
                        )
                except Exception:
                    break
                time.sleep(5)                                                     # poll interval for tail

        return Source__Stream(source='s3', stream=stream).with_generator(_gen())

    def query(self, q: Source__Query) -> Source__Result__Page:
        bucket, prefix = self._split_stream(q.stream)
        if not bucket:
            bucket = q.stream
            prefix = q.text if q.text else ''
        objects  = self.s3_client.search_objects(bucket, prefix, pattern=q.text or '*')
        events   = []
        for obj in objects[:q.limit]:
            events.append(Schema__AWS__Source__Event(
                timestamp = str(obj.last_modified),
                source    = 's3',
                stream    = f'{bucket}/{str(obj.key)}',
                message   = f'{str(obj.key)} ({obj.size} bytes)',
                raw       = {
                    'bucket'       : bucket,
                    'key'          : str(obj.key),
                    'size'         : obj.size,
                    'last_modified': obj.last_modified,
                    'etag'         : str(obj.etag),
                },
            ))
        return Source__Result__Page(
            events      = events,
            total_count = len(events),
            truncated   = len(objects) > q.limit,
        )

    def stats(self, stream: str, agg: str) -> dict:
        bucket, _ = self._split_stream(stream)
        if not bucket:
            bucket = stream
        size_info = self.s3_client.get_bucket_size_estimate(bucket)
        return {
            'bucket'      : bucket,
            'object_count': size_info.get('object_count', 0),
            'total_bytes' : size_info.get('total_bytes', 0),
        }

    def schema(self, stream: str) -> dict:
        return {
            'type'   : 's3-object',
            'fields' : {
                'bucket'       : 'str',
                'key'          : 'str',
                'size'         : 'int',
                'last_modified': 'str',
                'etag'         : 'str',
                'content_type' : 'str',
                'storage_class': 'str',
            },
        }

    # ── internal ──────────────────────────────────────────────────────────────

    def _split_stream(self, stream: str):                                         # "bucket/key" → (bucket, key)
        if not stream:
            return '', ''
        parts  = stream.split('/', 1)
        bucket = parts[0]
        key    = parts[1] if len(parts) > 1 else ''
        return bucket, key

    def _decode_lines(self, data: bytes) -> list:
        if data[:2] == b'\x1f\x8b':                                               # gzip magic bytes — transparent decompression
            try:
                data = gzip.decompress(data)
            except Exception:
                pass
        return data.decode('utf-8', errors='replace').splitlines(keepends=True)

    def _parse_since(self, since: str) -> float:                                  # parse duration string to epoch float
        if not since:
            return time.time() - 300                                              # default 5 min
        multipliers = {'s': 1, 'm': 60, 'h': 3600, 'd': 86400}
        if since[-1].lower() in multipliers:
            try:
                return time.time() - int(since[:-1]) * multipliers[since[-1].lower()]
            except ValueError:
                pass
        return time.time() - 300
