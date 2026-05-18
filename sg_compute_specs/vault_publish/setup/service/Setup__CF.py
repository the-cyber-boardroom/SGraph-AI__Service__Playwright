# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — vault-publish setup: Setup__CF
# Drift-check + create for the wildcard CloudFront distribution.
#
# Mutation gate: SG_AWS__VAULT_PUBLISH__SETUP__ALLOW_MUTATIONS=1
# Delete gate:   SG_AWS__VAULT_PUBLISH__SETUP__ALLOW_DELETES=1
#
# The expected distribution has alias *.{zone} and origin = waker Lambda URL.
# create() fetches the Lambda URL from the live function URL config so this
# service is self-contained.
# ═══════════════════════════════════════════════════════════════════════════════

import os
from typing import Callable, Optional

from osbot_utils.type_safe.Type_Safe import Type_Safe

from sg_compute_specs.vault_publish.setup.collections.List__Schema__Setup__Issue import List__Schema__Setup__Issue
from sg_compute_specs.vault_publish.setup.schemas.Enum__Setup__State             import Enum__Setup__State
from sg_compute_specs.vault_publish.setup.schemas.Schema__Setup__Issue           import Schema__Setup__Issue
from sg_compute_specs.vault_publish.setup.schemas.Schema__Setup__CF__Report      import Schema__Setup__CF__Report
from sg_compute_specs.vault_publish.setup.service.Setup__Lambda                  import WAKER_LAMBDA_NAME


class Setup__CF(Type_Safe):
    _cf_client_factory     : Optional[Callable] = None
    _lambda_client_factory : Optional[Callable] = None

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

    # ── read ─────────────────────────────────────────────────────────────────

    def check(self, zone: str) -> Schema__Setup__CF__Report:
        alias    = f'*.{zone}'
        issues   = List__Schema__Setup__Issue()
        cf       = self._cf_client()
        dist     = cf.find_distribution_by_alias(alias)
        if not dist:
            issues.append(Schema__Setup__Issue(
                severity='error', area='cf',
                message=f'no distribution with alias {alias}'))
            return Schema__Setup__CF__Report(
                state=Enum__Setup__State.MISSING, zone=zone, issues=issues)

        alias_ok = alias in list(dist.aliases)
        cert_ok  = bool(str(dist.cert_arn))

        if not alias_ok:
            issues.append(Schema__Setup__Issue(severity='warn', area='cf',
                                               message=f'alias {alias} not in distribution'))
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
            cert_ok         = cert_ok,
            issues          = issues,
        )

    def status(self, zone: str) -> dict:
        alias = f'*.{zone}'
        dist  = self._cf_client().find_distribution_by_alias(alias)
        if not dist:
            return {'zone': zone, 'alias': alias, 'exists': 'no'}
        return {
            'zone'           : zone,
            'alias'          : alias,
            'distribution_id': str(dist.distribution_id),
            'domain_name'    : str(dist.domain_name),
            'status'         : str(dist.status),
            'cert_arn'       : str(dist.cert_arn),
        }

    # ── mutations ─────────────────────────────────────────────────────────────

    def create(self, zone: str, cert_arn: str) -> Schema__Setup__CF__Report:
        _require_mutations()
        from sgraph_ai_service_playwright__cli.aws.cf.collections.List__CF__Alias          import List__CF__Alias
        from sgraph_ai_service_playwright__cli.aws.cf.primitives.Safe_Str__CF__Domain_Name import Safe_Str__CF__Domain_Name
        from sgraph_ai_service_playwright__cli.aws.cf.primitives.Safe_Str__Cert__Arn       import Safe_Str__Cert__Arn
        from sgraph_ai_service_playwright__cli.aws.cf.schemas.Schema__CF__Create__Request  import Schema__CF__Create__Request

        lc       = self._lambda_client()
        url_info = lc.get_function_url(WAKER_LAMBDA_NAME)
        if not url_info.exists:
            issues = List__Schema__Setup__Issue()
            issues.append(Schema__Setup__Issue(
                severity='error', area='cf',
                message=f'Lambda function URL not found — run `setup lambda create` first'))
            return Schema__Setup__CF__Report(
                state=Enum__Setup__State.ERROR, zone=zone, issues=issues)

        waker_url     = str(url_info.function_url)
        origin_domain = waker_url.removeprefix('https://').rstrip('/')
        cf_req = Schema__CF__Create__Request(
            origin_domain = Safe_Str__CF__Domain_Name(origin_domain),
            cert_arn      = Safe_Str__Cert__Arn(cert_arn),
            aliases       = List__CF__Alias([f'*.{zone}']),
            comment       = f'vault-publish waker — {zone}',
        )
        self._cf_client().ensure_distribution(cf_req)
        return self.check(zone)

    def delete(self, zone: str) -> bool:
        _require_deletes()
        alias = f'*.{zone}'
        dist  = self._cf_client().find_distribution_by_alias(alias)
        if not dist:
            return False
        try:
            self._cf_client().delete_distribution(str(dist.distribution_id))
            return True
        except Exception:
            return False


# ── gates ─────────────────────────────────────────────────────────────────────

def _require_mutations():
    if not os.environ.get('SG_AWS__VAULT_PUBLISH__SETUP__ALLOW_MUTATIONS'):
        raise RuntimeError(
            'Set SG_AWS__VAULT_PUBLISH__SETUP__ALLOW_MUTATIONS=1 to allow CF mutations')


def _require_deletes():
    if not os.environ.get('SG_AWS__VAULT_PUBLISH__SETUP__ALLOW_DELETES'):
        raise RuntimeError(
            'Set SG_AWS__VAULT_PUBLISH__SETUP__ALLOW_DELETES=1 to allow CF deletes')
