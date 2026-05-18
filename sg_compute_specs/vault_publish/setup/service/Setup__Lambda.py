# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — vault-publish setup: Setup__Lambda
# Drift-check + deploy for the sg-compute-vault-publish-waker Lambda function.
#
# Mutation gate: SG_AWS__VAULT_PUBLISH__SETUP__ALLOW_MUTATIONS=1
# Delete gate:   SG_AWS__VAULT_PUBLISH__SETUP__ALLOW_DELETES=1
#
# EXPECTED_* constants mirror the values set in Vault_Publish__Service.bootstrap.
# ═══════════════════════════════════════════════════════════════════════════════

import os
from typing import Callable, Optional

from osbot_utils.type_safe.Type_Safe import Type_Safe

from sg_compute_specs.vault_publish.setup.collections.List__Schema__Setup__Issue   import List__Schema__Setup__Issue
from sg_compute_specs.vault_publish.setup.schemas.Enum__Setup__State               import Enum__Setup__State
from sg_compute_specs.vault_publish.setup.schemas.Schema__Setup__Issue             import Schema__Setup__Issue
from sg_compute_specs.vault_publish.setup.schemas.Schema__Setup__Lambda__Report    import Schema__Setup__Lambda__Report

WAKER_LAMBDA_NAME = 'sg-compute-vault-publish-waker'
WAKER_HANDLER     = 'sg_compute_specs.vault_publish.waker.lambda_entry.handler'
EXPECTED_RUNTIME  = 'python3.12'
EXPECTED_MEMORY   = 512
EXPECTED_TIMEOUT  = 60


