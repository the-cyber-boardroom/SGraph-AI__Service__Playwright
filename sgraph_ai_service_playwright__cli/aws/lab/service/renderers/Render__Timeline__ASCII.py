# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI aws/lab — Render__Timeline__ASCII
# Stub — Agent A fills render_event_list; Agent D adds render_waterfall.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe


class Render__Timeline__ASCII(Type_Safe):

    def render_event_list(self, samples: list) -> str:
        raise NotImplementedError('render_event_list: pending Agent A implementation.')

    def render_waterfall(self, samples: list) -> str:
        raise NotImplementedError('render_waterfall: pending Agent D implementation.')
