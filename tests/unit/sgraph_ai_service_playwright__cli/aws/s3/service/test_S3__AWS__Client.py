# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tests for S3__AWS__Client (in-memory)
# Covers: ls, stat, presign, bucket-list, copy, delete, put, mutation gate.
# No mocks, no patches. Uses S3__AWS__Client__In_Memory.
# ═══════════════════════════════════════════════════════════════════════════════

import os
import pytest

from tests.unit.sgraph_ai_service_playwright__cli.aws.s3.service.S3__AWS__Client__In_Memory import (
    S3__AWS__Client__In_Memory,
)


_BUCKET  = 'test-bucket'
_KEY     = 'logs/2026-05-17.log'
_BODY    = b'line1\nline2\nline3\n'
_CONTENT = b'{"status": "ok"}'


class TestListBuckets:

    def test_empty_returns_empty_list(self):
        client = S3__AWS__Client__In_Memory()
        result = client.list_buckets()
        assert result == []

    def test_returns_added_buckets(self):
        client = S3__AWS__Client__In_Memory()
        client.add_bucket(_BUCKET)
        client.add_bucket('second-bucket')
        result = client.list_buckets()
        names  = [str(b.name) for b in result]
        assert _BUCKET       in names
        assert 'second-bucket' in names
        assert len(result)   == 2

    def test_bucket_has_creation_date(self):
        client = S3__AWS__Client__In_Memory()
        client.add_bucket(_BUCKET)
        buckets = client.list_buckets()
        assert buckets[0].creation_date != ''


class TestListObjects:

    def test_empty_bucket_returns_empty_response(self):
        client = S3__AWS__Client__In_Memory()
        client.add_bucket(_BUCKET)
        resp = client.list_objects(_BUCKET, '')
        assert resp.objects  == []
        assert resp.prefixes == []

    def test_returns_objects_in_bucket(self):
        client = S3__AWS__Client__In_Memory()
        client.add_bucket(_BUCKET)
        client.add_object(_BUCKET, _KEY, _BODY)
        resp = client.list_objects(_BUCKET, '', recursive=True)
        assert len(resp.objects) == 1
        assert str(resp.objects[0].key) == _KEY

    def test_prefix_filtering(self):
        client = S3__AWS__Client__In_Memory()
        client.add_bucket(_BUCKET)
        client.add_object(_BUCKET, 'logs/a.log', b'a')
        client.add_object(_BUCKET, 'data/b.json', b'b')
        resp = client.list_objects(_BUCKET, 'logs/', recursive=True)
        assert len(resp.objects) == 1
        assert str(resp.objects[0].key) == 'logs/a.log'

    def test_non_recursive_returns_common_prefixes(self):
        client = S3__AWS__Client__In_Memory()
        client.add_bucket(_BUCKET)
        client.add_object(_BUCKET, 'logs/a.log', b'a')
        client.add_object(_BUCKET, 'data/b.json', b'b')
        resp = client.list_objects(_BUCKET, '', recursive=False)
        assert 'logs/' in resp.prefixes or 'data/' in resp.prefixes

    def test_object_size_correct(self):
        client = S3__AWS__Client__In_Memory()
        client.add_bucket(_BUCKET)
        client.add_object(_BUCKET, 'file.txt', b'hello world')
        resp = client.list_objects(_BUCKET, '', recursive=True)
        assert resp.objects[0].size == 11


class TestHeadObject:

    def test_missing_object_returns_none(self):
        client = S3__AWS__Client__In_Memory()
        client.add_bucket(_BUCKET)
        result = client.head_object(_BUCKET, 'nonexistent.txt')
        assert result is None

    def test_returns_stat_for_existing_object(self):
        client = S3__AWS__Client__In_Memory()
        client.add_bucket(_BUCKET)
        client.add_object(_BUCKET, _KEY, _BODY)
        stat = client.head_object(_BUCKET, _KEY)
        assert stat is not None
        assert stat.size          == len(_BODY)
        assert str(stat.key)      == _KEY
        assert str(stat.bucket)   == _BUCKET

    def test_etag_populated(self):
        client = S3__AWS__Client__In_Memory()
        client.add_bucket(_BUCKET)
        client.add_object(_BUCKET, _KEY, _BODY)
        stat = client.head_object(_BUCKET, _KEY)
        assert stat.etag is not None
        assert str(stat.etag) != ''

    def test_storage_class_defaults_to_standard(self):
        from sgraph_ai_service_playwright__cli.aws.s3.enums.Enum__S3__Storage__Class import Enum__S3__Storage__Class
        client = S3__AWS__Client__In_Memory()
        client.add_bucket(_BUCKET)
        client.add_object(_BUCKET, _KEY, _BODY)
        stat = client.head_object(_BUCKET, _KEY)
        assert stat.storage_class == Enum__S3__Storage__Class.STANDARD