class Setup__Lambda(Type_Safe):
    _lambda_client_factory : Optional[Callable] = None
    _deployer_factory      : Optional[Callable] = None

    def _lambda_client(self):
        if self._lambda_client_factory:
            return self._lambda_client_factory()
        from sgraph_ai_service_playwright__cli.aws.lambda_.service.Lambda__AWS__Client import Lambda__AWS__Client
        return Lambda__AWS__Client()

    def _deployer(self):
        if self._deployer_factory:
            return self._deployer_factory()
        from sgraph_ai_service_playwright__cli.aws.lambda_.service.Lambda__Deployer import Lambda__Deployer
        return Lambda__Deployer()

    # ── read ─────────────────────────────────────────────────────────────────

    def check(self) -> Schema__Setup__Lambda__Report:
        lc     = self._lambda_client()
        issues = List__Schema__Setup__Issue()
        exists = lc.exists(WAKER_LAMBDA_NAME)
        if not exists:
            issues.append(Schema__Setup__Issue(
                severity='error', area='lambda',
                message=f'{WAKER_LAMBDA_NAME} not deployed'))
            return Schema__Setup__Lambda__Report(
                state=Enum__Setup__State.MISSING, function_name=WAKER_LAMBDA_NAME, issues=issues)

        details  = lc.get_function_details(WAKER_LAMBDA_NAME)
        url_info = lc.get_function_url(WAKER_LAMBDA_NAME)

        handler_ok = details.handler      == WAKER_HANDLER
        runtime_ok = str(details.runtime) == EXPECTED_RUNTIME
        memory_ok  = details.memory_size  == EXPECTED_MEMORY
        timeout_ok = details.timeout      == EXPECTED_TIMEOUT
        url_exists = url_info.exists

        drifted = []
        if not handler_ok:
            drifted.append(f'handler: got {details.handler}')
        if not runtime_ok:
            drifted.append(f'runtime: got {details.runtime}')
        if not memory_ok:
            drifted.append(f'memory: got {details.memory_size}')
        if not timeout_ok:
            drifted.append(f'timeout: got {details.timeout}')
        if not url_exists:
            drifted.append('function URL missing')

        for msg in drifted:
            issues.append(Schema__Setup__Issue(severity='warn', area='lambda', message=msg))

        state = Enum__Setup__State.OK if not drifted else Enum__Setup__State.DRIFT
        return Schema__Setup__Lambda__Report(
            state          = state,
            function_name  = WAKER_LAMBDA_NAME,
            function_arn   = str(details.function_arn),
            function_exists= True,
            handler_ok     = handler_ok,
            runtime_ok     = runtime_ok,
            memory_ok      = memory_ok,
            timeout_ok     = timeout_ok,
            url_exists     = url_exists,
            function_url   = str(url_info.function_url) if url_exists else '',
            issues         = issues,
        )

    def status(self) -> dict:
        lc = self._lambda_client()
        if not lc.exists(WAKER_LAMBDA_NAME):
            return {'function_name': WAKER_LAMBDA_NAME, 'exists': 'no'}
        details  = lc.get_function_details(WAKER_LAMBDA_NAME)
        url_info = lc.get_function_url(WAKER_LAMBDA_NAME)
        return {
            'function_name' : WAKER_LAMBDA_NAME,
            'function_arn'  : str(details.function_arn),
            'runtime'       : str(details.runtime),
            'handler'       : details.handler,
            'memory_size'   : str(details.memory_size),
            'timeout'       : str(details.timeout),
            'last_modified' : details.last_modified,
            'code_size'     : str(details.code_size),
            'function_url'  : str(url_info.function_url) if url_info.exists else '(none)',
        }

    # ── mutations ─────────────────────────────────────────────────────────────

    def create(self, role_arn: str = '') -> Schema__Setup__Lambda__Report:
        _require_mutations()
        from sgraph_ai_service_playwright__cli.aws.lambda_.enums.Enum__Lambda__Runtime       import Enum__Lambda__Runtime
        from sgraph_ai_service_playwright__cli.aws.lambda_.primitives.Safe_Str__Lambda__Name import Safe_Str__Lambda__Name
        from sgraph_ai_service_playwright__cli.aws.lambda_.schemas.Schema__Lambda__Deploy__Request import Schema__Lambda__Deploy__Request

        vault_publish_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
        package_root      = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../..'))

        deploy_req = Schema__Lambda__Deploy__Request(
            name        = Safe_Str__Lambda__Name(WAKER_LAMBDA_NAME),
            folder_path = vault_publish_dir,
            handler     = WAKER_HANDLER,
            role_arn    = role_arn,
            runtime     = Enum__Lambda__Runtime.PYTHON_3_12,
            memory_size = EXPECTED_MEMORY,
            timeout     = EXPECTED_TIMEOUT,
            description = 'Vault Publish Waker — cold-start wake + proxy',
        )
        deploy_resp = self._deployer().deploy_from_folder(
            deploy_req,
            package_root  = package_root,
            extra_modules = ['osbot_utils', 'osbot_aws'],
        )
        if not deploy_resp.success:
            issues = List__Schema__Setup__Issue()
            issues.append(Schema__Setup__Issue(
                severity='error', area='lambda',
                message=f'deploy failed: {deploy_resp.message}'))
            return Schema__Setup__Lambda__Report(
                state=Enum__Setup__State.ERROR, function_name=WAKER_LAMBDA_NAME, issues=issues)

        lc = self._lambda_client()
        lc.ensure_function_url(WAKER_LAMBDA_NAME)
        return self.check()

    def update(self) -> Schema__Setup__Lambda__Report:
        _require_mutations()
        return self.create()

    def delete(self) -> bool:
        _require_deletes()
        lc = self._lambda_client()
        try:
            lc.delete_function_url(WAKER_LAMBDA_NAME)
        except Exception:
            pass
        resp = lc.delete_function(WAKER_LAMBDA_NAME)
        return resp.success


# ── gates ─────────────────────────────────────────────────────────────────────

def _require_mutations():
    if not os.environ.get('SG_AWS__VAULT_PUBLISH__SETUP__ALLOW_MUTATIONS'):
        raise RuntimeError(
            'Set SG_AWS__VAULT_PUBLISH__SETUP__ALLOW_MUTATIONS=1 to allow Lambda mutations')


def _require_deletes():
    if not os.environ.get('SG_AWS__VAULT_PUBLISH__SETUP__ALLOW_DELETES'):
        raise RuntimeError(
            'Set SG_AWS__VAULT_PUBLISH__SETUP__ALLOW_DELETES=1 to allow Lambda deletes')
