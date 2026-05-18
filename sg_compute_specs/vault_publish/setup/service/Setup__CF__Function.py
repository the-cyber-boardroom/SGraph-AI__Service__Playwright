# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — vault-publish setup: Setup__CF__Function
# Drift-check + create for the CloudFront Function that copies the viewer Host
# header into X-Forwarded-Host before CloudFront forwards to the Lambda
# Function URL origin. Without this, the waker only ever sees the Lambda URL
# hostname and can never parse a slug.
#
# Function name : vault-publish-viewer-host
# Runtime       : cloudfront-js-2.0
# Event type    : viewer-request (runs at CF edge before origin fetch)
#
# Async by design: attach_function_to_distribution() returns immediately;
# CloudFront edge propagation takes ~5min and is intentionally not awaited
# (run `sg vp setup cf-function check` later to verify, or use the AWS
# console to watch propagation).
#
# Mutation gate: SG_AWS__VAULT_PUBLISH__SETUP__ALLOW_MUTATIONS=1
# Delete gate:   SG_AWS__VAULT_PUBLISH__SETUP__ALLOW_DELETES=1
# ═══════════════════════════════════════════════════════════════════════════════

import os
from typing import Callable, Optional

from osbot_utils.type_safe.Type_Safe import Type_Safe

from sg_compute_specs.vault_publish.setup.collections.List__Schema__Setup__Issue       import List__Schema__Setup__Issue
from sg_compute_specs.vault_publish.setup.schemas.Enum__Setup__State                   import Enum__Setup__State
from sg_compute_specs.vault_publish.setup.schemas.Schema__Setup__Issue                 import Schema__Setup__Issue
from sg_compute_specs.vault_publish.setup.schemas.Schema__Setup__CF_Function__Report   import Schema__Setup__CF_Function__Report

FUNCTION_NAME    = 'vault-publish-viewer-host'
FUNCTION_COMMENT = 'Vault Publish — copy viewer Host into X-Forwarded-Host for the waker Lambda'
FUNCTION_RUNTIME = 'cloudfront-js-2.0'
EVENT_TYPE       = 'viewer-request'

# Keep on one logical line — _normalise() collapses whitespace so trivial
# formatting differences don't trigger a false drift signal.
FUNCTION_CODE = """\
function handler(event) {
    var req = event.request;
    if (req.headers.host) {
        req.headers['x-forwarded-host'] = { value: req.headers.host.value };
    }
    return req;
}
"""


