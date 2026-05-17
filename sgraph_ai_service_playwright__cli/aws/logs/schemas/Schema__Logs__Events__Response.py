# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Schema__Logs__Events__Response
# Result of a filter_log_events call — list of events + metadata.
# Pure data — no methods.
# ═══════════════════════════════════════════════════════════════════════════════

from typing                                                                       import List

from osbot_utils.type_safe.Type_Safe                                              import Type_Safe

from sgraph_ai_service_playwright__cli.aws.logs.schemas.Schema__Logs__Event       import Schema__Logs__Event


class Schema__Logs__Events__Response(Type_Safe):
    events          : list = None         # list[Schema__Logs__Event]
    searched_streams: int  = 0
    more_available  : bool = False

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if self.events is None:
            self.events = []
