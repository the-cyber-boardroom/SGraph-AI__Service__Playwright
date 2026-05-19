# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — vault-publish setup: Setup__Admin__Lambda
# Drift-check + deploy for the sg-compute-vault-publish-admin Lambda.
#
# Mirrors Setup__Lambda (waker) but with a different handler / role / env vars:
#   handler  = sg_compute_specs.vault_publish.lambdas.admin.lambda_entry.handler
#   role     = sg-compute-vault-publish-admin-role  (broader perms; managed by Setup__Admin__IAM)
#   env vars = ADMIN_SERVICE_VERSION, ADMIN_VERSION, etc. + the API-key pair
#              SG_VAULT_PUBLISH__ADMIN__API_KEY_NAME / _VALUE (auto-generated
#              on first create, preserved across updates).
#
# Memory / timeout slightly higher than waker because the admin runs longer
# operations (register can take 60-180s, includes EC2 boot wait + auto-DNS).
#
# Mutation gate: SG_AWS__VAULT_PUBLISH__SETUP__ALLOW_MUTATIONS=1
# Delete gate:   SG_AWS__VAULT_PUBLISH__SETUP__ALLOW_DELETES=1
# ═══════════════════════════════════════════════════════════════════════════════

import os
import uuid
from datetime import datetime, timezone
from typing import Callable, Optional

from osbot_utils.type_safe.Type_Safe import Type_Safe

from sg_compute_specs.vault_publish.setup.collections.List__Schema__Setup__Issue import List__Schema__Setup__Issue
from sg_compute_specs.vault_publish.setup.schemas.Enum__Setup__State             import Enum__Setup__State
from sg_compute_specs.vault_publish.setup.schemas.Schema__Setup__Issue           import Schema__Setup__Issue
from sg_compute_specs.vault_publish.setup.schemas.Schema__Setup__Lambda__Report  import Schema__Setup__Lambda__Report
from sg_compute_specs.vault_publish.setup.service.Setup__Lambda                  import _read_version, _git_commit, _caller_identity

ADMIN_LAMBDA_NAME = 'sg-compute-vault-publish-admin'
ADMIN_HANDLER     = 'sg_compute_specs.vault_publish.lambdas.admin.lambda_entry.handler'
EXPECTED_RUNTIME  = 'python3.12'
EXPECTED_MEMORY   = 768                                                                # admin does longer work than waker; modest bump
EXPECTED_TIMEOUT  = 300                                                                # 5 min — register w/ --wait can take up to 90s, head-room for retries