class Setup__CF__Function(Type_Safe):
    _fn_client_factory   : Optional[Callable] = None
    _cf_client_factory   : Optional[Callable] = None

    def _fn_client(self):
        if self._fn_client_factory:
            return self._fn_client_factory()
        from sgraph_ai_service_playwright__cli.aws.cf.service.CloudFront__Function__AWS__Client import CloudFront__Function__AWS__Client
        return CloudFront__Function__AWS__Client()

    def _cf_client(self):
        if self._cf_client_factory:
            return self._cf_client_factory()
        from sgraph_ai_service_playwright__cli.aws.cf.service.CloudFront__AWS__Client import CloudFront__AWS__Client
        return CloudFront__AWS__Client()

    # ── read ─────────────────────────────────────────────────────────────────

    def check(self, zone: str) -> Schema__Setup__CF_Function__Report:
        issues = List__Schema__Setup__Issue()
        fn     = self._fn_client().describe(FUNCTION_NAME, stage='LIVE')
        if not fn.exists:
            issues.append(Schema__Setup__Issue(
                severity='error', area='cf-function',
                message=f'CloudFront Function {FUNCTION_NAME!r} not deployed'))
            return Schema__Setup__CF_Function__Report(
                state=Enum__Setup__State.MISSING, zone=zone,
                function_name=FUNCTION_NAME, issues=issues)

        live_code    = self._fn_client().get_code(FUNCTION_NAME, stage='LIVE')
        code_matches = _normalise(live_code) == _normalise(FUNCTION_CODE)
        if not code_matches:
            issues.append(Schema__Setup__Issue(
                severity='warn', area='cf-function',
                message='live code differs from expected — run `setup cf-function update`'))

        # Check distribution association
        attached    = False
        dist_id     = ''
        cf_dist     = self._cf_client().find_distribution_by_alias(f'*.{zone}')
        if cf_dist:
            dist_id  = str(cf_dist.distribution_id)
            attached = self._is_attached(dist_id, fn.arn)
            if not attached:
                issues.append(Schema__Setup__Issue(
                    severity='error', area='cf-function',
                    message=f'function not attached to distribution {dist_id} on {EVENT_TYPE}'))
        else:
            issues.append(Schema__Setup__Issue(
                severity='warn', area='cf-function',
                message=f'no CloudFront distribution for *.{zone} — cannot check attachment'))

        state = (Enum__Setup__State.OK if (code_matches and attached) else Enum__Setup__State.DRIFT)
        return Schema__Setup__CF_Function__Report(
            state           = state,
            zone            = zone,
            function_name   = FUNCTION_NAME,
            function_arn    = fn.arn,
            function_exists = True,
            function_stage  = fn.stage,
            code_matches    = code_matches,
            attached        = attached,
            distribution_id = dist_id,
            issues          = issues,
        )

    def status(self, zone: str) -> dict:
        fn = self._fn_client().describe(FUNCTION_NAME, stage='LIVE')
        if not fn.exists:
            return {'function_name': FUNCTION_NAME, 'exists': 'no'}
        dist_id  = ''
        attached = 'unknown'
        cf_dist  = self._cf_client().find_distribution_by_alias(f'*.{zone}')
        if cf_dist:
            dist_id  = str(cf_dist.distribution_id)
            attached = 'yes' if self._is_attached(dist_id, fn.arn) else 'no'
        return {
            'function_name'  : FUNCTION_NAME,
            'function_arn'   : fn.arn,
            'stage'          : fn.stage,
            'status'         : fn.status,
            'runtime'        : fn.runtime,
            'last_modified'  : fn.last_modified,
            'distribution_id': dist_id or '(none)',
            'attached'       : attached,
        }

    # ── mutations ─────────────────────────────────────────────────────────────

    def create(self, zone: str) -> Schema__Setup__CF_Function__Report:
        _require_mutations()
        fn_client = self._fn_client()

        # 1. ensure the DEVELOPMENT function exists with the expected code
        dev = fn_client.describe(FUNCTION_NAME, stage='DEVELOPMENT')
        if not dev.exists:
            fn_client.create(FUNCTION_NAME, code=FUNCTION_CODE,
                             comment=FUNCTION_COMMENT, runtime=FUNCTION_RUNTIME)
            dev = fn_client.describe(FUNCTION_NAME, stage='DEVELOPMENT')
        else:
            live_dev = fn_client.get_code(FUNCTION_NAME, stage='DEVELOPMENT')
            if _normalise(live_dev) != _normalise(FUNCTION_CODE):
                fn_client.update(FUNCTION_NAME, code=FUNCTION_CODE, etag=dev.etag,
                                 comment=FUNCTION_COMMENT, runtime=FUNCTION_RUNTIME)
                dev = fn_client.describe(FUNCTION_NAME, stage='DEVELOPMENT')

        # 2. publish DEVELOPMENT → LIVE
        fn_client.publish(FUNCTION_NAME, etag=dev.etag)
        live = fn_client.describe(FUNCTION_NAME, stage='LIVE')

        # 3. attach to the wildcard distribution (async — edge propagation ~5min)
        cf_dist = self._cf_client().find_distribution_by_alias(f'*.{zone}')
        if cf_dist:
            self._cf_client().attach_function_to_distribution(
                str(cf_dist.distribution_id), live.arn, event_type=EVENT_TYPE)

        return self.check(zone)

    def update(self, zone: str) -> Schema__Setup__CF_Function__Report:
        _require_mutations()
        return self.create(zone)                                                       # same flow — create() handles ensure+publish+attach

    def delete(self, zone: str) -> bool:
        _require_deletes()
        fn_client = self._fn_client()

        # 1. detach from the distribution (if any)
        cf_dist = self._cf_client().find_distribution_by_alias(f'*.{zone}')
        if cf_dist:
            try:
                self._cf_client().detach_function_from_distribution(
                    str(cf_dist.distribution_id), event_type=EVENT_TYPE)
            except Exception:
                pass

        # 2. delete the function — must use DEVELOPMENT etag and the function
        # must be UNASSOCIATED (post-edge-propagation). This commonly fails
        # for ~5min after detach; the operator can re-run later.
        for stage in ('DEVELOPMENT', 'LIVE'):
            meta = fn_client.describe(FUNCTION_NAME, stage=stage)
            if meta.exists and meta.etag:
                fn_client.delete(FUNCTION_NAME, etag=meta.etag)
        gone = not fn_client.describe(FUNCTION_NAME, stage='LIVE').exists
        return gone

    # ── internal ─────────────────────────────────────────────────────────────

    def _is_attached(self, distribution_id: str, function_arn: str) -> bool:
        try:
            arns = self._cf_client().get_function_associations(
                distribution_id, event_type=EVENT_TYPE)
        except Exception:
            return False
        # The qualified ARN includes a /function/<name> suffix and may differ
        # by version; we accept any association whose ARN starts with the
        # function ARN base (stripping any trailing /version qualifier).
        base = function_arn.split('/function/')[0] + '/function/' + FUNCTION_NAME
        return any(a.startswith(base) for a in arns)


def _normalise(code: str) -> str:
    # Strip whitespace differences so cosmetic edits don't trigger drift.
    return ''.join(code.split())


# ── gates ─────────────────────────────────────────────────────────────────────

def _require_mutations():
    if not os.environ.get('SG_AWS__VAULT_PUBLISH__SETUP__ALLOW_MUTATIONS'):
        raise RuntimeError(
            'Set SG_AWS__VAULT_PUBLISH__SETUP__ALLOW_MUTATIONS=1 to allow CF Function mutations')


def _require_deletes():
    if not os.environ.get('SG_AWS__VAULT_PUBLISH__SETUP__ALLOW_DELETES'):
        raise RuntimeError(
            'Set SG_AWS__VAULT_PUBLISH__SETUP__ALLOW_DELETES=1 to allow CF Function deletes')
