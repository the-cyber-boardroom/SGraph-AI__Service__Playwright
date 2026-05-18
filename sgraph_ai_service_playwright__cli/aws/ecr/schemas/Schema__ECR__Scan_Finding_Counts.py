# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI aws/ecr — Schema__ECR__Scan_Finding_Counts
# Severity-bucketed count of vulnerabilities reported by an ECR image scan.
# Mirrors AWS findingSeverityCounts keys: CRITICAL / HIGH / MEDIUM / LOW /
# INFORMATIONAL / UNDEFINED.
# Pure data — no methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe


class Schema__ECR__Scan_Finding_Counts(Type_Safe):
    critical      : int = 0
    high          : int = 0
    medium        : int = 0
    low           : int = 0
    informational : int = 0
    undefined     : int = 0
