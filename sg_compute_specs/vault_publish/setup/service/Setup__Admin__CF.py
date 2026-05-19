# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — vault-publish setup: Setup__Admin__CF
# Drift-check + create for the vp-admin CloudFront distribution AND its
# dedicated single-host ACM cert.
#
# Why one piece (cert + CF combined): the cert is tightly bound to this
# distribution — only used here, lifetime matches the distribution, and the
# critical "must not be the wildcard cert" guard is enforced at this layer.
# Splitting them would create a leaky abstraction.
#
# H2 coalescing guard (the entire reason this distribution exists separately
# from the waker's wildcard CF): the cert used here MUST cover ONLY
# vp-admin.aws.sg-labs.app, NOT *.aws.sg-labs.app. If the wildcard cert is
# ever attached, browsers would coalesce H2 connections between the slug
# FQDNs and the admin host, re-introducing the DNS-pinning problem the split
# is designed to solve.
#
# CloudFront certs MUST live in us-east-1 regardless of where the rest of
# the infrastructure is — that's an AWS constraint.
#
# Mutation gate: SG_AWS__VAULT_PUBLISH__SETUP__ALLOW_MUTATIONS=1
# Delete gate:   SG_AWS__VAULT_PUBLISH__SETUP__ALLOW_DELETES=1
# ═══════════════════════════════════════════════════════════════════════════════

import os
import time
from typing import Callable, Optional

from osbot_utils.type_safe.Type_Safe import Type_Safe

from sg_compute_specs.vault_publish.setup.collections.List__Schema__Setup__Issue import List__Schema__Setup__Issue
from sg_compute_specs.vault_publish.setup.schemas.Enum__Setup__State             import Enum__Setup__State
from sg_compute_specs.vault_publish.setup.schemas.Schema__Setup__Issue           import Schema__Setup__Issue
from sg_compute_specs.vault_publish.setup.schemas.Schema__Setup__CF__Report      import Schema__Setup__CF__Report
from sg_compute_specs.vault_publish.setup.service.Setup__Admin__Lambda           import ADMIN_LAMBDA_NAME

ACM_REGION = 'us-east-1'                                                              # CloudFront-bound certs MUST be in us-east-1


def _admin_host(zone: str) -> str:
    # Single source of truth — change here if the host name ever moves.
    return f'vp-admin.{zone}'


