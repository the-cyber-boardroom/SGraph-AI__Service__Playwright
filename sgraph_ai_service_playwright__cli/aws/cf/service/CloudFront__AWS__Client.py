# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — CloudFront__AWS__Client
# Sole boto3 boundary for CloudFront operations.
#
# EXCEPTION — osbot_aws.aws.cloud_front.Cloud_Front only covers list_distributions
# and invalidate_paths at the time of writing. Dev must implement create /
# disable / delete / wait here until upstream adds those methods. Remove once
# osbot-aws covers the full CRUD surface.
#
# All calls use us-east-1 (CloudFront is a global service fronted from IAD).
# ═══════════════════════════════════════════════════════════════════════════════

import time

import boto3                                                                          # EXCEPTION — see module header

from osbot_utils.type_safe.Type_Safe                                                    import Type_Safe

from sgraph_ai_service_playwright__cli.aws.cf.collections.List__CF__Alias                import List__CF__Alias
from sgraph_ai_service_playwright__cli.aws.cf.collections.List__Schema__CF__Distribution import List__Schema__CF__Distribution
from sgraph_ai_service_playwright__cli.aws.cf.enums.Enum__CF__Distribution__Status       import Enum__CF__Distribution__Status
from sgraph_ai_service_playwright__cli.aws.cf.enums.Enum__CF__Price__Class               import Enum__CF__Price__Class
from sgraph_ai_service_playwright__cli.aws.cf.primitives.Safe_Str__CF__Distribution_Id   import Safe_Str__CF__Distribution_Id
from sgraph_ai_service_playwright__cli.aws.cf.primitives.Safe_Str__CF__Domain_Name       import Safe_Str__CF__Domain_Name
from sgraph_ai_service_playwright__cli.aws.cf.primitives.Safe_Str__Cert__Arn             import Safe_Str__Cert__Arn
from sgraph_ai_service_playwright__cli.aws.cf.schemas.Schema__CF__Action__Response       import Schema__CF__Action__Response
from sgraph_ai_service_playwright__cli.aws.cf.schemas.Schema__CF__Create__Request        import Schema__CF__Create__Request
from sgraph_ai_service_playwright__cli.aws.cf.schemas.Schema__CF__Create__Response       import Schema__CF__Create__Response
from sgraph_ai_service_playwright__cli.aws.cf.schemas.Schema__CF__Distribution           import Schema__CF__Distribution
from sgraph_ai_service_playwright__cli.aws.cf.service.CloudFront__Distribution__Builder  import CloudFront__Distribution__Builder


