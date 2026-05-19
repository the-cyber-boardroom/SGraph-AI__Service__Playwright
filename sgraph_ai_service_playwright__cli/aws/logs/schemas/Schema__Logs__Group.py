# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Schema__Logs__Group
# One CloudWatch Logs log group record.  Pure data — no methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe


class Schema__Logs__Group(Type_Safe):
    name           : str = ''    # logGroupName
    retention_days : int = 0     # 0 means no retention policy set
    arn            : str = ''    # logGroupArn
    stored_bytes   : int = 0     # storedBytes
