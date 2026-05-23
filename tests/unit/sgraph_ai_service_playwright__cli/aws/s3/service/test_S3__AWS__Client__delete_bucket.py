# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tests for S3__AWS__Client.delete_bucket / empty_bucket (Sentinel teardown)
# ═══════════════════════════════════════════════════════════════════════════════

from tests.unit.sgraph_ai_service_playwright__cli.aws.s3.service.S3__AWS__Client__In_Memory import S3__AWS__Client__In_Memory

_BUCKET = 'sg-sentinel-logs-acct'


def _client():
    return S3__AWS__Client__In_Memory().add_bucket(_BUCKET)


class TestEmptyBucket:
    def test_empty_removes_all_objects(self):
        c = _client()
        c.put_object(_BUCKET, 'a/1.json', b'{}')
        c.put_object(_BUCKET, 'a/2.json', b'{}')
        assert c.empty_bucket(_BUCKET) == 2
        assert len(c.list_objects(_BUCKET, '', recursive=True).objects) == 0


class TestDeleteBucket:
    def test_delete_empty_bucket(self):
        c = _client()
        assert c.delete_bucket(_BUCKET) is True
        assert _BUCKET not in c._bucket_store

    def test_delete_nonempty_without_force_fails(self):
        c = _client()
        c.put_object(_BUCKET, 'a/1.json', b'{}')
        assert c.delete_bucket(_BUCKET) is False                                     # BucketNotEmpty
        assert _BUCKET in c._bucket_store

    def test_force_empties_then_deletes(self):
        c = _client()
        c.put_object(_BUCKET, 'a/1.json', b'{}')
        assert c.delete_bucket(_BUCKET, force=True) is True
        assert _BUCKET not in c._bucket_store
