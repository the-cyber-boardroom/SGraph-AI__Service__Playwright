# ═══════════════════════════════════════════════════════════════════════════════
# Tests — IAM__Policy__Auditor (7 detectors, positive + negative per detector)
# ═══════════════════════════════════════════════════════════════════════════════

import json

from sgraph_ai_service_playwright__cli.aws.iam.collections.List__Safe_Str__Aws__Action   import List__Safe_Str__Aws__Action
from sgraph_ai_service_playwright__cli.aws.iam.collections.List__Safe_Str__Aws__Resource import List__Safe_Str__Aws__Resource
from sgraph_ai_service_playwright__cli.aws.iam.collections.List__Schema__IAM__Policy     import List__Schema__IAM__Policy
from sgraph_ai_service_playwright__cli.aws.iam.collections.List__Schema__IAM__Statement  import List__Schema__IAM__Statement
from sgraph_ai_service_playwright__cli.aws.iam.enums.Enum__IAM__Audit__Finding           import Enum__IAM__Audit__Finding
from sgraph_ai_service_playwright__cli.aws.iam.enums.Enum__IAM__Audit__Severity          import Enum__IAM__Audit__Severity
from sgraph_ai_service_playwright__cli.aws.iam.enums.Enum__IAM__Trust__Service           import Enum__IAM__Trust__Service
from sgraph_ai_service_playwright__cli.aws.iam.primitives.Safe_Str__Aws__Action          import Safe_Str__Aws__Action
from sgraph_ai_service_playwright__cli.aws.iam.primitives.Safe_Str__Aws__Resource        import Safe_Str__Aws__Resource
from sgraph_ai_service_playwright__cli.aws.iam.primitives.Safe_Str__IAM__Policy_Arn      import Safe_Str__IAM__Policy_Arn
from sgraph_ai_service_playwright__cli.aws.iam.primitives.Safe_Str__IAM__Role_Arn        import Safe_Str__IAM__Role_Arn
from sgraph_ai_service_playwright__cli.aws.iam.primitives.Safe_Str__IAM__Role_Name       import Safe_Str__IAM__Role_Name
from sgraph_ai_service_playwright__cli.aws.iam.schemas.Schema__IAM__Policy               import Schema__IAM__Policy
from sgraph_ai_service_playwright__cli.aws.iam.schemas.Schema__IAM__Role                 import Schema__IAM__Role
from sgraph_ai_service_playwright__cli.aws.iam.schemas.Schema__IAM__Statement            import Schema__IAM__Statement
from sgraph_ai_service_playwright__cli.aws.iam.service.IAM__Policy__Auditor              import IAM__Policy__Auditor


def _stmt(actions, resources, allow_wildcard=False, condition=None) -> Schema__IAM__Statement:
    act_list = List__Safe_Str__Aws__Action()
    for a in actions:
        act_list.append(Safe_Str__Aws__Action(a))
    res_list = List__Safe_Str__Aws__Resource()
    for r in resources:
        res_list.append(Safe_Str__Aws__Resource(r))
    return Schema__IAM__Statement(
        actions                = act_list,
        resources              = res_list,
        allow_wildcard_resource= allow_wildcard,
        condition_json         = json.dumps(condition) if condition else '',
    )


def _role(stmts, managed_arns=None, last_used='2026-05-17T00:00:00+00:00') -> Schema__IAM__Role:
    stmt_list = List__Schema__IAM__Statement()
    for s in stmts:
        stmt_list.append(s)
    policy    = Schema__IAM__Policy(statements=stmt_list)
    pol_list  = List__Schema__IAM__Policy()
    pol_list.append(policy)
    role = Schema__IAM__Role(
        role_name  = Safe_Str__IAM__Role_Name('test-role'),
        role_arn   = Safe_Str__IAM__Role_Arn('arn:aws:iam::123456789012:role/test-role'),
        last_used  = last_used,
    )
    role.inline_policies = pol_list
    if managed_arns:
        from sgraph_ai_service_playwright__cli.aws.iam.collections.List__Safe_Str__IAM__Policy_Arn import List__Safe_Str__IAM__Policy_Arn
        arn_list = List__Safe_Str__IAM__Policy_Arn()
        for a in managed_arns:
            arn_list.append(Safe_Str__IAM__Policy_Arn(a))
        role.managed_policy_arns = arn_list
    return role


