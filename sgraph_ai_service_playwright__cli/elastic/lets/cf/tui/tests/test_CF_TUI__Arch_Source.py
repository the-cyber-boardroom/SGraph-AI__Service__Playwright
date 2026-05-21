# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI (tests) — cf tui: CF_TUI__Arch_Source
# Drives the architecture source with fake AWS clients (subclass + override the list
# methods) — no AWS, no mocks. Covers the happy path and the graceful per-source
# error path (a raising client → an honest error string, not a crash).
# ═══════════════════════════════════════════════════════════════════════════════

from unittest import TestCase

from sgraph_ai_service_playwright__cli.aws.cf.service.CloudFront__AWS__Client import CloudFront__AWS__Client
from sgraph_ai_service_playwright__cli.aws.firehose.tests.test_Firehose__AWS__Client import FakeFirehose
from sgraph_ai_service_playwright__cli.aws.logs.service.Logs__AWS__Client     import Logs__AWS__Client
from sgraph_ai_service_playwright__cli.aws.logs.schemas.Schema__Logs__Group   import Schema__Logs__Group
from sgraph_ai_service_playwright__cli.aws.s3.service.S3__AWS__Client          import S3__AWS__Client
from sgraph_ai_service_playwright__cli.elastic.lets.cf.tui.source.CF_TUI__Arch_Source import CF_TUI__Arch_Source


class _FakeDist:                                                                     # duck-typed distribution (avoids Safe_Str construction)
    def __init__(self, did, domain, aliases, status, enabled=True):
        self.distribution_id = did
        self.domain_name     = domain
        self.aliases         = aliases
        self.status          = status
        self.enabled         = enabled


class FakeCF(CloudFront__AWS__Client):
    def list_distributions(self):
        return [_FakeDist('E1ABCDE2FGHIJK', 'd1abc.cloudfront.net', ['sgraph.ai'], 'Deployed'),
                _FakeDist('E2ZZZ', 'd2.cloudfront.net', [], 'Deployed', enabled=False)]


class FakeLogs(Logs__AWS__Client):
    def list_log_groups(self, prefix=''):
        return [Schema__Logs__Group(name='/aws/lambda/edge-waker', retention_days=7, stored_bytes=2048)]


class _FakeListResp:
    prefixes = ['cloudfront-realtime/2026/']
    objects  = []


class FakeS3(S3__AWS__Client):
    def list_objects(self, bucket, prefix='', recursive=False):
        return _FakeListResp()


class FakeCF_Err(CloudFront__AWS__Client):
    def list_distributions(self):
        raise RuntimeError('Unable to locate credentials')


def source(cf=None, logs=None, s3=None, firehose=None):
    return CF_TUI__Arch_Source(cf_client=cf or FakeCF(), logs_client=logs or FakeLogs(), s3_client=s3 or FakeS3(),
                               firehose_client=firehose or FakeFirehose(), bucket='b')


class test_CF_TUI__Arch_Source(TestCase):

    def test_happy_path(self):
        snap = source().snapshot()
        assert len(snap.distributions)       == 2
        assert snap.distributions[0].distribution_id == 'E1ABCDE2FGHIJK'
        assert snap.distributions[0].aliases         == 'sgraph.ai'
        assert snap.distributions[0].rt_log_status   == 'UNVERIFIED'
        assert snap.distributions[1].enabled         is False
        assert len(snap.log_groups)          == 1
        assert snap.bucket_reachable         is True
        assert snap.bucket_top_folders       == 1
        assert snap.cf_error                 == ''
        assert len(snap.firehose_streams)    == 1
        assert snap.firehose_streams[0].destination_bucket.endswith('cf-logs--eu-west-2')

    def test_cf_error_is_graceful(self):
        snap = source(cf=FakeCF_Err()).snapshot()
        assert snap.distributions  == []
        assert 'credentials' in snap.cf_error                                        # honest error, no crash
        assert snap.bucket_reachable is True                                         # other sources still read
