# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Schema__Logs__Event
# One CloudWatch Logs event record.  Pure data — no methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                             import Type_Safe

from sgraph_ai_service_playwright__cli.aws.logs.primitives.Safe_Str__Log__Stream import Safe_Str__Log__Stream


class Schema__Logs__Event(Type_Safe):
    event_id    : str                 = ''    # CloudWatch eventId (dedup key)
    timestamp   : int                 = 0     # epoch ms
    log_stream  : Safe_Str__Log__Stream
    message     : str                 = ''