class CloudFront__AWS__Client(Type_Safe):

    def client(self):                                                                  # Single boto3 seam — subclass overrides to inject fake
        return boto3.client('cloudfront', region_name='us-east-1')

    # ── read ──────────────────────────────────────────────────────────────────

    def list_distributions(self) -> List__Schema__CF__Distribution:
        cf     = self.client()
        items  = []
        kwargs = {}
        while True:
            resp  = cf.list_distributions(**kwargs)
            dl    = resp.get('DistributionList', {})
            items.extend(dl.get('Items', []))
            if not dl.get('IsTruncated', False):
                break
            kwargs = {'Marker': dl['NextMarker']}
        result = List__Schema__CF__Distribution()
        for item in items:
            result.append(self._parse_distribution(item))
        return result

    def get_distribution(self, distribution_id: str) -> Schema__CF__Distribution:
        resp  = self.client().get_distribution(Id=distribution_id)
        dist  = resp.get('Distribution', {})
        return self._parse_distribution_detail(dist)

    # ── mutations ─────────────────────────────────────────────────────────────

    def create_distribution(self, req: Schema__CF__Create__Request) -> Schema__CF__Create__Response:
        aliases = List__CF__Alias(list(req.aliases))
        builder = CloudFront__Distribution__Builder(
            origin_domain = str(req.origin_domain),
            cert_arn      = str(req.cert_arn),
            aliases       = aliases,
            comment       = req.comment,
            price_class   = req.price_class,
            enabled       = req.enabled,
        )
        config = builder.build()
        resp   = self.client().create_distribution(DistributionConfig=config)
        dist   = resp.get('Distribution', {})
        return Schema__CF__Create__Response(
            distribution_id = Safe_Str__CF__Distribution_Id(dist.get('Id', '')),
            domain_name     = Safe_Str__CF__Domain_Name(dist.get('DomainName', '')),
            status          = self._parse_status(dist.get('Status', '')),
            message         = 'created',
        )

    def disable_distribution(self, distribution_id: str) -> Schema__CF__Action__Response:
        cf = self.client()
        try:
            config_resp = cf.get_distribution_config(Id=distribution_id)
            etag        = config_resp['ETag']
            config      = config_resp['DistributionConfig']
            config['Enabled'] = False
            cf.update_distribution(Id=distribution_id, DistributionConfig=config, IfMatch=etag)
            return Schema__CF__Action__Response(
                distribution_id = Safe_Str__CF__Distribution_Id(distribution_id),
                success         = True,
                message         = 'disabled',
            )
        except Exception as e:
            return Schema__CF__Action__Response(
                distribution_id = Safe_Str__CF__Distribution_Id(distribution_id),
                success         = False,
                message         = str(e),
            )

    def delete_distribution(self, distribution_id: str) -> Schema__CF__Action__Response:
        cf = self.client()
        try:
            dist_resp = cf.get_distribution(Id=distribution_id)
            etag      = dist_resp['ETag']
            cf.delete_distribution(Id=distribution_id, IfMatch=etag)
            return Schema__CF__Action__Response(
                distribution_id = Safe_Str__CF__Distribution_Id(distribution_id),
                success         = True,
                message         = 'deleted',
            )
        except Exception as e:
            return Schema__CF__Action__Response(
                distribution_id = Safe_Str__CF__Distribution_Id(distribution_id),
                success         = False,
                message         = str(e),
            )

    def wait_deployed(self, distribution_id: str,
                      timeout_sec: int = 900, poll_sec: int = 30) -> Schema__CF__Action__Response:
        deadline = time.time() + timeout_sec
        while time.time() < deadline:
            dist = self.get_distribution(distribution_id)
            if dist.status == Enum__CF__Distribution__Status.DEPLOYED:
                return Schema__CF__Action__Response(
                    distribution_id = dist.distribution_id,
                    success         = True,
                    message         = 'deployed',
                )
            time.sleep(poll_sec)
        return Schema__CF__Action__Response(
            distribution_id = Safe_Str__CF__Distribution_Id(distribution_id),
            success         = False,
            message         = f'timed out after {timeout_sec}s',
        )

    # ── internal ──────────────────────────────────────────────────────────────

    def _parse_status(self, raw: str) -> Enum__CF__Distribution__Status:
        try:
            return Enum__CF__Distribution__Status(raw)
        except ValueError:
            return Enum__CF__Distribution__Status.IN_PROGRESS

    def _parse_price_class(self, raw: str) -> Enum__CF__Price__Class:
        try:
            return Enum__CF__Price__Class(raw)
        except ValueError:
            return Enum__CF__Price__Class.PriceClass_All

    def _parse_distribution(self, item: dict) -> Schema__CF__Distribution:
        cert   = item.get('ViewerCertificate', {})
        arn    = cert.get('ACMCertificateArn', '')
        return Schema__CF__Distribution(
            distribution_id = Safe_Str__CF__Distribution_Id(item.get('Id', '')),
            domain_name     = Safe_Str__CF__Domain_Name(item.get('DomainName', '')),
            status          = self._parse_status(item.get('Status', '')),
            comment         = item.get('Comment', ''),
            enabled         = item.get('Enabled', True),
            cert_arn        = Safe_Str__Cert__Arn(arn) if arn else Safe_Str__Cert__Arn(''),
            price_class     = self._parse_price_class(item.get('PriceClass', '')),
            aliases         = List__CF__Alias(item.get('Aliases', {}).get('Items', [])),
            created_time    = str(item.get('LastModifiedTime', '')),
        )

    def _parse_distribution_detail(self, dist: dict) -> Schema__CF__Distribution:
        dc = dist.get('DistributionConfig', {})
        return self._parse_distribution({
            'Id'             : dist.get('Id', ''),
            'DomainName'     : dist.get('DomainName', ''),
            'Status'         : dist.get('Status', ''),
            'Comment'        : dc.get('Comment', ''),
            'Enabled'        : dc.get('Enabled', True),
            'ViewerCertificate': dc.get('ViewerCertificate', {}),
            'PriceClass'     : dc.get('PriceClass', ''),
            'Aliases'        : dc.get('Aliases', {}),
            'LastModifiedTime': dist.get('LastModifiedTime', ''),
        })
