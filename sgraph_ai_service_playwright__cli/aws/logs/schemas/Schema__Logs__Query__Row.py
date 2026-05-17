# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Schema__Logs__Query__Row
# One result row from a CloudWatch Logs Insights query.
# Pure data — no methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe


class Schema__Logs__Query__Row(Type_Safe):
    fields : dict = None       # field_name → value mapping from Insights result

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if self.fields is None:
            self.fields = {}

    def get(self, key: str, default: str = '') -> str:
        return self.fields.get(key, default)
