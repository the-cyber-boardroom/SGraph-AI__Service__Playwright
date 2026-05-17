# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Waker__Policy__Template
# Verifies the built policy satisfies the audit target state: max INFO severity.
# ═══════════════════════════════════════════════════════════════════════════════

from sgraph_ai_service_playwright__cli.aws.iam.collections.List__Schema__IAM__Policy     import List__Schema__IAM__Policy
from sgraph_ai_service_playwright__cli.aws.iam.enums.Enum__IAM__Audit__Severity          import Enum__IAM__Audit__Severity
from sgraph_ai_service_playwright__cli.aws.iam.primitives.Safe_Str__IAM__Role_Arn        import Safe_Str__IAM__Role_Arn
from sgraph_ai_service_playwright__cli.aws.iam.primitives.Safe_Str__IAM__Role_Name       import Safe_Str__IAM__Role_Name
from sgraph_ai_service_playwright__cli.aws.iam.schemas.Schema__IAM__Role                 import Schema__IAM__Role
from sgraph_ai_service_playwright__cli.aws.iam.service.IAM__Policy__Auditor              import IAM__Policy__Auditor
from sgraph_ai_service_playwright__cli.aws.iam.service.templates.Waker__Policy__Template import Waker__Policy__Template


class Test__Waker__Policy__Template:

    def test_1__builds_policy_with_three_statements(self):
        policy = Waker__Policy__Template().build()
        assert len(policy.statements) == 3

    def test_2__all_statements_have_allow_effect(self):
        policy = Waker__Policy__Template().build()
        for stmt in policy.statements:
            assert stmt.effect == 'Allow'

    def test_3__audit_max_severity_is_info(self):
        policy   = Waker__Policy__Template().build()
        pol_list = List__Schema__IAM__Policy()
        pol_list.append(policy)
        role = Schema__IAM__Role(
            role_name = Safe_Str__IAM__Role_Name('sg-compute-vault-publish-waker-role'),
            role_arn  = Safe_Str__IAM__Role_Arn('arn:aws:iam::745506449035:role/sg-compute-vault-publish-waker-role'),
            last_used = '2026-05-17T00:00:00+00:00',
        )
        role.inline_policies = pol_list
        report = IAM__Policy__Auditor().audit(role)
        assert report.overall_severity == Enum__IAM__Audit__Severity.INFO, \
               f'Expected INFO, got {report.overall_severity}. Findings: {[str(f.code) for f in report.findings]}'
        critical = [f for f in report.findings if str(f.severity) == 'CRITICAL']
        warn     = [f for f in report.findings if str(f.severity) == 'WARN']
        assert len(critical) == 0, f'Unexpected CRITICAL findings: {critical}'
        assert len(warn)     == 0, f'Unexpected WARN findings: {warn}'
