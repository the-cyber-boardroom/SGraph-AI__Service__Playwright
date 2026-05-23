# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Live ephemeral AWS smoke test (Target A, gated)
# Deploy → curl each canonical path → assert HTTP 403/404 for blocks and a log
# object landed in S3 for every request → teardown → assert no orphans.
#
# Gated on a real AWS account + the mutation gate; skips everywhere else (CI, web,
# local-without-creds). This is the executable record of the live procedure and the
# Phase-5 acceptance check; it never runs without explicit opt-in.
# ═══════════════════════════════════════════════════════════════════════════════

import os

import pytest

from sgraph_ai_service_playwright__cli.sentinel.schemas.Schema__Sentinel__Deploy__Request import Schema__Sentinel__Deploy__Request
from sgraph_ai_service_playwright__cli.sentinel.service.Sentinel__Deployer                import Sentinel__Deployer

CANONICAL = [('GET', '/etc/passwd',   403),
             ('GET', '/wp-login.php', 404),
             ('GET', '/.env',         404),
             ('GET', '/index.html',   200)]


def _live() -> bool:
    return (os.environ.get('SG_SENTINEL__LIVE_TESTS', '') == '1' and
            os.environ.get('SG_AWS__SENTINEL__ALLOW_MUTATIONS', '') == '1')


@pytest.mark.skipif(not _live(), reason='live smoke needs SG_SENTINEL__LIVE_TESTS=1 + SG_AWS__SENTINEL__ALLOW_MUTATIONS=1')
class TestLiveSmoke:
    def test_deploy_curl_teardown_no_orphans(self):
        import time

        import requests

        from sgraph_ai_service_playwright__cli.aws._shared.auth.Aws__Session__Factory import boto3_client_via_context

        region   = os.environ.get('AWS_REGION', 'us-east-1')
        account  = str(boto3_client_via_context('sts').get_caller_identity().get('Account', ''))
        deployer = Sentinel__Deployer(region=region, account_id=account)

        resp = deployer.create(Schema__Sentinel__Deploy__Request(region=region))
        try:
            dist   = deployer.cf_client.get_distribution(str(resp.distribution_id))
            domain = str(dist.domain_name)
            deployer.cf_client.wait_deployed(str(resp.distribution_id))               # ~15 min on first deploy

            for method, path, expected in CANONICAL:
                r = requests.request(method, f'https://{domain}{path}', allow_redirects=False, timeout=20)
                if expected >= 400:
                    assert r.status_code == expected, f'{path}: expected {expected}, got {r.status_code}'

            time.sleep(5)                                                             # allow the L@E S3 write to settle
            objects = deployer.s3_client.list_objects(str(resp.log_bucket), '', recursive=True).objects
            assert len(objects) >= len(CANONICAL), 'expected a log object per request'
        finally:
            deployer.teardown(str(resp.distribution_id), log_bucket=str(resp.log_bucket))

        assert str(resp.log_bucket) not in [str(b.name) for b in deployer.s3_client.list_buckets()]
