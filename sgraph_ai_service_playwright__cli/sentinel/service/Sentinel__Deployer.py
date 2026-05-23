# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Sentinel__Deployer
# Composes the existing aws/* clients (no new boto3 seam) into the live SG/Sentinel
# stack: an S3 log bucket, the L1 CloudFront Function (viewer-request), and the L2
# Lambda@Edge (origin-request) on a cache-disabled ephemeral distribution. The L1
# JS is materialised with BANNED_IPS inlined; the L2 zip gets a generated
# _sentinel_config.py (Lambda@Edge has no env vars).
#
# Live L@E packaging (full dependency zip) + replica-deletion timing are validated
# by the gated Phase-5 smoke test; the create/destroy/teardown lifecycle here is
# fully unit-tested via Sentinel__Deployer__In_Memory (no AWS, no network).
# ═══════════════════════════════════════════════════════════════════════════════

import os
import shutil
import tempfile
import time

from osbot_utils.type_safe.Type_Safe                import Type_Safe
from osbot_utils.type_safe.primitives.core.Safe_Str import Safe_Str

from sgraph_ai_service_playwright__cli.aws._shared.auth                                import AWS__Role__Profiles as profiles
from sgraph_ai_service_playwright__cli.aws.cf.primitives.Safe_Str__CF__Domain_Name     import Safe_Str__CF__Domain_Name
from sgraph_ai_service_playwright__cli.aws.cf.schemas.Schema__CF__Create__Request      import Schema__CF__Create__Request
from sgraph_ai_service_playwright__cli.aws.cf.service.CloudFront__AWS__Client          import CloudFront__AWS__Client
from sgraph_ai_service_playwright__cli.aws.cf.service.CloudFront__Function__AWS__Client import CloudFront__Function__AWS__Client
from sgraph_ai_service_playwright__cli.aws.lambda_.schemas.Schema__Lambda__Deploy__Request import Schema__Lambda__Deploy__Request
from sgraph_ai_service_playwright__cli.aws.lambda_.service.Lambda__Deployer            import Lambda__Deployer
from sgraph_ai_service_playwright__cli.aws.s3.service.S3__AWS__Client                  import S3__AWS__Client
from sgraph_ai_service_playwright__cli.sentinel.runtime.layer1.Sentinel__L1__Source    import Sentinel__L1__Source
from sgraph_ai_service_playwright__cli.sentinel.schemas.Schema__Sentinel__Deploy__Request  import Schema__Sentinel__Deploy__Request
from sgraph_ai_service_playwright__cli.sentinel.schemas.Schema__Sentinel__Deploy__Response import Schema__Sentinel__Deploy__Response
from sgraph_ai_service_playwright__cli.sentinel.service.Sentinel__Role__Profile        import BUCKET_PREFIX, EDGE_FAMILY

_L1_NAME      = 'sg-sentinel-l1'
_L2_NAME      = 'sg-sentinel-l2'
_RULESET      = '0.1.0'