class Setup__Admin__Lambda(Type_Safe):
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
        from sgraph_ai_service_playwright__cli.aws._shared.Aws__Region__Resolver   import Aws__Region__Resolver
        from sgraph_ai_service_playwright__cli.aws.lambda_.service.Lambda__Deployer import Lambda__Deployer
        return Lambda__Deployer(region=str(Aws__Region__Resolver().resolve()))

    # ── read ─────────────────────────────────────────────────────────────────

    def check(self) -> Schema__Setup__Lambda__Report:
        lc     = self._lambda_client()
        issues = List__Schema__Setup__Issue()
        exists = lc.exists(ADMIN_LAMBDA_NAME)
        if not exists:
            issues.append(Schema__Setup__Issue(
                severity='error', area='lambda',
                message=f'{ADMIN_LAMBDA_NAME} not deployed'))
            return Schema__Setup__Lambda__Report(
                state=Enum__Setup__State.MISSING, function_name=ADMIN_LAMBDA_NAME, issues=issues)

        details  = lc.get_function_details(ADMIN_LAMBDA_NAME)
        url_info = lc.get_function_url(ADMIN_LAMBDA_NAME)

        handler_ok = details.handler      == ADMIN_HANDLER
        runtime_ok = str(details.runtime) == EXPECTED_RUNTIME
        memory_ok  = details.memory_size  == EXPECTED_MEMORY
        timeout_ok = details.timeout      == EXPECTED_TIMEOUT
        url_exists = url_info.exists

        drifted = []
        if not handler_ok: drifted.append(f'handler: got {details.handler}')
        if not runtime_ok: drifted.append(f'runtime: got {details.runtime}')
        if not memory_ok : drifted.append(f'memory: got {details.memory_size}')
        if not timeout_ok: drifted.append(f'timeout: got {details.timeout}')
        if not url_exists: drifted.append('function URL missing')
        for msg in drifted:
            issues.append(Schema__Setup__Issue(severity='warn', area='lambda', message=msg))

        env_live = getattr(details, 'environment', {}) or {}
        deploy_env_lines = '\n'.join(
            f'{k}: {env_live.get(k, "(unset)")}'
            for k in ('ADMIN_SERVICE_VERSION', 'ADMIN_VERSION', 'ADMIN_DEPLOYED_AT',
                       'ADMIN_DEPLOY_ID', 'ADMIN_DEPLOY_REGION', 'ADMIN_DEPLOYED_BY',
                       'ADMIN_GIT_COMMIT',
                       'SG_AWS__DNS__DEFAULT_ZONE',
                       'SG_VAULT_PUBLISH__ADMIN__API_KEY_NAME',
                       'SG_VAULT_PUBLISH__ADMIN__API_KEY_VALUE')
        )

        state = Enum__Setup__State.OK if not drifted else Enum__Setup__State.DRIFT
        return Schema__Setup__Lambda__Report(
            state          = state,
            function_name  = ADMIN_LAMBDA_NAME,
            function_arn   = str(details.function_arn),
            function_exists= True,
            handler_ok     = handler_ok,
            runtime_ok     = runtime_ok,
            memory_ok      = memory_ok,
            timeout_ok     = timeout_ok,
            url_exists     = url_exists,
            function_url   = str(url_info.function_url) if url_exists else '',
            runtime        = str(details.runtime),
            handler        = details.handler,
            memory_size    = int(details.memory_size or 0),
            timeout        = int(details.timeout or 0),
            code_size      = int(getattr(details, 'code_size', 0) or 0),
            last_modified  = str(details.last_modified or ''),
            deploy_env     = deploy_env_lines,
            issues         = issues,
        )

    def status(self) -> dict:
        lc = self._lambda_client()
        if not lc.exists(ADMIN_LAMBDA_NAME):
            return {'function_name': ADMIN_LAMBDA_NAME, 'exists': 'no'}
        details  = lc.get_function_details(ADMIN_LAMBDA_NAME)
        url_info = lc.get_function_url(ADMIN_LAMBDA_NAME)
        env      = getattr(details, 'environment', {}) or {}
        out = {
            'function_name' : ADMIN_LAMBDA_NAME,
            'function_arn'  : str(details.function_arn),
            'runtime'       : str(details.runtime),
            'handler'       : details.handler,
            'memory_size'   : str(details.memory_size),
            'timeout'       : str(details.timeout),
            'last_modified' : details.last_modified,
            'code_size'     : str(details.code_size),
            'function_url'  : str(url_info.function_url) if url_info.exists else '(none)',
        }
        for k in ('ADMIN_SERVICE_VERSION', 'ADMIN_VERSION', 'ADMIN_DEPLOYED_AT',
                   'ADMIN_DEPLOY_ID', 'ADMIN_DEPLOY_REGION', 'ADMIN_DEPLOYED_BY',
                   'ADMIN_GIT_COMMIT',
                   'SG_AWS__DNS__DEFAULT_ZONE',
                   'SG_VAULT_PUBLISH__ADMIN__API_KEY_NAME',
                   'SG_VAULT_PUBLISH__ADMIN__API_KEY_VALUE'):
            out[f'env.{k}'] = str(env.get(k, '(unset)'))
        return out

    # ── mutations ─────────────────────────────────────────────────────────────

    def create(self, role_arn: str = '', progress: Optional[Callable] = None) -> Schema__Setup__Lambda__Report:
        _require_mutations()
        from sgraph_ai_service_playwright__cli.aws.lambda_.enums.Enum__Lambda__Runtime       import Enum__Lambda__Runtime
        from sgraph_ai_service_playwright__cli.aws.lambda_.primitives.Safe_Str__Lambda__Name import Safe_Str__Lambda__Name
        from sgraph_ai_service_playwright__cli.aws.lambda_.schemas.Schema__Lambda__Deploy__Request import Schema__Lambda__Deploy__Request

        vault_publish_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
        package_root      = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../..'))

        if progress: progress('build-env', 'start')
        env = _build_admin_deploy_env(vault_publish_dir)
        if progress: progress('build-env', 'done')

        if not role_arn:
            # Resolve from the existing role via Setup__Admin__IAM. The role
            # must exist before create — surface a clear error otherwise.
            from sg_compute_specs.vault_publish.setup.service.Setup__Admin__IAM import Setup__Admin__IAM, ADMIN_ROLE_NAME
            iam_status = Setup__Admin__IAM().status()
            role_arn   = iam_status.get('arn', '')
            if not role_arn:
                issues = List__Schema__Setup__Issue()
                issues.append(Schema__Setup__Issue(
                    severity='error', area='lambda',
                    message=f'admin IAM role missing — run `sg vp setup admin-iam create` first ({ADMIN_ROLE_NAME})'))
                return Schema__Setup__Lambda__Report(
                    state=Enum__Setup__State.ERROR, function_name=ADMIN_LAMBDA_NAME, issues=issues)

        deploy_req = Schema__Lambda__Deploy__Request(
            name        = Safe_Str__Lambda__Name(ADMIN_LAMBDA_NAME),
            folder_path = vault_publish_dir,
            handler     = ADMIN_HANDLER,
            role_arn    = role_arn,
            runtime     = Enum__Lambda__Runtime.PYTHON_3_12,
            memory_size = EXPECTED_MEMORY,
            timeout     = EXPECTED_TIMEOUT,
            description = f'Vault Publish Admin - {env.get("ADMIN_VERSION", "?")} '
                          f'deployed {env.get("ADMIN_DEPLOYED_AT", "?")}',
        )
        # Admin Lambda needs fastapi + starlette + anyio for the FastAPI app.
        # Waker doesn't, so its deploy lists only osbot_utils / osbot_aws.
        deploy_resp = self._deployer().deploy_from_folder(
            deploy_req,
            package_root  = package_root,
            extra_modules = ['osbot_utils', 'osbot_aws', 'fastapi', 'starlette', 'anyio',
                              'pydantic', 'pydantic_core', 'typing_extensions',
                              'annotated_types', 'typing_inspection',
                              'sniffio', 'idna', 'python_multipart'],
            environment   = env,
            progress      = progress,
        )
        if not deploy_resp.success:
            issues = List__Schema__Setup__Issue()
            issues.append(Schema__Setup__Issue(
                severity='error', area='lambda',
                message=f'deploy failed: {deploy_resp.message}'))
            return Schema__Setup__Lambda__Report(
                state=Enum__Setup__State.ERROR, function_name=ADMIN_LAMBDA_NAME, issues=issues)

        lc = self._lambda_client()
        if progress: progress('ensure-url', 'start')
        lc.ensure_function_url(ADMIN_LAMBDA_NAME)
        if progress: progress('ensure-url', 'done')

        if progress: progress('check', 'start')
        report = self.check()
        if progress: progress('check', 'done')
        report.zip_size = int(getattr(deploy_resp, 'zip_size', 0) or 0)
        return report

    def update(self, progress: Optional[Callable] = None) -> Schema__Setup__Lambda__Report:
        _require_mutations()
        lc      = self._lambda_client()
        details = lc.get_function_details(ADMIN_LAMBDA_NAME)
        return self.create(role_arn=details.role_arn, progress=progress)

    def delete(self) -> bool:
        _require_deletes()
        lc = self._lambda_client()
        try:
            lc.delete_function_url(ADMIN_LAMBDA_NAME)
        except Exception:
            pass
        resp = lc.delete_function(ADMIN_LAMBDA_NAME)
        return resp.success


