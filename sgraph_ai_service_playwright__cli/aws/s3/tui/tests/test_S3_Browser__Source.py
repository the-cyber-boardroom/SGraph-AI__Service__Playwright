# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI (tests) — s3 tui: S3_Browser__Source
# Drives the browser source with a fake S3__AWS__Client (subclass + override the
# three read methods) — no AWS, no mocks. Covers buckets, folders+files listing, and
# the object viewer (text, gzip-decompress, binary hex dump).
# ═══════════════════════════════════════════════════════════════════════════════

import gzip
from unittest import TestCase

from sgraph_ai_service_playwright__cli.aws.s3.service.S3__AWS__Client          import S3__AWS__Client
from sgraph_ai_service_playwright__cli.aws.s3.service.S3__Format__Detector     import S3__Format__Detector
from sgraph_ai_service_playwright__cli.aws.s3.tui.source.S3_Browser__Source    import S3_Browser__Source


class _FBucket:
    def __init__(self, name): self.name = name


class _FObj:
    def __init__(self, key, size=0, lm=''):
        self.key = key; self.size = size; self.last_modified = lm


class _FResp:
    def __init__(self, prefixes, objects):
        self.prefixes = prefixes; self.objects = objects


BODIES = {'a.json'   : b'{"x": 1}',                                                  # keyed by object key (bucket-agnostic fake)
          'logs/x.gz': gzip.compress(b'line-1\nline-2\n'),
          'blob.bin' : b'\x00\x01\xff\xfe\x10'}


class FakeS3(S3__AWS__Client):
    def list_buckets(self):
        return [_FBucket('bucket-1'), _FBucket('bucket-2')]

    def list_objects(self, bucket, prefix='', recursive=False):
        if prefix == '':
            return _FResp(['logs/'], [_FObj('a.json', 8, '2026-05-21')])
        return _FResp([], [_FObj('logs/x.gz', 40, '2026-05-21')])

    def get_object_body(self, bucket, key):
        return BODIES.get(key, b'')


def source():
    return S3_Browser__Source(client=FakeS3(), detector=S3__Format__Detector())


class test_S3_Browser__Source(TestCase):

    def test_list_buckets(self):
        entries = source().list_buckets()
        assert {e.name for e in entries} == {'bucket-1', 'bucket-2'}
        assert all(e.kind == 'bucket' for e in entries)

    def test_list_dir_folders_and_files(self):
        entries = source().list_dir('b', '')
        kinds   = {e.name: e.kind for e in entries}
        assert kinds['logs/']  == 'folder'
        assert kinds['a.json'] == 'file'

    def test_read_object_json_text(self):
        view = source().read_object('b', 'a.json')
        assert view.is_binary is False
        assert view.fmt       == 'json'
        assert '"x"'          in view.text

    def test_read_object_gzip_decompressed(self):
        view = source().read_object('b', 'logs/x.gz')
        assert view.gunzipped is True
        assert 'line-1'       in view.text

    def test_read_object_binary_hexdump(self):
        view = source().read_object('b', 'blob.bin')
        assert view.is_binary is True
        assert view.fmt       == 'binary'
        assert '00 01 ff'     in view.text
