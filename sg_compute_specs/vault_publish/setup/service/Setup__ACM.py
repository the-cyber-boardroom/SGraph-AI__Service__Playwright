# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — vault-publish setup: Setup__ACM
# Read-only drift-check for the ACM wildcard certificate.
#
# CloudFront certs MUST live in us-east-1; all checks scan that region.
# Mutation gate: SG_AWS__VAULT_PUBLISH__SETUP__ALLOW_MUTATIONS=1
#
# Note: requesting a cert triggers DNS/email validation which requires manual
# action. create() requests the cert and immediately returns; the operator
# must complete validation before Setup__CF.create() can reference the ARN.
# ═══════════════════════════════════════════════════════════════════════════════

import os
from typing import Callable, Optional

from osbot_utils.type_safe.Type_Safe import Type_Safe

from sg_compute_specs.vault_publish.setup.collections.List__Schema__Setup__Issue import List__Schema__Setup__Issue
from sg_compute_specs.vault_publish.setup.schemas.Enum__Setup__State             import Enum__Setup__State
from sg_compute_specs.vault_publish.setup.schemas.Schema__Setup__Issue           import Schema__Setup__Issue
from sg_compute_specs.vault_publish.setup.schemas.Schema__Setup__ACM__Report     import Schema__Setup__ACM__Report

ACM_REGION = 'us-east-1'


class Setup__ACM(Type_Safe):
    _acm_client_factory : Optional[Callable] = None

    def _acm_client(self):
        if self._acm_client_factory:
            return self._acm_client_factory()
        from sgraph_ai_service_playwright__cli.aws.acm.service.ACM__AWS__Client import ACM__AWS__Client
        return ACM__AWS__Client()

    # ── read ─────────────────────────────────────────────────────────────────

    def check(self, zone: str) -> Schema__Setup__ACM__Report:
        wildcard = f'*.{zone}'
        issues   = List__Schema__Setup__Issue()
        acm      = self._acm_client()
        cert     = self._find_cert(acm, wildcard)
        if not cert:
            issues.append(Schema__Setup__Issue(
                severity='error', area='acm',
                message=f'no ISSUED certificate for {wildcard} in {ACM_REGION}'))
            return Schema__Setup__ACM__Report(
                state=Enum__Setup__State.MISSING, zone=zone, issues=issues)

        status_ok = cert.status == 'ISSUED'
        if not status_ok:
            issues.append(Schema__Setup__Issue(
                severity='warn', area='acm',
                message=f'certificate status is {cert.status} — expected ISSUED'))

        state = Enum__Setup__State.OK if status_ok else Enum__Setup__State.DRIFT
        return Schema__Setup__ACM__Report(
            state       = state,
            zone        = zone,
            cert_arn    = cert.arn,
            cert_exists = True,
            cert_status = cert.status,
            issues      = issues,
        )

    def status(self, zone: str) -> dict:
        wildcard = f'*.{zone}'
        acm      = self._acm_client()
        cert     = self._find_cert(acm, wildcard)
        if not cert:
            return {'zone': zone, 'wildcard': wildcard, 'exists': 'no', 'region': ACM_REGION}
        return {
            'zone'       : zone,
            'wildcard'   : wildcard,
            'cert_arn'   : cert.arn,
            'status'     : cert.status,
            'domain_name': cert.domain_name,
            'region'     : ACM_REGION,
        }

    # ── mutations ─────────────────────────────────────────────────────────────

    def request(self, zone: str) -> Schema__Setup__ACM__Report:
        _require_mutations()
        import boto3
        wildcard = f'*.{zone}'
        acm      = boto3.client('acm', region_name=ACM_REGION)
        resp     = acm.request_certificate(
            DomainName              = wildcard,
            ValidationMethod        = 'DNS',
            SubjectAlternativeNames = [wildcard, zone],
        )
        arn    = resp.get('CertificateArn', '')
        issues = List__Schema__Setup__Issue()
        issues.append(Schema__Setup__Issue(
            severity='info', area='acm',
            message=f'certificate requested — complete DNS validation before using ARN: {arn}'))
        return Schema__Setup__ACM__Report(
            state=Enum__Setup__State.DRIFT, zone=zone, cert_arn=arn, cert_exists=True,
            cert_status='PENDING_VALIDATION', issues=issues)

    # ── internal ─────────────────────────────────────────────────────────────

    def _find_cert(self, acm, wildcard: str):
        for cert in acm.list_certificates(region=ACM_REGION):
            if cert.domain_name == wildcard and cert.status == 'ISSUED':
                return cert
        return None


# ── gate ──────────────────────────────────────────────────────────────────────

def _require_mutations():
    if not os.environ.get('SG_AWS__VAULT_PUBLISH__SETUP__ALLOW_MUTATIONS'):
        raise RuntimeError(
            'Set SG_AWS__VAULT_PUBLISH__SETUP__ALLOW_MUTATIONS=1 to allow ACM mutations')
