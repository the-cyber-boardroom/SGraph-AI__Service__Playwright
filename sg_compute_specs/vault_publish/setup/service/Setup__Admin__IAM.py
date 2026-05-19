# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — vault-publish setup: Setup__Admin__IAM
# Manages the IAM execution role for the sg-compute-vault-publish-admin Lambda.
#
# Mirrors Setup__IAM's five-verb shape (check/status/create/update/delete) but
# with broader permissions — the admin Lambda runs register / unpublish /
# adopt flows, so it needs EC2 Run/Terminate, Route 53 mutation, IAM PassRole,
# SSM SendCommand on top of the waker's read-only set.
#
# Mutation gate: SG_AWS__VAULT_PUBLISH__SETUP__ALLOW_MUTATIONS=1
# Delete gate:   SG_AWS__VAULT_PUBLISH__SETUP__ALLOW_DELETES=1
# ═══════════════════════════════════════════════════════════════════════════════

import os
from typing import Callable, Optional

from osbot_utils.type_safe.Type_Safe import Type_Safe

from sg_compute_specs.vault_publish.setup.collections.List__Schema__Setup__Issue import List__Schema__Setup__Issue
from sg_compute_specs.vault_publish.setup.schemas.Enum__Setup__State             import Enum__Setup__State
from sg_compute_specs.vault_publish.setup.schemas.Schema__Setup__Issue           import Schema__Setup__Issue
from sg_compute_specs.vault_publish.setup.schemas.Schema__Setup__IAM__Report     import Schema__Setup__IAM__Report
from sg_compute_specs.vault_publish.setup.service.Setup__IAM                     import (
    IAM_ADMIN_ROLE, _detect_iam_role, _stmt_key, _fmt_key, _find_inline_policy,
    _require_mutations, _require_deletes,
)

ADMIN_ROLE_NAME   = 'sg-compute-vault-publish-admin-role'
ADMIN_POLICY_NAME = 'AdminExecutionPolicy'


