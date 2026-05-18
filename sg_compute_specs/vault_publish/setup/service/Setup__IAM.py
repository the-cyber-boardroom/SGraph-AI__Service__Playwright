# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — vault-publish setup: Setup__IAM
# Manages the IAM execution role for the vault-publish waker Lambda.
#
# Five verbs: check / status / create / update / delete
#   check  — read-only; compares live role to Waker__Policy__Template
#   status — pretty-prints live role config (read-only)
#   create — creates role + attaches policy from template (mutation-gated)
#   update — replaces inline policy with current template (mutation-gated)
#   delete — detaches + deletes role (delete-gated)
#
# Mutation gate: SG_AWS__VAULT_PUBLISH__SETUP__ALLOW_MUTATIONS=1
# Delete gate:   SG_AWS__VAULT_PUBLISH__SETUP__ALLOW_DELETES=1
#
# Role auto-detection:
#   IAM mutations require elevated privileges.  If the 'iam-admin' role is
#   registered in the credentials store and the caller is not already using it,
#   Setup__IAM automatically uses it and prints a notice to the operator.
#   Pass _iam_client_factory to bypass this logic in tests.
# ═══════════════════════════════════════════════════════════════════════════════

import json
import os
from typing import Callable, Optional

from osbot_utils.type_safe.Type_Safe import Type_Safe

from sg_compute_specs.vault_publish.setup.collections.List__Schema__Setup__Issue import List__Schema__Setup__Issue
from sg_compute_specs.vault_publish.setup.schemas.Enum__Setup__State             import Enum__Setup__State
from sg_compute_specs.vault_publish.setup.schemas.Schema__Setup__Issue           import Schema__Setup__Issue
from sg_compute_specs.vault_publish.setup.schemas.Schema__Setup__IAM__Report     import Schema__Setup__IAM__Report

WAKER_ROLE_NAME   = 'sg-compute-vault-publish-waker-role'
WAKER_POLICY_NAME = 'WakerExecutionPolicy'
IAM_ADMIN_ROLE    = 'iam-admin'
_CURRENT_ROLE_ENV = 'SG_CREDENTIALS__CURRENT_ROLE'