class Sentinel__Deployer(Type_Safe):
    cf_client       : CloudFront__AWS__Client
    cf_fn_client    : CloudFront__Function__AWS__Client
    lambda_deployer : Lambda__Deployer
    s3_client       : S3__AWS__Client
    region          : Safe_Str = Safe_Str('us-east-1')
    account_id      : Safe_Str = Safe_Str('')
    origin_domain   : Safe_Str__CF__Domain_Name = Safe_Str__CF__Domain_Name('example.com')   # ephemeral test-distribution origin

    # ── naming ───────────────────────────────────────────────────────────────

    def l1_name(self) -> str: return _L1_NAME
    def l2_name(self) -> str: return _L2_NAME

    def derive_bucket(self, req: Schema__Sentinel__Deploy__Request) -> str:
        if str(req.log_bucket):
            return str(req.log_bucket)
        acct = str(self.account_id) or 'acct'
        return f'{BUCKET_PREFIX}-{acct}'[:63]

    def edge_role_arn(self) -> str:
        profile = profiles.get_profile(EDGE_FAMILY)
        return profiles.role_arn(profile, str(self.account_id) or '000000000000')

    def layer2_dir(self) -> str:
        return os.path.join(os.path.dirname(os.path.dirname(__file__)), 'runtime', 'layer2')

    # ── create ──────────────────────────────────────────────────────────────

    def create(self, req: Schema__Sentinel__Deploy__Request) -> Schema__Sentinel__Deploy__Response:
        region          = str(req.region) or str(self.region)
        bucket          = self.derive_bucket(req)
        self.s3_client.create_bucket(bucket, region=region)
        cf_function_arn = self.publish_l1(req.comment and str(req.comment) or 'SG/Sentinel L1')
        lambda_arn      = self.publish_l2(bucket, region)
        distribution_id = str(req.distribution_id) or self.create_distribution(str(req.comment))
        self.cf_client.attach_function_to_distribution(distribution_id, cf_function_arn, 'viewer-request')
        self.cf_client.associate_lambda_edge(distribution_id, lambda_arn, 'origin-request')
        return Schema__Sentinel__Deploy__Response(distribution_id = distribution_id,
                                                  cf_function_arn = cf_function_arn,
                                                  lambda_edge_arn = lambda_arn,
                                                  log_bucket      = bucket,
                                                  status          = 'created')

    def publish_l1(self, comment: str) -> str:                                       # create-or-update then publish; returns LIVE ARN
        name     = self.l1_name()
        code     = Sentinel__L1__Source().materialised_source()
        existing = self.cf_fn_client.describe(name, stage='DEVELOPMENT')
        if existing.exists:
            fn = self.cf_fn_client.update(name, code, str(existing.etag), comment=comment)
        else:
            fn = self.cf_fn_client.create(name, code, comment=comment)
        published = self.cf_fn_client.publish(name, str(fn.etag))
        return str(published.arn)

    def publish_l2(self, bucket: str, region: str) -> str:                           # deploy + publish numbered version ARN (L@E)
        pkg = self.prepare_layer2_package(bucket, region)
        try:
            req = Schema__Lambda__Deploy__Request(name        = self.l2_name(),
                                                  folder_path = pkg,
                                                  handler     = 'lambda_handler.handler',
                                                  role_arn    = self.edge_role_arn(),
                                                  memory_size = 128,
                                                  timeout     = 5,
                                                  description = 'SG/Sentinel L2 (Lambda@Edge)')
            self.lambda_deployer.deploy_from_folder(req)
        finally:
            shutil.rmtree(pkg, ignore_errors=True)
        return self.lambda_deployer.publish_version(self.l2_name())

    def prepare_layer2_package(self, bucket: str, region: str) -> str:               # copy layer2 + write the generated config
        out = tempfile.mkdtemp(prefix='sg_sentinel_l2_')
        shutil.copytree(self.layer2_dir(), out, dirs_exist_ok=True,
                        ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
        with open(os.path.join(out, '_sentinel_config.py'), 'w') as fh:
            fh.write(f"LOG_BUCKET = {bucket!r}\nREGION = {region!r}\nRULESET_VERSION = {_RULESET!r}\n")
        return out

    def create_distribution(self, comment: str) -> str:                              # cache-disabled (builder pins CachingDisabled)
        resp = self.cf_client.create_distribution(Schema__CF__Create__Request(
            origin_domain = str(self.origin_domain),
            comment       = comment or 'SG/Sentinel ephemeral test distribution'))
        return str(resp.distribution_id)

    # ── destroy / teardown ────────────────────────────────────────────────────

    def destroy(self, distribution_id: str) -> Schema__Sentinel__Deploy__Response:   # remove distribution + edge resources; keep the log bucket
        self.cf_client.disassociate_lambda_edge(distribution_id, 'origin-request')
        self.cf_client.detach_function_from_distribution(distribution_id, 'viewer-request')
        self.cf_client.disable_distribution(distribution_id)
        self.cf_client.delete_distribution(distribution_id)
        self.delete_l1()
        self.delete_l2()
        return Schema__Sentinel__Deploy__Response(distribution_id=distribution_id, status='destroyed')

    def teardown(self, distribution_id: str, log_bucket: str = '') -> Schema__Sentinel__Deploy__Response:
        self.destroy(distribution_id)
        if log_bucket:
            self.s3_client.delete_bucket(log_bucket, force=True)                      # empty + delete — no orphans
        return Schema__Sentinel__Deploy__Response(distribution_id=distribution_id, log_bucket=log_bucket, status='torn down')

    def delete_l1(self) -> bool:
        fn = self.cf_fn_client.describe(self.l1_name(), stage='DEVELOPMENT')
        if not fn.exists:
            return False
        return self.cf_fn_client.delete(self.l1_name(), str(fn.etag))

    def delete_l2(self, retries: int = 6, wait_sec: int = 30) -> bool:               # L@E replicas delete asynchronously — retry
        lc = self.lambda_deployer.client()
        for attempt in range(retries):
            try:
                lc.delete_function(FunctionName=self.l2_name())
                return True
            except Exception:
                if attempt == retries - 1:
                    return False
                time.sleep(wait_sec)                                                 # wait for CloudFront to release the replica
        return False

    # ── status ─────────────────────────────────────────────────────────────────

    def status(self) -> dict:
        l1_exists = self.cf_fn_client.describe(self.l1_name(), stage='DEVELOPMENT').exists
        try:
            self.lambda_deployer.client().get_function(FunctionName=self.l2_name())
            l2_exists = True
        except Exception:
            l2_exists = False
        return {'l1_function': l1_exists, 'l2_lambda': l2_exists, 'region': str(self.region)}