class Setup__Admin__IAM(Type_Safe):
    _iam_client_factory : Optional[Callable] = None
    _resolved_role      : str                = ''
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
        from sgraph_ai_service_playwright__cli.aws.iam.service.templates.Admin__Policy__Template import Admin__Policy__Template
        return Admin__Policy__Template().build()

    # ── check ─────────────────────────────────────────────────────────────────

    def check(self) -> Schema__Setup__IAM__Report:
        from sgraph_ai_service_playwright__cli.aws.iam.enums.Enum__IAM__Trust__Service import Enum__IAM__Trust__Service
        iam    = self._iam()
        issues = List__Schema__Setup__Issue()

        role = iam.get_role(ADMIN_ROLE_NAME)
        if role is None:
            issues.append(Schema__Setup__Issue(
                severity = 'error', area = 'iam',
                message  = f'role {ADMIN_ROLE_NAME!r} does not exist — run setup admin-iam create',
            ))
            return Schema__Setup__IAM__Report(
                state       = Enum__Setup__State.MISSING,
                role_name   = ADMIN_ROLE_NAME,
                policy_name = ADMIN_POLICY_NAME,
                issues      = issues,
            )

        trust_ok = (role.trust_service == Enum__IAM__Trust__Service.LAMBDA)
        if not trust_ok:
            issues.append(Schema__Setup__Issue(
                severity = 'error', area = 'iam',
                message  = f'trust policy is {role.trust_service!r} — expected LAMBDA',
            ))

        expected_policy = self._template_policy()

        live_policy = _find_inline_policy(role, ADMIN_POLICY_NAME)
        if live_policy is None:
            issues.append(Schema__Setup__Issue(
                severity = 'error', area = 'iam',
                message  = f'inline policy {ADMIN_POLICY_NAME!r} missing from role — run setup admin-iam update',
            ))
            return Schema__Setup__IAM__Report(
                state          = Enum__Setup__State.DRIFT,
                role_name      = ADMIN_ROLE_NAME,
                role_arn       = str(role.role_arn),
                role_exists    = True,
                trust_policy_ok= trust_ok,
                policy_name    = ADMIN_POLICY_NAME,
                issues         = issues,
            )

        expected_keys = {_stmt_key(s) for s in list(expected_policy.statements)}
        live_keys     = {_stmt_key(s) for s in list(live_policy.statements)}
        missing       = expected_keys - live_keys
        extra         = live_keys - expected_keys

        if missing or extra or not trust_ok:
            if missing:
                issues.append(Schema__Setup__Issue(
                    severity='error', area='iam',
                    message=f'policy missing {len(missing)} statement(s)'))
            if extra:
                issues.append(Schema__Setup__Issue(
                    severity='warn', area='iam',
                    message=f'policy has {len(extra)} extra statement(s)'))
            return Schema__Setup__IAM__Report(
                state               = Enum__Setup__State.DRIFT,
                role_name           = ADMIN_ROLE_NAME,
                role_arn            = str(role.role_arn),
                role_exists         = True,
                trust_policy_ok     = trust_ok,
                policy_name         = ADMIN_POLICY_NAME,
                policy_matches      = False,
                missing_statements  = '; '.join(_fmt_key(k) for k in sorted(missing)),
                extra_statements    = '; '.join(_fmt_key(k) for k in sorted(extra)),
                issues              = issues,
            )

        return Schema__Setup__IAM__Report(
            state           = Enum__Setup__State.OK,
            role_name       = ADMIN_ROLE_NAME,
            role_arn        = str(role.role_arn),
            role_exists     = True,
            trust_policy_ok = True,
            policy_name     = ADMIN_POLICY_NAME,
            policy_matches  = True,
            issues          = issues,
        )

    # ── status ────────────────────────────────────────────────────────────────

    def status(self) -> dict:
        iam  = self._iam()
        role = iam.get_role(ADMIN_ROLE_NAME)
        if role is None:
            return {'role': ADMIN_ROLE_NAME, 'exists': False}
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
        role = iam.get_role(ADMIN_ROLE_NAME)
        if role is not None:
            return self.update()                                                   # idempotent

        from sgraph_ai_service_playwright__cli.aws.iam.enums.Enum__IAM__Trust__Service         import Enum__IAM__Trust__Service
        from sgraph_ai_service_playwright__cli.aws.iam.primitives.Safe_Str__IAM__Role_Name      import Safe_Str__IAM__Role_Name
        from sgraph_ai_service_playwright__cli.aws.iam.schemas.Schema__IAM__Role__Create__Request import Schema__IAM__Role__Create__Request
        req = Schema__IAM__Role__Create__Request(
            role_name     = Safe_Str__IAM__Role_Name(ADMIN_ROLE_NAME),
            trust_service = Enum__IAM__Trust__Service.LAMBDA,
            description   = 'Execution role for the vault-publish admin Lambda - broader perms than waker',
        )
        iam.create_role(req)
        iam.put_inline_policy(ADMIN_ROLE_NAME, ADMIN_POLICY_NAME, self._template_policy())
        return self.check()

    # ── update ────────────────────────────────────────────────────────────────

    def update(self) -> Schema__Setup__IAM__Report:
        _require_mutations()
        iam  = self._iam()
        role = iam.get_role(ADMIN_ROLE_NAME)
        if role is not None:
            from sgraph_ai_service_playwright__cli.aws.iam.enums.Enum__IAM__Trust__Service import Enum__IAM__Trust__Service
            if role.trust_service != Enum__IAM__Trust__Service.LAMBDA:
                iam.update_assume_role_policy(ADMIN_ROLE_NAME, Enum__IAM__Trust__Service.LAMBDA)
        iam.put_inline_policy(ADMIN_ROLE_NAME, ADMIN_POLICY_NAME, self._template_policy())
        return self.check()

    # ── delete ────────────────────────────────────────────────────────────────

    def delete(self) -> Schema__Setup__IAM__Report:
        _require_deletes()
        iam  = self._iam()
        role = iam.get_role(ADMIN_ROLE_NAME)
        if role is None:
            issues = List__Schema__Setup__Issue()
            issues.append(Schema__Setup__Issue(
                severity='info', area='iam',
                message=f'role {ADMIN_ROLE_NAME!r} already absent'))
            return Schema__Setup__IAM__Report(
                state       = Enum__Setup__State.MISSING,
                role_name   = ADMIN_ROLE_NAME,
                policy_name = ADMIN_POLICY_NAME,
                issues      = issues,
            )
        for mp in list(role.managed_policy_arns):
            iam.detach_managed_policy(ADMIN_ROLE_NAME, str(mp))
        iam.delete_role(ADMIN_ROLE_NAME)
        return Schema__Setup__IAM__Report(
            state       = Enum__Setup__State.MISSING,
            role_name   = ADMIN_ROLE_NAME,
            policy_name = ADMIN_POLICY_NAME,
        )