class Setup__Admin__CF(Type_Safe):
    _cf_client_factory     : Optional[Callable] = None
    _lambda_client_factory : Optional[Callable] = None
    _acm_client_factory    : Optional[Callable] = None

    def _cf_client(self):
        if self._cf_client_factory:
            return self._cf_client_factory()
        from sgraph_ai_service_playwright__cli.aws.cf.service.CloudFront__AWS__Client import CloudFront__AWS__Client
        return CloudFront__AWS__Client()

    def _lambda_client(self):
        if self._lambda_client_factory:
            return self._lambda_client_factory()
        from sgraph_ai_service_playwright__cli.aws.lambda_.service.Lambda__AWS__Client import Lambda__AWS__Client
        return Lambda__AWS__Client()

    def _acm_client(self):
        if self._acm_client_factory:
            return self._acm_client_factory()
        from sgraph_ai_service_playwright__cli.aws.acm.service.ACM__AWS__Client import ACM__AWS__Client
        return ACM__AWS__Client()

    # ── read ─────────────────────────────────────────────────────────────────

    def check(self, zone: str) -> Schema__Setup__CF__Report:
        host   = _admin_host(zone)
        issues = List__Schema__Setup__Issue()
        cf     = self._cf_client()
        dist   = cf.find_distribution_by_alias(host)
        if not dist:
            issues.append(Schema__Setup__Issue(
                severity='error', area='cf',
                message=f'no distribution with alias {host} — run `setup admin-cf create`'))
            return Schema__Setup__CF__Report(
                state=Enum__Setup__State.MISSING, zone=zone, issues=issues)

        alias_ok = host in list(dist.aliases)
        cert_arn = str(dist.cert_arn)
        cert_ok  = bool(cert_arn)

        # The critical coalescing-defeat check: cert SAN must NOT cover the
        # slug FQDNs.
        coalescing_safe = True
        if cert_arn:
            coalescing_safe = self._cert_is_single_host(cert_arn, host)
            if not coalescing_safe:
                issues.append(Schema__Setup__Issue(
                    severity='error', area='cf',
                    message=f'cert {cert_arn} covers *.{zone} — H2 coalescing will defeat the admin/waker split. Reissue with single-host cert and re-run admin-cf update.'))

        if not alias_ok:
            issues.append(Schema__Setup__Issue(severity='warn', area='cf',
                                               message=f'alias {host} not in distribution'))
        if not cert_ok:
            issues.append(Schema__Setup__Issue(severity='warn', area='cf',
                                               message='no certificate configured'))

        state = Enum__Setup__State.OK if not issues else Enum__Setup__State.DRIFT
        return Schema__Setup__CF__Report(
            state           = state,
            zone            = zone,
            distribution_id = str(dist.distribution_id),
            domain_name     = str(dist.domain_name),
            dist_exists     = True,
            alias_ok        = alias_ok,
            cert_ok         = cert_ok and coalescing_safe,
            issues          = issues,
        )

    def status(self, zone: str) -> dict:
        host = _admin_host(zone)
        dist = self._cf_client().find_distribution_by_alias(host)
        out  = {'zone': zone, 'host': host, 'admin_url': f'https://{host}/'}
        if not dist:
            out['exists'] = 'no'
        else:
            out.update({
                'distribution_id': str(dist.distribution_id),
                'domain_name'    : str(dist.domain_name),
                'status'         : str(dist.status),
                'cert_arn'       : str(dist.cert_arn),
                'coalescing_safe': self._cert_is_single_host(str(dist.cert_arn), host),
            })
        return out

    # ── mutations ─────────────────────────────────────────────────────────────

    def create(self, zone: str, *, cert_wait_timeout_sec: int = 1800,
               progress: Optional[Callable] = None) -> Schema__Setup__CF__Report:
        _require_mutations()
        host = _admin_host(zone)

        # 1) Ensure admin Lambda + Function URL exist (origin for the CF distribution).
        if progress: progress('check-origin', 'start')
        lc       = self._lambda_client()
        url_info = lc.get_function_url(ADMIN_LAMBDA_NAME)
        if not url_info.exists:
            issues = List__Schema__Setup__Issue()
            issues.append(Schema__Setup__Issue(
                severity='error', area='cf',
                message=f'admin Lambda function URL not found — run `sg vp setup admin-lambda create` first'))
            return Schema__Setup__CF__Report(state=Enum__Setup__State.ERROR, zone=zone, issues=issues)
        admin_lambda_url = str(url_info.function_url)
        if progress: progress('check-origin', f'done — {admin_lambda_url}')

        # 2) Ensure the single-host ACM cert for `host` exists + is ISSUED.
        if progress: progress('ensure-cert', 'start')
        cert_arn, cert_msg = self._ensure_single_host_cert(host, zone,
                                                           wait_timeout=cert_wait_timeout_sec,
                                                           progress=progress)
        if not cert_arn:
            issues = List__Schema__Setup__Issue()
            issues.append(Schema__Setup__Issue(severity='error', area='cf', message=cert_msg))
            return Schema__Setup__CF__Report(state=Enum__Setup__State.ERROR, zone=zone, issues=issues)
        if progress: progress('ensure-cert', f'done — {cert_arn}')

        # 3) Idempotent CF create / update with the validated cert.
        if progress: progress('ensure-cf', 'start')
        from sgraph_ai_service_playwright__cli.aws.cf.collections.List__CF__Alias          import List__CF__Alias
        from sgraph_ai_service_playwright__cli.aws.cf.primitives.Safe_Str__CF__Domain_Name import Safe_Str__CF__Domain_Name
        from sgraph_ai_service_playwright__cli.aws.cf.primitives.Safe_Str__Cert__Arn       import Safe_Str__Cert__Arn
        from sgraph_ai_service_playwright__cli.aws.cf.schemas.Schema__CF__Create__Request  import Schema__CF__Create__Request

        origin_domain = admin_lambda_url.removeprefix('https://').rstrip('/')
        cf_req = Schema__CF__Create__Request(
            origin_domain = Safe_Str__CF__Domain_Name(origin_domain),
            cert_arn      = Safe_Str__Cert__Arn(cert_arn),
            aliases       = List__CF__Alias([host]),
            comment       = f'vault-publish admin — {host}',
        )
        self._cf_client().ensure_distribution(cf_req)
        if progress: progress('ensure-cf', 'done')

        return self.check(zone)

    def update(self, zone: str, *, progress: Optional[Callable] = None) -> Schema__Setup__CF__Report:
        # Same path as create — idempotent CF + cert ensure.
        return self.create(zone, progress=progress)

    def delete(self, zone: str) -> bool:
        _require_deletes()
        host = _admin_host(zone)
        dist = self._cf_client().find_distribution_by_alias(host)
        if not dist:
            return False
        try:
            self._cf_client().delete_distribution(str(dist.distribution_id))
            return True
        except Exception:
            return False

    # ── helpers ──────────────────────────────────────────────────────────────

    def _cert_is_single_host(self, cert_arn: str, expected_host: str) -> bool:
        # Returns True iff cert is for exactly `expected_host` (no wildcard SAN
        # covering *.aws.sg-labs.app). Best-effort — failures fail closed (return
        # False) so the check report flags suspect certs for the operator.
        try:
            import boto3
            acm    = boto3.client('acm', region_name=ACM_REGION)
            detail = acm.describe_certificate(CertificateArn=cert_arn)
            cert   = detail.get('Certificate', {}) or {}
            sans   = set(cert.get('SubjectAlternativeNames', []) or [])
            dn     = cert.get('DomainName', '')
            all_names = sans | {dn} if dn else sans
            # Reject if ANY name starts with '*.' — that's a wildcard.
            return all_names == {expected_host}
        except Exception:
            return False

    def _ensure_single_host_cert(self, host: str, zone: str, *,
                                  wait_timeout: int = 1800,
                                  progress: Optional[Callable] = None) -> tuple:
        # Find or request a single-host cert for `host`. Returns
        # (cert_arn, status_message). Empty cert_arn = failure with reason in
        # status_message.
        import boto3
        acm = boto3.client('acm', region_name=ACM_REGION)

        # 1) Look for an existing ISSUED single-host cert.
        existing = self._find_existing_single_host(acm, host)
        if existing:
            return existing, f'using existing cert {existing}'

        # 2) Request a new cert with DNS validation.
        if progress: progress('cert-request', host)
        resp     = acm.request_certificate(DomainName=host, ValidationMethod='DNS')
        cert_arn = resp.get('CertificateArn', '')
        if not cert_arn:
            return '', 'request_certificate returned no ARN'

        # 3) Wait briefly for AWS to populate the validation records, then
        # auto-add them to Route 53 in the parent zone.
        time.sleep(5)
        if progress: progress('cert-validation-dns', 'adding records to Route 53')
        if not self._add_validation_records(acm, cert_arn, zone):
            return cert_arn, ('cert requested but DNS validation records could not be added — '
                              'add manually via the AWS console')

        # 4) Poll until ISSUED or timeout.
        deadline = time.time() + wait_timeout
        while time.time() < deadline:
            detail = acm.describe_certificate(CertificateArn=cert_arn)
            status = detail.get('Certificate', {}).get('Status', '')
            if progress: progress('cert-poll', f'status={status} elapsed={int(time.time()-deadline+wait_timeout)}s')
            if status == 'ISSUED':
                return cert_arn, 'cert issued'
            if status == 'FAILED':
                return '', f'cert validation FAILED (arn: {cert_arn})'
            time.sleep(10)

        return '', f'cert {cert_arn} did not reach ISSUED within {wait_timeout}s — check ACM console'

    def _find_existing_single_host(self, acm, host: str) -> str:
        # Returns the ARN of an existing ISSUED cert for exactly `host`, or ''.
        # (Excludes any cert whose SAN list contains a wildcard.)
        paginator = acm.get_paginator('list_certificates')
        for page in paginator.paginate():
            for summary in page.get('CertificateSummaryList', []):
                arn = summary.get('CertificateArn', '')
                if not arn:
                    continue
                detail = acm.describe_certificate(CertificateArn=arn).get('Certificate', {})
                if detail.get('Status') != 'ISSUED':
                    continue
                dn   = detail.get('DomainName', '')
                sans = set(detail.get('SubjectAlternativeNames', []) or [])
                if dn == host and sans == {host}:
                    return arn
        return ''

    def _add_validation_records(self, acm, cert_arn: str, zone: str) -> bool:
        # Read the validation CNAMEs ACM published, then upsert each into the
        # parent zone via Route 53. Returns True on success.
        try:
            from sgraph_ai_service_playwright__cli.aws.dns.service.Route53__AWS__Client import Route53__AWS__Client
        except Exception:
            return False
        try:
            detail = acm.describe_certificate(CertificateArn=cert_arn).get('Certificate', {})
            opts   = detail.get('DomainValidationOptions', []) or []
            r53    = Route53__AWS__Client()
            zone_obj = r53.find_hosted_zone_by_name(zone)
            if not zone_obj:
                return False
            for opt in opts:
                rr = opt.get('ResourceRecord') or {}
                name  = rr.get('Name', '')
                value = rr.get('Value', '')
                rtype = rr.get('Type', 'CNAME')
                if name and value:
                    r53.upsert_record(str(zone_obj.zone_id), name, rtype, [value], ttl=60)
            return True
        except Exception:
            return False


# ── gates ─────────────────────────────────────────────────────────────────────

def _require_mutations():
    if not os.environ.get('SG_AWS__VAULT_PUBLISH__SETUP__ALLOW_MUTATIONS'):
        raise RuntimeError(
            'Set SG_AWS__VAULT_PUBLISH__SETUP__ALLOW_MUTATIONS=1 to allow admin-CF mutations')


def _require_deletes():
    if not os.environ.get('SG_AWS__VAULT_PUBLISH__SETUP__ALLOW_DELETES'):
        raise RuntimeError(
            'Set SG_AWS__VAULT_PUBLISH__SETUP__ALLOW_DELETES=1 to allow admin-CF deletes')