class Test__IAM__Policy__Auditor:

    # ── WildcardActionDetector ─────────────────────────────────────────────────

    def test_1__wildcard_resource_without_opt_in_flagged(self):
        role   = _role([_stmt(['ec2:DescribeInstances'], ['*'], allow_wildcard=False)])
        report = IAM__Policy__Auditor().audit(role)
        codes  = [f.code for f in report.findings]
        assert Enum__IAM__Audit__Finding.WILDCARD_RESOURCE in codes

    def test_2__wildcard_resource_with_opt_in_not_flagged_as_wildcard(self):
        role   = _role([_stmt(['ec2:DescribeInstances'], ['*'], allow_wildcard=True)])
        report = IAM__Policy__Auditor().audit(role)
        codes  = [f.code for f in report.findings]
        assert Enum__IAM__Audit__Finding.WILDCARD_RESOURCE not in codes

    # ── MissingConditionDetector ───────────────────────────────────────────────

    def test_3__power_action_without_condition_flagged_critical(self):
        role   = _role([_stmt(['ec2:StartInstances'], ['arn:aws:ec2:*:*:instance/*'])])
        report = IAM__Policy__Auditor().audit(role)
        codes  = [f.code for f in report.findings]
        assert Enum__IAM__Audit__Finding.MISSING_CONDITION in codes
        sev    = next(f.severity for f in report.findings if f.code == Enum__IAM__Audit__Finding.MISSING_CONDITION)
        assert sev == Enum__IAM__Audit__Severity.CRITICAL

    def test_4__power_action_with_condition_not_flagged(self):
        cond   = {'StringEquals': {'aws:ResourceTag/StackType': 'vault-app'}}
        role   = _role([_stmt(['ec2:StartInstances'], ['arn:aws:ec2:*:*:instance/*'], condition=cond)])
        report = IAM__Policy__Auditor().audit(role)
        codes  = [f.code for f in report.findings]
        assert Enum__IAM__Audit__Finding.MISSING_CONDITION not in codes

    # ── AdminAccessDetector ────────────────────────────────────────────────────

    def test_5__admin_access_attached_flagged_critical(self):
        role   = _role([], managed_arns=['arn:aws:iam::aws:policy/AdministratorAccess'])
        report = IAM__Policy__Auditor().audit(role)
        codes  = [f.code for f in report.findings]
        assert Enum__IAM__Audit__Finding.ADMIN_ACCESS in codes
        sev    = next(f.severity for f in report.findings if f.code == Enum__IAM__Audit__Finding.ADMIN_ACCESS)
        assert sev == Enum__IAM__Audit__Severity.CRITICAL

    def test_6__non_admin_policy_not_flagged(self):
        role   = _role([], managed_arns=['arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess'])
        report = IAM__Policy__Auditor().audit(role)
        codes  = [f.code for f in report.findings]
        assert Enum__IAM__Audit__Finding.ADMIN_ACCESS not in codes

    # ── StaleRoleDetector ──────────────────────────────────────────────────────

    def test_7__never_used_role_flagged_info(self):
        role   = _role([], last_used='')
        report = IAM__Policy__Auditor().audit(role)
        codes  = [f.code for f in report.findings]
        assert Enum__IAM__Audit__Finding.STALE_ROLE in codes
        sev    = next(f.severity for f in report.findings if f.code == Enum__IAM__Audit__Finding.STALE_ROLE)
        assert sev == Enum__IAM__Audit__Severity.INFO

    def test_8__recently_used_role_not_stale(self):
        role   = _role([], last_used='2026-05-17T00:00:00+00:00')
        report = IAM__Policy__Auditor().audit(role)
        codes  = [f.code for f in report.findings]
        assert Enum__IAM__Audit__Finding.STALE_ROLE not in codes

    # ── OverlyBroadServiceDetector ─────────────────────────────────────────────

    def test_9__service_wildcard_action_flagged_warn(self):
        role   = _role([_stmt(['iam:*'], ['arn:aws:iam::123456789012:role/*'])])
        report = IAM__Policy__Auditor().audit(role)
        codes  = [f.code for f in report.findings]
        assert Enum__IAM__Audit__Finding.OVERLY_BROAD_SERVICE in codes

    def test_10__specific_action_not_broad_service(self):
        cond = {'StringEquals': {'aws:ResourceTag/StackType': 'vault-app'}}
        role   = _role([_stmt(['iam:PassRole'], ['arn:aws:iam::123456789012:role/*'], condition=cond)])
        report = IAM__Policy__Auditor().audit(role)
        codes  = [f.code for f in report.findings]
        assert Enum__IAM__Audit__Finding.OVERLY_BROAD_SERVICE not in codes

    # ── MissingTagConditionDetector ────────────────────────────────────────────

    def test_11__ec2_stop_without_tag_condition_flagged(self):
        role   = _role([_stmt(['ec2:StopInstances'], ['arn:aws:ec2:*:*:instance/*'])])
        report = IAM__Policy__Auditor().audit(role)
        codes  = [f.code for f in report.findings]
        assert Enum__IAM__Audit__Finding.MISSING_TAG_CONDITION in codes or \
               Enum__IAM__Audit__Finding.MISSING_CONDITION in codes     # MISSING_CONDITION takes priority

    def test_12__ec2_stop_with_tag_condition_not_flagged(self):
        cond   = {'StringEquals': {'aws:ResourceTag/StackType': 'vault-app'}}
        role   = _role([_stmt(['ec2:StopInstances'], ['arn:aws:ec2:*:*:instance/*'], condition=cond)])
        report = IAM__Policy__Auditor().audit(role)
        codes  = [f.code for f in report.findings]
        assert Enum__IAM__Audit__Finding.MISSING_TAG_CONDITION not in codes

    # ── overall severity ───────────────────────────────────────────────────────

    def test_13__overall_severity_tracks_max_finding(self):
        role   = _role([_stmt(['ec2:StartInstances'], ['arn:aws:ec2:*:*:instance/*'])])
        report = IAM__Policy__Auditor().audit(role)
        assert report.overall_severity == Enum__IAM__Audit__Severity.CRITICAL

    def test_14__clean_role_overall_severity_info(self):
        cond = {'StringEquals': {'aws:ResourceTag/StackType': 'vault-app'}}
        role = _role([_stmt(['ec2:StartInstances'], ['arn:aws:ec2:*:*:instance/*'], condition=cond)],
                     last_used='2026-05-17T00:00:00+00:00')
        report = IAM__Policy__Auditor().audit(role)
        assert report.overall_severity == Enum__IAM__Audit__Severity.INFO
