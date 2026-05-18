# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — IAM__Policy__Auditor
# Runs a role's inline and managed policies through 7 pattern detectors and
# returns a Schema__IAM__Audit__Report. No AWS calls — the report is built from
# a Schema__IAM__Role that the caller has already loaded.
#
# Detectors (in severity order):
#   WILDCARD_ACTION          — CRITICAL  Action: "*" in any statement
#   MISSING_CONDITION        — CRITICAL  power action without a Condition block
#   ADMIN_ACCESS             — CRITICAL  AdministratorAccess / PowerUserAccess attached
#   WILDCARD_RESOURCE        — WARN      Resource: "*" outside the accepted allowlist
#   OVERLY_BROAD_SERVICE     — WARN      service-prefix wildcard (e.g. "iam:*")
#   MISSING_TAG_CONDITION    — WARN      EC2/S3/Lambda resource without a tag Condition
#   STALE_ROLE               — INFO      role unused for > STALE_DAYS days
# ═══════════════════════════════════════════════════════════════════════════════

import json
from datetime import datetime, timezone, timedelta

from osbot_utils.type_safe.Type_Safe                                                        import Type_Safe

from sgraph_ai_service_playwright__cli.aws.iam.collections.List__Schema__IAM__Audit__Finding import List__Schema__IAM__Audit__Finding
from sgraph_ai_service_playwright__cli.aws.iam.enums.Enum__IAM__Audit__Finding              import Enum__IAM__Audit__Finding
from sgraph_ai_service_playwright__cli.aws.iam.enums.Enum__IAM__Audit__Severity             import Enum__IAM__Audit__Severity
from sgraph_ai_service_playwright__cli.aws.iam.schemas.Schema__IAM__Audit__Finding          import Schema__IAM__Audit__Finding
from sgraph_ai_service_playwright__cli.aws.iam.schemas.Schema__IAM__Audit__Report           import Schema__IAM__Audit__Report
from sgraph_ai_service_playwright__cli.aws.iam.schemas.Schema__IAM__Role                    import Schema__IAM__Role
from sgraph_ai_service_playwright__cli.aws.iam.schemas.Schema__IAM__Statement               import Schema__IAM__Statement

STALE_DAYS = 90

_POWER_ACTION_PREFIXES = ('iam:PassRole', 'ec2:Start', 'ec2:Stop', 'ec2:Terminate', 'lambda:Invoke')

_WILDCARD_RESOURCE_ALLOWLIST = {                                                     # Services that legitimately require Resource: "*"
    'logs'          ,                                                                # CloudWatch Logs (no resource-level perms for CreateLogGroup)
    'cloudwatch'    ,                                                                # CloudWatch Metrics
    'xray'          ,                                                                # X-Ray
    'ec2-Describe'  ,                                                                # EC2 Describe* actions (no resource-level perms)
}

_ADMIN_POLICY_ARNS = {
    'arn:aws:iam::aws:policy/AdministratorAccess',
    'arn:aws:iam::aws:policy/PowerUserAccess',
}

_TAG_SENSITIVE_SERVICES = {'ec2', 's3', 'lambda'}


