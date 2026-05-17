# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Vault_App__Stop__Policy__Template
# ═══════════════════════════════════════════════════════════════════════════════

from sgraph_ai_service_playwright__cli.aws.iam.collections.List__Schema__IAM__Policy          import List__Schema__IAM__Policy
from sgraph_ai_service_playwright__cli.aws.iam.enums.Enum__IAM__Audit__Severity               import Enum__IAM__Audit__Severity
from sgraph_ai_service_playwright__cli.aws.iam.primitives.Safe_Str__IAM__Role_Arn             import Safe_Str__IAM__Role_Arn
from sgraph_ai_service_playwright__cli.aws.iam.primitives.Safe_Str__IAM__Role_Name            import Safe_Str__IAM__Role_Name
from sgraph_ai_service_playwright__cli.aws.iam.schemas.Schema__IAM__Role                      import Schema__IAM__Role
from sgraph_ai_service_playwright__cli.aws.iam.service.IAM__Policy__Auditor                   import IAM__Policy__Auditor
from sgraph_ai_service_playwright__cli.aws.iam.service.templates.Vault_App__Stop__Policy__Template import Vault_App__Stop__Policy__Template


class Test__Vault_App__Stop__Policy__Template:

    def test_1__builds_policy_with_two_statements(self):
        policy = Vault_App__Stop__Policy__Template().build()
        assert len(policy.statements) == 2

    def test_2__stop_and_start_actions_present(self):
        policy  = Vault_App__Stop__Policy__Template().build()
        actions = []
        for stmt in policy.statements:
            actions.extend([str(a) for a in stmt.actions])
        assert 'ec2:StopInstances'  in actions
        assert 'ec2:StartInstances' in actions

    def test_3__audit_no_critical_no_warn(self):
        policy   = Vault_App__Stop__Policy__Template().build()
        pol_list = List__Schema__IAM__Policy()
        pol_list.append(policy)
        role = Schema__IAM__Role(
            role_name = Safe_Str__IAM__Role_Name('vault-app-operator-role'),
            role_arn  = Safe_Str__IAM__Role_Arn('arn:aws:iam::123456789012:role/vault-app-operator-role'),
            last_used = '2026-05-17T00:00:00+00:00',
        )
        role.inline_policies = pol_list
        report = IAM__Policy__Auditor().audit(role)
        critical = [f for f in report.findings if str(f.severity) == 'CRITICAL']
        warn     = [f for f in report.findings if str(f.severity) == 'WARN']
        assert len(critical) == 0, f'Unexpected CRITICAL: {[f.message for f in critical]}'
        assert len(warn)     == 0, f'Unexpected WARN: {[f.message for f in warn]}'
