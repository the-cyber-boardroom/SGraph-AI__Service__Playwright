# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tests for S3__Source__Adapter
# Covers: connect, list_streams, query, stats, schema.
# No mocks, no patches. Uses S3__AWS__Client__In_Memory.
# ═══════════════════════════════════════════════════════════════════════════════

from sgraph_ai_service_playwright__cli.aws.s3.service.S3__Source__Adapter import S3__Source__Adapter
from tests.unit.sgraph_ai_service_playwright__cli.aws.s3.service.S3__AWS__Client__In_Memory import (
    S3__AWS__Client__In_Memory,
)
from sgraph_ai_service_playwright__cli.aws._shared.source_contract.Source__Query import Source__Query

_BUCKET = 'obs-bucket'


def _adapter_with_buckets(*names) -> S3__Source__Adapter:
    client = S3__AWS__Client__In_Memory()
    for name in names:
        client.add_bucket(name)
    return S3__Source__Adapter(s3_client=client)


class TestConnect:

    def test_returns_true_when_buckets_accessible(self):
        adapter = _adapter_with_buckets(_BUCKET)
        assert adapter.connect() is True

    def test_returns_true_when_no_buckets(self):
        adapter = _adapter_with_buckets()
        assert adapter.connect() is True                                           # empty list is still a valid response


class TestListStreams:

    def test_returns_bucket_names(self):
        adapter = _adapter_with_buckets('bucket-a', 'bucket-b')
        streams = adapter.list_streams()
        assert 'bucket-a' in streams
        assert 'bucket-b' in streams

    def test_empty_when_no_buckets(self):
        adapter = _adapter_with_buckets()
        assert adapter.list_streams() == []


class TestQuery:

    def test_returns_result_page(self):
        client = S3__AWS__Client__In_Memory()
        client.add_bucket(_BUCKET)
        client.add_object(_BUCKET, 'logs/2026-05-17.log', b'data')
        client.add_object(_BUCKET, 'data/report.json',    b'{}')
        adapter = S3__Source__Adapter(s3_client=client)
        q       = Source__Query(stream=_BUCKET, text='*.log', limit=10)
        page    = adapter.query(q)
        keys    = [ev.raw.get('key', '') for ev in page.events]
        assert 'logs/2026-05-17.log' in keys

    def test_total_count_matches_events(self):
        client = S3__AWS__Client__In_Memory()
        client.add_bucket(_BUCKET)
        client.add_object(_BUCKET, 'a.txt', b'a')
        client.add_object(_BUCKET, 'b.txt', b'b')
        adapter = S3__Source__Adapter(s3_client=client)
        q       = Source__Query(stream=_BUCKET, text='*.txt', limit=10)
        page    = adapter.query(q)
        assert page.total_count == len(page.events)

    def test_limit_respected(self):
        client = S3__AWS__Client__In_Memory()
        client.add_bucket(_BUCKET)
        for i in range(10):
            client.add_object(_BUCKET, f'file-{i}.txt', b'x')
        adapter = S3__Source__Adapter(s3_client=client)
        q       = Source__Query(stream=_BUCKET, text='*.txt', limit=3)
        page    = adapter.query(q)
        assert len(page.events) <= 3


class TestStats:

    def test_returns_bucket_stats(self):
        client = S3__AWS__Client__In_Memory()
        client.add_bucket(_BUCKET)
        client.add_object(_BUCKET, 'a.txt', b'hello world')  # 11 bytes
        adapter = S3__Source__Adapter(s3_client=client)
        result  = adapter.stats(_BUCKET, 'count')
        assert result['bucket']       == _BUCKET
        assert result['object_count'] == 1
        assert result['total_bytes']  == 11

    def test_empty_bucket_returns_zeros(self):
        client = S3__AWS__Client__In_Memory()
        client.add_bucket(_BUCKET)
        adapter = S3__Source__Adapter(s3_client=client)
        result  = adapter.stats(_BUCKET, 'count')
        assert result['object_count'] == 0
        assert result['total_bytes']  == 0


class TestSchema:

    def test_schema_returns_expected_fields(self):
        adapter = _adapter_with_buckets(_BUCKET)
        schema  = adapter.schema(_BUCKET)
        assert schema.get('type') == 's3-object'
        fields = schema.get('fields', {})
        assert 'bucket'        in fields
        assert 'key'           in fields
        assert 'size'          in fields
        assert 'last_modified' in fields
        assert 'etag'          in fields
