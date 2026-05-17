# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Schema__Logs__Query__Result
# Result from get_query_results — status + rows.
# Pure data — no methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe


class Schema__Logs__Query__Result(Type_Safe):
    query_id : str  = ''
    status   : str  = ''     # 'Running' | 'Complete' | 'Failed' | 'Cancelled'
    rows     : list = None   # list[Schema__Logs__Query__Row]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if self.rows is None:
            self.rows = []

    def is_complete(self) -> bool:
        return self.status == 'Complete'