class Setup__IAM(Type_Safe):
    _iam_client_factory : Optional[Callable] = None  # seam: () -> IAM__AWS__Client
    _resolved_role      : str                = ''    # set once by _resolve()
    _role_auto_assumed  : bool               = False
    _resolved           : bool               = False

    def _resolve(self) -> None:
        if self._resolved:
            return
        role, auto = _detect_iam_role()
        self._resolved_role     = role
        self._role_auto_assumed = auto
        self._resolved          = True

    def assumed_role_notice(self) -> str:
        """Returns a human-readable notice when we auto-assumed a role; empty otherwise."""
        self._resolve()
        if self._role_auto_assumed:
            return f"for this action, assuming role '{self._resolved_role}'"
        return ''

    def _iam(self):
        if self._iam_client_factory is not None:
            return self._iam_client_factory()
        self._resolve()
        from sgraph_ai_service_playwright__cli.aws.iam.service.IAM__AWS__Client import IAM__AWS__Client
        if self._resolved_role:
            return IAM__AWS__Client(role_name=self._resolved_role)
        return IAM__AWS__Client()

    def _template_policy(self):
        from sgraph_ai_service_playwright__cli.aws.iam.service.templates.Waker__Policy__Template import Waker__Policy__Template
        return Waker__Policy__Template().build()

    # ── check ─────────────────────────────────────────────────────────────────

    def check(self) -> Schema__Setup__IAM__Report:
        iam    = self._iam()
        issues = List__Schema__Setup__Issue()

        role = iam.get_role(WAKER_ROLE_NAME)
        if role is None:
            issues.append(Schema__Setup__Issue(
                severity = 'error',
                area     = 'iam',
                message  = f'role {WAKER_ROLE_NAME!r} does not exist — run setup iam create',
            ))
            return Schema__Setup__IAM__Report(
                state       = Enum__Setup__State.MISSING,
                role_name   = WAKER_ROLE_NAME,
                policy_name = WAKER_POLICY_NAME,
                issues      = issues,
            )

        expected_policy = self._template_policy()
        expected_actions = _collect_actions(expected_policy)

        live_policy = _find_inline_policy(role, WAKER_POLICY_NAME)
        if live_policy is None:
            issues.append(Schema__Setup__Issue(
                severity = 'error',
                area     = 'iam',
                message  = f'inline policy {WAKER_POLICY_NAME!r} missing from role — run setup iam update',
            ))
            return Schema__Setup__IAM__Report(
                state       = Enum__Setup__State.DRIFT,
                role_name   = WAKER_ROLE_NAME,
                role_arn    = str(role.role_arn),
                role_exists = True,
                policy_name = WAKER_POLICY_NAME,
                issues      = issues,
            )

        live_actions    = _collect_actions(live_policy)
        missing_actions = expected_actions - live_actions
        extra_actions   = live_actions - expected_actions

        if missing_actions or extra_actions:
            if missing_actions:
                issues.append(Schema__Setup__Issue(
                    severity = 'error',
                    area     = 'iam',
                    message  = f'policy missing actions: {", ".join(sorted(missing_actions))}',
                ))
            if extra_actions:
                issues.append(Schema__Setup__Issue(
                    severity = 'warn',
                    area     = 'iam',
                    message  = f'policy has extra actions: {", ".join(sorted(extra_actions))}',
                ))
            return Schema__Setup__IAM__Report(
                state           = Enum__Setup__State.DRIFT,
                role_name       = WAKER_ROLE_NAME,
                role_arn        = str(role.role_arn),
                role_exists     = True,
                policy_name     = WAKER_POLICY_NAME,
                policy_matches  = False,
                missing_actions = ', '.join(sorted(missing_actions)),
                extra_actions   = ', '.join(sorted(extra_actions)),
                issues          = issues,
            )

        return Schema__Setup__IAM__Report(
            state          = Enum__Setup__State.OK,
            role_name      = WAKER_ROLE_NAME,
            role_arn       = str(role.role_arn),
            role_exists    = True,
            policy_name    = WAKER_POLICY_NAME,
            policy_matches = True,
            issues         = issues,
        )

    # ── status ────────────────────────────────────────────────────────────────

    def status(self) -> dict:
        iam  = self._iam()
        role = iam.get_role(WAKER_ROLE_NAME)
        if role is None:
            return {'role': WAKER_ROLE_NAME, 'exists': False}
        return {
            'role'             : str(role.role_name),
            'arn'              : str(role.role_arn),
            'exists'           : True,
            'inline_policies'  : len(list(role.inline_policies)),
            'managed_policies' : len(list(role.managed_policy_arns)),
        }

    # ── create ────────────────────────────────────────────────────────────────

    def create(self) -> Schema__Setup__IAM__Report:
        _require_mutations()
        iam  = self._iam()
        role = iam.get_role(WAKER_ROLE_NAME)
        if role is not None:
            return self.update()                                     # idempotent: role exists → update policy

        from sgraph_ai_service_playwright__cli.aws.iam.enums.Enum__IAM__Trust__Service         import Enum__IAM__Trust__Service
        from sgraph_ai_service_playwright__cli.aws.iam.primitives.Safe_Str__IAM__Role_Name      import Safe_Str__IAM__Role_Name
        from sgraph_ai_service_playwright__cli.aws.iam.schemas.Schema__IAM__Role__Create__Request import Schema__IAM__Role__Create__Request
        req = Schema__IAM__Role__Create__Request(
            role_name     = Safe_Str__IAM__Role_Name(WAKER_ROLE_NAME),
            trust_service = Enum__IAM__Trust__Service.LAMBDA,
            description   = 'Execution role for the vault-publish waker Lambda',
        )
        iam.create_role(req)
        iam.put_inline_policy(WAKER_ROLE_NAME, WAKER_POLICY_NAME, self._template_policy())
        return self.check()

    # ── update ────────────────────────────────────────────────────────────────

    def update(self) -> Schema__Setup__IAM__Report:
        _require_mutations()
        iam = self._iam()
        iam.put_inline_policy(WAKER_ROLE_NAME, WAKER_POLICY_NAME, self._template_policy())
        return self.check()

    # ── delete ────────────────────────────────────────────────────────────────

    def delete(self) -> Schema__Setup__IAM__Report:
        _require_deletes()
        iam  = self._iam()
        role = iam.get_role(WAKER_ROLE_NAME)
        if role is None:
            issues = List__Schema__Setup__Issue()
            issues.append(Schema__Setup__Issue(
                severity = 'info',
                area     = 'iam',
                message  = f'role {WAKER_ROLE_NAME!r} already absent',
            ))
            return Schema__Setup__IAM__Report(
                state       = Enum__Setup__State.MISSING,
                role_name   = WAKER_ROLE_NAME,
                policy_name = WAKER_POLICY_NAME,
                issues      = issues,
            )
        for mp in list(role.managed_policy_arns):
            iam.detach_managed_policy(WAKER_ROLE_NAME, str(mp))
        iam.delete_role(WAKER_ROLE_NAME)
        return Schema__Setup__IAM__Report(
            state       = Enum__Setup__State.MISSING,
            role_name   = WAKER_ROLE_NAME,
            policy_name = WAKER_POLICY_NAME,
        )


