# ═══════════════════════════════════════════════════════════════════════════════
# SG Credentials — Schema__Audit__Event
# One line in ~/.sg/audit.jsonl.
# Full v0.2.28 shape: includes identity ARN, session ID, chain, duration, etc.
# Pure data — no methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                           import Type_Safe

from sgraph_ai_service_playwright__cli.credentials.enums.Enum__Audit__Action                  import Enum__Audit__Action
from sgraph_ai_service_playwright__cli.credentials.primitives.Safe_Str__Aws__Arn              import Safe_Str__Aws__Arn
from sgraph_ai_service_playwright__cli.credentials.primitives.Safe_Str__Audit__Command_Args   import Safe_Str__Audit__Command_Args
from sgraph_ai_service_playwright__cli.credentials.primitives.Safe_Str__Error__Message        import Safe_Str__Error__Message
from sgraph_ai_service_playwright__cli.credentials.primitives.Safe_Str__Iso8601_Timestamp     import Safe_Str__Iso8601_Timestamp
from sgraph_ai_service_playwright__cli.credentials.primitives.Safe_Str__Role__Name            import Safe_Str__Role__Name
from sgraph_ai_service_playwright__cli.credentials.primitives.Safe_Str__Sts__Session_Name     import Safe_Str__Sts__Session_Name


class Schema__Audit__Event(Type_Safe):
    timestamp       : Safe_Str__Iso8601_Timestamp               # UTC ISO 8601 — YYYY-MM-DDTHH:MM:SSZ
    role            : Safe_Str__Role__Name                       # role context (may be empty)
    identity_arn    : Safe_Str__Aws__Arn                         # STS GetCallerIdentity — empty if static creds
    session_id      : Safe_Str__Sts__Session_Name                # CloudTrail-correlatable — empty if static creds
    session_expiry  : Safe_Str__Iso8601_Timestamp                # empty if static creds (no expiry)
    action          : Enum__Audit__Action
    command_args    : Safe_Str__Audit__Command_Args              # allowlist-redacted argv string
    resolved_via    : list                                       # list[str] role-name chain e.g. ['default', 'admin']
    duration_ms     : int                                        # non-negative; 0 if not measured
    success         : bool
    error           : Safe_Str__Error__Message                   # empty on success
