# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Schema__Route53__Change__Result
# Result returned by Route 53 after a change_resource_record_sets call.
# Pure data — no methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                 import Type_Safe


class Schema__Route53__Change__Result(Type_Safe):
    change_id    : str                                                                # e.g. /change/C1234567890ABC
    status       : str                                                                # PENDING | INSYNC
    submitted_at : str                                                                # ISO datetime string