# ── helpers ───────────────────────────────────────────────────────────────────

def _detect_iam_role() -> tuple:
    """Returns (role_name, auto_assumed).

    Checks whether we should auto-assume the 'iam-admin' role:
    - If already in iam-admin (env var or context) → use it, no notice
    - If iam-admin is in the credentials store → use it, print notice
    - Otherwise → empty string, use whatever context is active
    """
    current = os.environ.get(_CURRENT_ROLE_ENV, '')
    if not current:
        try:
            from sgraph_ai_service_playwright__cli.credentials.service.Sg__Aws__Context import Sg__Aws__Context
            current = Sg__Aws__Context.get_current_role()
        except Exception:
            pass

    if current == IAM_ADMIN_ROLE:
        return (IAM_ADMIN_ROLE, False)   # already in iam-admin — use it silently

    # Check if iam-admin is registered in the local credentials store
    try:
        from sgraph_ai_service_playwright__cli.credentials.service.Credentials__Store import Credentials__Store
        from sgraph_ai_service_playwright__cli.osx.keyring.service.Keyring__Mac__OS   import Keyring__Mac__OS
        store = Credentials__Store(keyring=Keyring__Mac__OS())
        if store.aws_credentials_get(IAM_ADMIN_ROLE) is not None:
            return (IAM_ADMIN_ROLE, True)  # auto-switch with notice
    except Exception:
        pass

    return (current, False)              # use active role (may be '' → bare boto3)


def _collect_actions(policy) -> set:
    actions = set()
    for stmt in list(policy.statements):
        for action in list(stmt.actions):
            actions.add(str(action))
    return actions


def _find_inline_policy(role, policy_name: str):
    for p in list(role.inline_policies):
        return p                                                      # we own exactly one inline policy
    return None


def _require_mutations():
    if not os.environ.get('SG_AWS__VAULT_PUBLISH__SETUP__ALLOW_MUTATIONS'):
        raise RuntimeError(
            'Set SG_AWS__VAULT_PUBLISH__SETUP__ALLOW_MUTATIONS=1 to allow IAM mutations'
        )


def _require_deletes():
    if not os.environ.get('SG_AWS__VAULT_PUBLISH__SETUP__ALLOW_DELETES'):
        raise RuntimeError(
            'Set SG_AWS__VAULT_PUBLISH__SETUP__ALLOW_DELETES=1 to allow IAM deletes'
        )