class TestGetObjectBody:

    def test_missing_object_returns_empty_bytes(self):
        client = S3__AWS__Client__In_Memory()
        client.add_bucket(_BUCKET)
        result = client.get_object_body(_BUCKET, 'missing.txt')
        assert result == b''

    def test_returns_body(self):
        client = S3__AWS__Client__In_Memory()
        client.add_bucket(_BUCKET)
        client.add_object(_BUCKET, _KEY, _BODY)
        result = client.get_object_body(_BUCKET, _KEY)
        assert result == _BODY


class TestStreamObject:

    def test_streams_chunks(self):
        client = S3__AWS__Client__In_Memory()
        client.add_bucket(_BUCKET)
        client.add_object(_BUCKET, _KEY, _BODY)
        chunks = list(client.stream_object(_BUCKET, _KEY, chunk_size=4))
        assert b''.join(chunks) == _BODY

    def test_missing_object_yields_nothing(self):
        client = S3__AWS__Client__In_Memory()
        client.add_bucket(_BUCKET)
        chunks = list(client.stream_object(_BUCKET, 'missing.txt'))
        assert chunks == []


class TestPresign:

    def test_returns_non_empty_url(self):
        client = S3__AWS__Client__In_Memory()
        client.add_bucket(_BUCKET)
        client.add_object(_BUCKET, _KEY, _BODY)
        url = client.generate_presigned_url(_BUCKET, _KEY)
        assert url != ''
        assert _BUCKET in url
        assert _KEY    in url

    def test_ttl_reflected_in_url(self):
        client = S3__AWS__Client__In_Memory()
        client.add_bucket(_BUCKET)
        client.add_object(_BUCKET, _KEY, _BODY)
        url = client.generate_presigned_url(_BUCKET, _KEY, ttl_seconds=7200)
        assert '7200' in url


class TestPutAndCopyDelete:

    def test_put_object_stores_body(self):
        client = S3__AWS__Client__In_Memory()
        client.add_bucket(_BUCKET)
        ok   = client.put_object(_BUCKET, 'new.txt', b'hello')
        body = client.get_object_body(_BUCKET, 'new.txt')
        assert ok   is True
        assert body == b'hello'

    def test_copy_object_duplicates_body(self):
        client = S3__AWS__Client__In_Memory()
        client.add_bucket(_BUCKET)
        client.add_object(_BUCKET, 'src.txt', b'data')
        ok   = client.copy_object(_BUCKET, 'src.txt', _BUCKET, 'dst.txt')
        body = client.get_object_body(_BUCKET, 'dst.txt')
        assert ok   is True
        assert body == b'data'

    def test_delete_object_removes_entry(self):
        client = S3__AWS__Client__In_Memory()
        client.add_bucket(_BUCKET)
        client.add_object(_BUCKET, 'del.txt', b'bye')
        ok     = client.delete_object(_BUCKET, 'del.txt')
        result = client.get_object_body(_BUCKET, 'del.txt')
        assert ok     is True
        assert result == b''


class TestBucketCreate:

    def test_creates_bucket(self):
        client = S3__AWS__Client__In_Memory()
        ok      = client.create_bucket('new-bucket-xyz')
        buckets = [str(b.name) for b in client.list_buckets()]
        assert ok                   is True
        assert 'new-bucket-xyz' in  buckets

    def test_get_bucket_region(self):
        client = S3__AWS__Client__In_Memory()
        client.add_bucket(_BUCKET, region='eu-west-1')
        region = client.get_bucket_region(_BUCKET)
        assert region == 'eu-west-1'

    def test_get_bucket_versioning(self):
        client = S3__AWS__Client__In_Memory()
        client.add_bucket(_BUCKET, versioning='Enabled')
        ver = client.get_bucket_versioning(_BUCKET)
        assert ver == 'Enabled'


class TestSearchObjects:

    def test_pattern_substring_match(self):
        client = S3__AWS__Client__In_Memory()
        client.add_bucket(_BUCKET)
        client.add_object(_BUCKET, 'logs/2026-05-17.log', b'a')
        client.add_object(_BUCKET, 'data/report.json',    b'b')
        matches = client.search_objects(_BUCKET, '', '2026-05-17')
        assert len(matches) == 1
        assert str(matches[0].key) == 'logs/2026-05-17.log'

    def test_glob_pattern_match(self):
        client = S3__AWS__Client__In_Memory()
        client.add_bucket(_BUCKET)
        client.add_object(_BUCKET, 'logs/2026-05-17.log', b'a')
        client.add_object(_BUCKET, 'logs/2026-05-16.log', b'b')
        client.add_object(_BUCKET, 'data/report.json',    b'c')
        matches = client.search_objects(_BUCKET, 'logs/', '*.log')
        keys = [str(m.key) for m in matches]
        assert 'logs/2026-05-17.log' in keys
        assert 'logs/2026-05-16.log' in keys
        assert 'data/report.json'    not in keys