# ── deployment metadata ──────────────────────────────────────────────────────

def _build_admin_deploy_env(vault_publish_dir: str) -> dict:
    """Compose env vars baked into the admin Lambda config at deploy time."""
    from sgraph_ai_service_playwright__cli.aws._shared.Aws__Region__Resolver import Aws__Region__Resolver
    now       = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    repo_root = os.path.abspath(os.path.join(vault_publish_dir, '..', '..'))
    env = {
        'ADMIN_SERVICE_VERSION': _read_version(repo_root),
        'ADMIN_VERSION'        : _read_version(vault_publish_dir),
        'ADMIN_DEPLOYED_AT'    : now,
        'ADMIN_DEPLOY_ID'      : uuid.uuid4().hex[:16],
        'ADMIN_DEPLOY_REGION'  : str(Aws__Region__Resolver().resolve()),
        'ADMIN_DEPLOYED_BY'    : _caller_identity(),
        'ADMIN_GIT_COMMIT'     : _git_commit(),
    }
    zone = os.environ.get('SG_AWS__DNS__DEFAULT_ZONE', '')
    if zone:
        env['SG_AWS__DNS__DEFAULT_ZONE'] = zone

    # API key — preserve across updates by reading the live env first.
    from sg_compute_specs.vault_publish.lambdas.admin.Admin__Auth import (
        DEFAULT_NAME as ADMIN_KEY_DEFAULT_NAME, generate_key_value)
    existing_env = {}
    try:
        from sgraph_ai_service_playwright__cli.aws.lambda_.service.Lambda__AWS__Client import Lambda__AWS__Client
        lc = Lambda__AWS__Client()
        if lc.exists(ADMIN_LAMBDA_NAME):
            details = lc.get_function_details(ADMIN_LAMBDA_NAME)
            existing_env = getattr(details, 'environment', {}) or {}
    except Exception:
        pass
    env['SG_VAULT_PUBLISH__ADMIN__API_KEY_NAME'] = (
        existing_env.get('SG_VAULT_PUBLISH__ADMIN__API_KEY_NAME') or
        os.environ.get('SG_VAULT_PUBLISH__ADMIN__API_KEY_NAME', ADMIN_KEY_DEFAULT_NAME))
    env['SG_VAULT_PUBLISH__ADMIN__API_KEY_VALUE'] = (
        existing_env.get('SG_VAULT_PUBLISH__ADMIN__API_KEY_VALUE') or
        os.environ.get('SG_VAULT_PUBLISH__ADMIN__API_KEY_VALUE') or
        generate_key_value())
    return env


def _require_mutations():
    if not os.environ.get('SG_AWS__VAULT_PUBLISH__SETUP__ALLOW_MUTATIONS'):
        raise RuntimeError('Set SG_AWS__VAULT_PUBLISH__SETUP__ALLOW_MUTATIONS=1 to allow Lambda mutations')


def _require_deletes():
    if not os.environ.get('SG_AWS__VAULT_PUBLISH__SETUP__ALLOW_DELETES'):
        raise RuntimeError('Set SG_AWS__VAULT_PUBLISH__SETUP__ALLOW_DELETES=1 to allow Lambda deletes')
