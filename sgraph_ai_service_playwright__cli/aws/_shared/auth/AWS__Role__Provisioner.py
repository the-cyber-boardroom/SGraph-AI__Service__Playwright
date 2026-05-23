# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — aws shared auth: AWS__Role__Provisioner
# The generic create/diff/delete engine behind `… iam` for every command family. Given
# a family profile (from AWS__Role__Profiles) it renders the desired inline policy +
# account-root trust, diffs them against the live IAM role, and applies changes through
# the existing IAM__AWS__Client (the one IAM boto3 boundary — injectable, so tests run
# against an in-memory fake with no AWS). Knows nothing family-specific; the profile
# carries all the intent. Mutations are gated at the CLI layer, not here.
# ═══════════════════════════════════════════════════════════════════════════════

import json

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe

from sgraph_ai_service_playwright__cli.aws._shared.auth                            import AWS__Role__Profiles as profiles
from sgraph_ai_service_playwright__cli.aws._shared.auth.schemas.Schema__AWS__Role__Plan import Schema__AWS__Role__Plan
from sgraph_ai_service_playwright__cli.aws.iam.service.IAM__AWS__Client            import IAM__AWS__Client


class AWS__Role__Provisioner(Type_Safe):
    iam        : IAM__AWS__Client = None                                             # injected or lazy via setup()
    account_id : str              = ''                                               # injected in tests; resolved via STS otherwise

    def setup(self):
        if self.iam is None:
            self.iam = IAM__AWS__Client()
        return self

    def policy_name_for(self, profile) -> str:
        return f'{profile.family}-policy'

    def resolve_account_id(self) -> str:
        if self.account_id:
            return self.account_id
        from sgraph_ai_service_playwright__cli.aws._shared.auth.Aws__Session__Factory import boto3_client_via_context
        try:
            self.account_id = str(boto3_client_via_context('sts').get_caller_identity().get('Account', ''))
        except Exception:
            self.account_id = ''
        return self.account_id

    def desired_policy_json(self, profile) -> str:
        return json.dumps(profiles.policy_document(profile), indent=2)

    def desired_trust_json(self, account_id : str, profile=None) -> str:
        if profile is not None:                                                       # honour an execution-role (service-principal) trust when declared
            return json.dumps(profiles.trust_policy_for(profile, account_id), indent=2)
        return json.dumps(profiles.trust_policy_document(account_id), indent=2)

    def current_actions(self, profile) -> list:                                      # actions on the live inline policy ([] if role/policy absent)
        self.setup()
        role = self.iam.get_role(profile.role_name)
        if role is None:
            return []
        actions = []
        for policy in role.inline_policies:
            for stmt in policy.statements:
                actions.extend(str(a) for a in stmt.actions)
        return sorted(set(actions))

    def desired_actions(self, profile) -> list:
        actions = []
        for s in profile.statements:
            actions.extend(str(a) for a in s.actions)
        return sorted(set(actions))

    def plan(self, profile) -> Schema__AWS__Role__Plan:
        self.setup()
        account_id = self.resolve_account_id()
        role       = self.iam.get_role(profile.role_name)
        exists     = role is not None
        current    = self.current_actions(profile)
        desired    = self.desired_actions(profile)
        to_add     = sorted(set(desired) - set(current))
        to_remove  = sorted(set(current) - set(desired))
        return Schema__AWS__Role__Plan(
            family            = profile.family,
            role_name         = profile.role_name,
            role_arn          = profiles.role_arn(profile, account_id) if account_id else '',
            exists            = exists,
            actions_desired   = desired,
            actions_current   = current,
            actions_to_add    = to_add,
            actions_to_remove = to_remove,
            in_sync           = exists and not to_add and not to_remove,
            policy_json       = self.desired_policy_json(profile),
            trust_json        = self.desired_trust_json(account_id, profile) if account_id else '')

    def apply(self, profile):                                                        # create-or-update: idempotent, overwrites the inline policy to match the profile
        self.setup()
        account_id = self.resolve_account_id()
        trust_json = self.desired_trust_json(account_id, profile)
        resp       = self.iam.create_role_with_trust(profile.role_name, trust_json,
                                                      str(profile.description))
        if not resp.created:                                                         # role already there — keep its trust current too
            self.iam.update_assume_role_policy_raw(profile.role_name, trust_json)
        self.iam.put_raw_inline_policy(profile.role_name, self.policy_name_for(profile),
                                       self.desired_policy_json(profile))
        return resp

    def delete(self, profile) -> bool:
        self.setup()
        return self.iam.delete_role(profile.role_name)
