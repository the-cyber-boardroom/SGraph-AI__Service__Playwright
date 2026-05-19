# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — vault-publish setup: Setup__Lambda
# Drift-check + deploy for the sg-compute-vault-publish-waker Lambda function.
#
# Mutation gate: SG_AWS__VAULT_PUBLISH__SETUP__ALLOW_MUTATIONS=1
# Delete gate:   SG_AWS__VAULT_PUBLISH__SETUP__ALLOW_DELETES=1
#
# EXPECTED_* constants mirror the values set in Vault_Publish__Service.bootstrap.
#
# ── WAKER_VERSION policy (agent-managed) ──────────────────────────────────────
# sg_compute_specs/vault_publish/version (currently v0.1.6) is the canonical
# version of the vault-publish Lambda runtime — NOT auto-bumped by CI.
#
#   Rule: every commit that changes the LAMBDA RUNTIME CODE must bump the
#   rightmost component (.z) of that file in the same commit. "Lambda runtime
#   code" = anything in sg_compute_specs/vault_publish/waker/** plus any
#   schema referenced by Fast_API__Waker / Waker__Handler.
#
#   Out of scope (no bump needed):
#     - CLI changes in sg_compute_specs/vault_publish/{cli,setup/cli}/**
#     - Tests, docs, CI
#     - CloudFront Function code (it has its own FUNCTION_VERSION in
#       Setup__CF__Function.py, bumped under its own rule there)
#     - The deployer / setup services (this file) when the change doesn't
#       alter what gets baked into the Lambda
#
#   The .y bumps once the existing v0.1 series stabilises and we ship a
#   first-cut "vault-publish v0.2" with a documented breaking change to the
#   waker contract (renamed env var, dropped endpoint, changed X-Waker-*
#   header semantics, etc.).
#
# /version (repo root, currently v0.2.29) is the CANONICAL SERVICE version —
# bumped automatically by CI on merges to dev. Surfaced as WAKER_SERVICE_VERSION.
#
# Both values are baked into the Lambda env at deploy time and visible via
# `sg vp setup lambda status`, the diagnostic 200 status page, and
# `sg vp setup lambda invoke` (which hits /__waker__/deploy).
#
# Deployment metadata env vars set on every create/update:
#   WAKER_SERVICE_VERSION — repo-root `version` (canonical service version)
#   WAKER_VERSION         — `sg_compute_specs/vault_publish/version` (sub-package)
#   WAKER_DEPLOYED_AT     — ISO-8601 UTC timestamp of this deploy
#   WAKER_DEPLOY_ID       — unique per-deploy ID (uuid4 hex)
#   WAKER_DEPLOY_REGION   — region the deployer targeted
#   WAKER_DEPLOYED_BY     — STS GetCallerIdentity ARN at deploy time
#   WAKER_GIT_COMMIT      — git rev-parse HEAD (best-effort; empty when absent)
# Plus any env vars the runtime needs (e.g. SG_AWS__DNS__DEFAULT_ZONE).
# ═══════════════════════════════════════════════════════════════════════════════