class IAM__Policy__Auditor(Type_Safe):

    def audit(self, role: Schema__IAM__Role) -> Schema__IAM__Audit__Report:
        findings = List__Schema__IAM__Audit__Finding()
        all_stmts = []
        for policy in role.inline_policies:
            all_stmts.extend(list(policy.statements))

        for idx, stmt in enumerate(all_stmts):
            self._detect_wildcard_action         (stmt, idx, findings)
            self._detect_missing_condition       (stmt, idx, findings)
            self._detect_wildcard_resource       (stmt, idx, findings)
            self._detect_overly_broad_service    (stmt, idx, findings)
            self._detect_missing_tag_condition   (stmt, idx, findings)

        self._detect_admin_access (role, findings)
        self._detect_stale_role   (role, findings)

        overall = self._max_severity(findings)
        return Schema__IAM__Audit__Report(
            role_name        = role.role_name,
            findings         = findings,
            overall_severity = overall,
            passed_count     = len(all_stmts) - len([f for f in findings if f.statement_index >= 0]),
            failed_count     = len(findings),
        )

    # ── detectors ─────────────────────────────────────────────────────────────

    def _detect_wildcard_action(self, stmt: Schema__IAM__Statement,
                                 idx: int, findings: List__Schema__IAM__Audit__Finding) -> None:
        for action in stmt.actions:
            if str(action) == '*':                                                   # Should not happen — Safe_Str__Aws__Action rejects bare "*" — but guard anyway
                findings.append(Schema__IAM__Audit__Finding(
                    severity         = Enum__IAM__Audit__Severity.CRITICAL,
                    code             = Enum__IAM__Audit__Finding.WILDCARD_ACTION,
                    statement_index  = idx,
                    message          = f'Statement {idx}: Action "*" grants all permissions',
                    remediation_hint = 'Replace "*" with an explicit list of required actions.',
                ))
                return
        for action in stmt.actions:                                                  # Also flag service-level wildcards like "iam:*" — detected by OverlyBroadServiceDetector
            pass

    def _detect_missing_condition(self, stmt: Schema__IAM__Statement,
                                   idx: int, findings: List__Schema__IAM__Audit__Finding) -> None:
        for action in stmt.actions:
            a = str(action)
            if any(a.startswith(prefix) for prefix in _POWER_ACTION_PREFIXES):
                if not stmt.condition_json:
                    findings.append(Schema__IAM__Audit__Finding(
                        severity         = Enum__IAM__Audit__Severity.CRITICAL,
                        code             = Enum__IAM__Audit__Finding.MISSING_CONDITION,
                        statement_index  = idx,
                        message          = f'Statement {idx}: power action "{a}" has no Condition block',
                        remediation_hint = 'Add a StringEquals condition on a resource tag (e.g. aws:ResourceTag/StackType).',
                    ))
                    return

    def _detect_wildcard_resource(self, stmt: Schema__IAM__Statement,
                                   idx: int, findings: List__Schema__IAM__Audit__Finding) -> None:
        if stmt.allow_wildcard_resource:
            return                                                                   # Explicit opt-in — only INFO-level
        for resource in stmt.resources:
            if str(resource) == '*':
                service = self._service_of_statement(stmt)
                if service not in _WILDCARD_RESOURCE_ALLOWLIST:
                    findings.append(Schema__IAM__Audit__Finding(
                        severity         = Enum__IAM__Audit__Severity.WARN,
                        code             = Enum__IAM__Audit__Finding.WILDCARD_RESOURCE,
                        statement_index  = idx,
                        message          = f'Statement {idx}: Resource "*" without explicit opt-in flag',
                        remediation_hint = 'Narrow the resource ARN or set allow_wildcard_resource=True with a documented reason.',
                    ))
                    return

    def _detect_overly_broad_service(self, stmt: Schema__IAM__Statement,
                                      idx: int, findings: List__Schema__IAM__Audit__Finding) -> None:
        for action in stmt.actions:
            a = str(action)
            if ':' in a:
                service, verb = a.split(':', 1)
                if verb == '*':
                    findings.append(Schema__IAM__Audit__Finding(
                        severity         = Enum__IAM__Audit__Severity.WARN,
                        code             = Enum__IAM__Audit__Finding.OVERLY_BROAD_SERVICE,
                        statement_index  = idx,
                        message          = f'Statement {idx}: "{a}" grants all {service} actions',
                        remediation_hint = f'Replace "{a}" with the specific {service} actions required.',
                    ))
                    return

    def _detect_missing_tag_condition(self, stmt: Schema__IAM__Statement,
                                       idx: int, findings: List__Schema__IAM__Audit__Finding) -> None:
        if stmt.condition_json:
            return                                                                   # Condition already present
        services_in_resources = set()
        for resource in stmt.resources:
            r = str(resource)
            if r.startswith('arn:aws:'):
                parts = r.split(':')
                if len(parts) >= 3:
                    services_in_resources.add(parts[2])
        if services_in_resources & _TAG_SENSITIVE_SERVICES:
            for action in stmt.actions:
                a = str(action)
                if any(a.startswith(p) for p in ('ec2:Start', 'ec2:Stop', 'ec2:Terminate',
                                                  's3:Delete', 's3:Put', 'lambda:InvokeFunction')):
                    findings.append(Schema__IAM__Audit__Finding(
                        severity         = Enum__IAM__Audit__Severity.WARN,
                        code             = Enum__IAM__Audit__Finding.MISSING_TAG_CONDITION,
                        statement_index  = idx,
                        message          = f'Statement {idx}: mutating action on "{", ".join(services_in_resources & _TAG_SENSITIVE_SERVICES)}" resource without a tag Condition',
                        remediation_hint = 'Add a Condition block using aws:ResourceTag to restrict to tagged resources.',
                    ))
                    return

    def _detect_admin_access(self, role: Schema__IAM__Role,
                              findings: List__Schema__IAM__Audit__Finding) -> None:
        for arn in role.managed_policy_arns:
            if str(arn) in _ADMIN_POLICY_ARNS:
                findings.append(Schema__IAM__Audit__Finding(
                    severity         = Enum__IAM__Audit__Severity.CRITICAL,
                    code             = Enum__IAM__Audit__Finding.ADMIN_ACCESS,
                    statement_index  = -1,
                    message          = f'Managed policy "{arn}" grants admin/power-user access',
                    remediation_hint = 'Detach the admin policy and replace with least-privilege inline policy.',
                ))
                return

    def _detect_stale_role(self, role: Schema__IAM__Role,
                            findings: List__Schema__IAM__Audit__Finding) -> None:
        if not role.last_used:
            findings.append(Schema__IAM__Audit__Finding(
                severity         = Enum__IAM__Audit__Severity.INFO,
                code             = Enum__IAM__Audit__Finding.STALE_ROLE,
                statement_index  = -1,
                message          = 'Role has never been used',
                remediation_hint = 'Delete the role if it is no longer needed.',
            ))
            return
        try:
            last = datetime.fromisoformat(role.last_used.replace('Z', '+00:00'))
            age  = datetime.now(timezone.utc) - last
            if age > timedelta(days=STALE_DAYS):
                findings.append(Schema__IAM__Audit__Finding(
                    severity         = Enum__IAM__Audit__Severity.INFO,
                    code             = Enum__IAM__Audit__Finding.STALE_ROLE,
                    statement_index  = -1,
                    message          = f'Role unused for {age.days} days (threshold: {STALE_DAYS})',
                    remediation_hint = 'Delete the role if it is no longer needed.',
                ))
        except (ValueError, TypeError):
            pass

    # ── helpers ───────────────────────────────────────────────────────────────

    def _service_of_statement(self, stmt: Schema__IAM__Statement) -> str:
        for action in stmt.actions:
            a = str(action)
            if ':' in a:
                return a.split(':', 1)[0]
        return ''

    def _max_severity(self, findings: List__Schema__IAM__Audit__Finding) -> Enum__IAM__Audit__Severity:
        order = {Enum__IAM__Audit__Severity.INFO: 0,
                 Enum__IAM__Audit__Severity.WARN: 1,
                 Enum__IAM__Audit__Severity.CRITICAL: 2}
        best  = Enum__IAM__Audit__Severity.INFO
        for f in findings:
            if order[f.severity] > order[best]:
                best = f.severity
        return best
