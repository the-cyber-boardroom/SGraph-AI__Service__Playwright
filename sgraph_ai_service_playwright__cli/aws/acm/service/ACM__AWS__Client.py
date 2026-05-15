# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — ACM__AWS__Client
# Sole boto3 boundary for ACM read operations. Every boto3 call for the acm
# sub-package lives here so Cli__Acm can stay pure Python + Type_Safe schemas
# and the in-memory test subclass has a small, well-defined surface.
#
# FOLLOW-UP: the rest of the repo forbids direct boto3 use (CLAUDE.md rule)
# and routes AWS operations through osbot-aws. No osbot-aws ACM wrapper
# exists at the time of writing. Keeping the entire client on raw boto3 gives
# us one import boundary, matching the Elastic__AWS__Client precedent. Migrate
# to osbot-aws once an ACM wrapper is available there.
#
# P0 surface: read-only (list_certificates, list_certificates__dual_region,
# describe_certificate). Mutation methods (request / delete) are P1+.
#
# Dual-region default: CloudFront certificates MUST live in us-east-1, so
# list_certificates__dual_region() scans both the current region and us-east-1
# and deduplicates by ARN.
# ═══════════════════════════════════════════════════════════════════════════════

from typing                                                                          import Optional

import boto3                                                                         # EXCEPTION — see module header

from osbot_utils.type_safe.Type_Safe                                                 import Type_Safe
from osbot_utils.type_safe.type_safe_core.decorators.type_safe                       import type_safe

from sgraph_ai_service_playwright__cli.aws.acm.collections.List__Schema__ACM__Certificate import List__Schema__ACM__Certificate
from sgraph_ai_service_playwright__cli.aws.acm.enums.Enum__ACM__Cert_Status               import Enum__ACM__Cert_Status
from sgraph_ai_service_playwright__cli.aws.acm.enums.Enum__ACM__Cert_Type                 import Enum__ACM__Cert_Type
from sgraph_ai_service_playwright__cli.aws.acm.schemas.Schema__ACM__Certificate           import Schema__ACM__Certificate

FALLBACK_REGION = 'eu-west-1'                                                        # Default region when boto3 session has no configured region
US_EAST_1       = 'us-east-1'                                                        # CloudFront certs must live here — always included in dual-region scan


class ACM__AWS__Client(Type_Safe):                                                   # Isolated boto3 boundary for ACM read operations

    def client(self, region: str = None):                                             # Single seam — tests override to return a fake client
        return boto3.client('acm', region_name=region or self.current_region())

    def current_region(self) -> str:                                                  # Returns the configured boto3 region, falling back to eu-west-1
        region = boto3.session.Session().region_name
        return region if region else FALLBACK_REGION

    @type_safe
    def list_certificates(self, region: str = None) -> List__Schema__ACM__Certificate:  # Paginate ACM certs + describe each; region field filled from param
        effective_region = region or self.current_region()
        acm              = self.client(effective_region)
        certs            = List__Schema__ACM__Certificate()
        paginator        = acm.get_paginator('list_certificates')
        for page in paginator.paginate():
            for summary in page.get('CertificateSummaryList', []):
                arn  = summary.get('CertificateArn', '')
                cert = self.describe_certificate(arn, region=effective_region)
                if cert is not None:
                    certs.append(cert)
        return certs

    def list_certificates__dual_region(self) -> List__Schema__ACM__Certificate:      # Scan current region + us-east-1; deduplicate by ARN
        seen   = set()
        result = List__Schema__ACM__Certificate()
        for region in (self.current_region(), US_EAST_1):
            for cert in self.list_certificates(region=region):
                arn = cert.arn
                if arn not in seen:
                    seen.add(arn)
                    result.append(cert)
        return result

    @type_safe
    def describe_certificate(self, arn: str, region: str = None) -> Optional[Schema__ACM__Certificate]:  # Describe a single cert by ARN; auto-detect region from ARN when region is None
        effective_region = region or self.region_from_arn(arn) or self.current_region()
        acm              = self.client(effective_region)
        try:
            resp = acm.describe_certificate(CertificateArn=arn)
        except Exception:
            return None
        raw  = resp.get('Certificate', {})
        return self.map_certificate(raw, effective_region)

    def map_certificate(self, raw: dict, region: str) -> Schema__ACM__Certificate:  # Map a raw boto3 Certificate dict to Schema__ACM__Certificate
        arn         = str(raw.get('CertificateArn', ''))
        domain      = str(raw.get('DomainName', ''))
        sans        = raw.get('SubjectAlternativeNames', [])
        san_count   = max(0, len(sans) - 1)                                           # SANs count excludes the primary domain (which is always first in the SAN list)
        in_use      = len(raw.get('InUseBy', []))
        status_raw  = str(raw.get('Status', 'INACTIVE'))
        type_raw    = str(raw.get('Type', 'AMAZON_ISSUED'))
        renewal     = str(raw.get('RenewalEligibility', '')) == 'ELIGIBLE'
        try:
            status = Enum__ACM__Cert_Status(status_raw)
        except ValueError:
            status = Enum__ACM__Cert_Status.INACTIVE
        try:
            cert_type = Enum__ACM__Cert_Type(type_raw)
        except ValueError:
            cert_type = Enum__ACM__Cert_Type.AMAZON_ISSUED
        return Schema__ACM__Certificate(arn              = arn       ,
                                        domain_name      = domain    ,
                                        san_count        = san_count ,
                                        status           = status    ,
                                        cert_type        = cert_type ,
                                        in_use_by        = in_use    ,
                                        renewal_eligible = renewal   ,
                                        region           = region    )

    def region_from_arn(self, arn: str) -> Optional[str]:                            # Extract region from ACM ARN: arn:aws:acm:<region>:<account>:certificate/<id>
        parts = arn.split(':')
        if len(parts) >= 4 and parts[3]:
            return parts[3]
        return None

    def get_validation_record_names(self, regions: list = None) -> set:              # Returns the set of DNS-01 validation record names (sans trailing dot) for every cert in the listed regions. Used by `zone check` to distinguish active ACM-validation CNAMEs from orphaned ones.
        if regions is None:
            regions = list({self.current_region(), 'us-east-1'})                      # Dedupe — current and us-east-1 are often the same
        names = set()
        for region in regions:
            try:
                acm = self.client(region)
                paginator = acm.get_paginator('list_certificates')
                for page in paginator.paginate():
                    for summary in page.get('CertificateSummaryList', []):
                        arn = summary.get('CertificateArn', '')
                        if not arn:
                            continue
                        try:
                            resp = acm.describe_certificate(CertificateArn=arn)
                        except Exception:
                            continue
                        cert = resp.get('Certificate', {})
                        for opt in cert.get('DomainValidationOptions', []):
                            rr   = opt.get('ResourceRecord') or {}
                            name = str(rr.get('Name', '')).rstrip('.')
                            if name:
                                names.add(name)
            except Exception:                                                         # Whole-region failure (e.g. region not enabled) — skip silently
                continue
        return names