import os
import subprocess
import uuid
from datetime import datetime, timezone
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
        from sgraph_ai_service_playwright__cli.aws._shared.Aws__Region__Resolver   import Aws__Region__Resolver
        from sgraph_ai_service_playwright__cli.aws.lambda_.service.Lambda__Deployer import Lambda__Deployer
        return Lambda__Deployer(region=str(Aws__Region__Resolver().resolve()))      # must match Lambda__AWS__Client region

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

        env_live = getattr(details, 'environment', {}) or {}
        deploy_env_lines = '\n'.join(
            f'{k}: {env_live.get(k, "(unset)")}'
            for k in ('WAKER_SERVICE_VERSION', 'WAKER_VERSION', 'WAKER_DEPLOYED_AT',
                       'WAKER_DEPLOY_ID', 'WAKER_DEPLOY_REGION', 'WAKER_DEPLOYED_BY',
                       'WAKER_GIT_COMMIT')
        )

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
        if not lc.exists(WAKER_LAMBDA_NAME):
            return {'function_name': WAKER_LAMBDA_NAME, 'exists': 'no'}
        details  = lc.get_function_details(WAKER_LAMBDA_NAME)
        url_info = lc.get_function_url(WAKER_LAMBDA_NAME)
        env      = getattr(details, 'environment', {}) or {}
        out = {
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
        # Surface deploy-metadata env vars (set by Setup__Lambda at deploy time)
        for k in ('WAKER_SERVICE_VERSION', 'WAKER_VERSION', 'WAKER_DEPLOYED_AT',
                   'WAKER_DEPLOY_ID', 'WAKER_DEPLOY_REGION', 'WAKER_DEPLOYED_BY',
                   'WAKER_GIT_COMMIT'):
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
        env = _build_deploy_env(vault_publish_dir)
        if progress: progress('build-env', 'done')

        deploy_req = Schema__Lambda__Deploy__Request(
            name        = Safe_Str__Lambda__Name(WAKER_LAMBDA_NAME),
            folder_path = vault_publish_dir,
            handler     = WAKER_HANDLER,
            role_arn    = role_arn,
            runtime     = Enum__Lambda__Runtime.PYTHON_3_12,
            memory_size = EXPECTED_MEMORY,
            timeout     = EXPECTED_TIMEOUT,
            description = f'Vault Publish Waker — {env.get("WAKER_VERSION", "?")} '
                          f'deployed {env.get("WAKER_DEPLOYED_AT", "?")}',
        )
        deploy_resp = self._deployer().deploy_from_folder(
            deploy_req,
            package_root  = package_root,
            extra_modules = ['osbot_utils', 'osbot_aws'],
            environment   = env,
            progress      = progress,
        )
        if not deploy_resp.success:
            issues = List__Schema__Setup__Issue()
            issues.append(Schema__Setup__Issue(
                severity='error', area='lambda',
                message=f'deploy failed: {deploy_resp.message}'))
            return Schema__Setup__Lambda__Report(
                state=Enum__Setup__State.ERROR, function_name=WAKER_LAMBDA_NAME, issues=issues)

        lc = self._lambda_client()
        if progress: progress('ensure-url', 'start')
        lc.ensure_function_url(WAKER_LAMBDA_NAME)
        if progress: progress('ensure-url', 'done')

        if progress: progress('check', 'start')
        report = self.check()
        if progress: progress('check', 'done')
        # Stamp deploy-only details that check() can't know about
        report.zip_size = int(getattr(deploy_resp, 'zip_size', 0) or 0)
        return report

    def update(self, progress: Optional[Callable] = None) -> Schema__Setup__Lambda__Report:
        _require_mutations()
        lc      = self._lambda_client()
        details = lc.get_function_details(WAKER_LAMBDA_NAME)
        return self.create(role_arn=details.role_arn, progress=progress)               # carry live role so deployer can fall back to create if needed

    def delete(self) -> bool:
        _require_deletes()
        lc = self._lambda_client()
        try:
            lc.delete_function_url(WAKER_LAMBDA_NAME)
        except Exception:
            pass
        resp = lc.delete_function(WAKER_LAMBDA_NAME)
        return resp.success


# ── deployment metadata ──────────────────────────────────────────────────────

def _build_deploy_env(vault_publish_dir: str) -> dict:
    """Compose the env-var dict baked into the Lambda config at deploy time."""
    from sgraph_ai_service_playwright__cli.aws._shared.Aws__Region__Resolver import Aws__Region__Resolver
    now      = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    repo_root = os.path.abspath(os.path.join(vault_publish_dir, '..', '..'))
    env = {
        'WAKER_SERVICE_VERSION': _read_version(repo_root),                            # repo-root canonical version
        'WAKER_VERSION'        : _read_version(vault_publish_dir),                    # sub-package version
        'WAKER_DEPLOYED_AT'    : now,
        'WAKER_DEPLOY_ID'      : uuid.uuid4().hex[:16],
        'WAKER_DEPLOY_REGION'  : str(Aws__Region__Resolver().resolve()),
        'WAKER_DEPLOYED_BY'    : _caller_identity(),
        'WAKER_GIT_COMMIT'     : _git_commit(),
    }
    # Pass through the DNS zone the slug parser needs.
    zone = os.environ.get('SG_AWS__DNS__DEFAULT_ZONE', '')
    if zone:
        env['SG_AWS__DNS__DEFAULT_ZONE'] = zone
    # Dev RPC channel (/__waker__/cmd) — defaults to ON for dev. Set to '0'
    # on the function config manually to disable in production.
    env['WAKER_CMD_ENABLED']           = os.environ.get('WAKER_CMD_ENABLED',           '1')
    env['WAKER_CMD_MUTATIONS_ENABLED'] = os.environ.get('WAKER_CMD_MUTATIONS_ENABLED', '1')
    # Lambda's own Function URL. Used by Warming__Page to poll cross-origin
    # from the slug FQDN (different origin → different socket pool slot in
    # the browser → no DNS pinning on the slug FQDN socket). Discovered
    # best-effort here; on first create the URL doesn't exist yet so this
    # is empty — `sg vp setup lambda update` after the URL is provisioned
    # will pick it up and bake it in.
    try:
        from sgraph_ai_service_playwright__cli.aws.lambda_.service.Lambda__AWS__Client import Lambda__AWS__Client
        url_info = Lambda__AWS__Client().get_function_url(WAKER_LAMBDA_NAME)
        if getattr(url_info, 'exists', False) and getattr(url_info, 'function_url', ''):
            env['WAKER_LAMBDA_FUNCTION_URL'] = str(url_info.function_url).rstrip('/')
    except Exception:
        pass                                                                            # silent — handled by the warming page falling back to slug polling
    return env


def _read_version(dir_path: str) -> str:
    path = os.path.join(dir_path, 'version')
    try:
        return open(path).read().strip() or 'unknown'
    except OSError:
        return 'unknown'


def _git_commit() -> str:
    try:
        out = subprocess.check_output(['git', 'rev-parse', '--short', 'HEAD'],
                                      stderr=subprocess.DEVNULL, timeout=2)
        return out.decode('ascii', errors='ignore').strip()
    except Exception:
        return ''


def _caller_identity() -> str:
    try:
        import boto3
        return boto3.client('sts').get_caller_identity().get('Arn', '')[:128]
    except Exception:
        return ''


# ── gates ─────────────────────────────────────────────────────────────────────

def _require_mutations():
    if not os.environ.get('SG_AWS__VAULT_PUBLISH__SETUP__ALLOW_MUTATIONS'):
        raise RuntimeError(
            'Set SG_AWS__VAULT_PUBLISH__SETUP__ALLOW_MUTATIONS=1 to allow Lambda mutations')


def _require_deletes():
    if not os.environ.get('SG_AWS__VAULT_PUBLISH__SETUP__ALLOW_DELETES'):
        raise RuntimeError(
            'Set SG_AWS__VAULT_PUBLISH__SETUP__ALLOW_DELETES=1 to allow Lambda deletes')
