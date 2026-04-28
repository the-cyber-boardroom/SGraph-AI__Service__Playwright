# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tests for Schema__Prom__Health
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                       import TestCase

from sgraph_ai_service_playwright__cli.prometheus.enums.Enum__Prom__Stack__State    import Enum__Prom__Stack__State
from sgraph_ai_service_playwright__cli.prometheus.schemas.Schema__Prom__Health      import Schema__Prom__Health


class test_Schema__Prom__Health(TestCase):

    def test__defaults_are_unreachable(self):                                       # -1 sentinels ⇒ "couldn't probe"
        h = Schema__Prom__Health()
        assert h.targets_total    == -1
        assert h.targets_up       == -1
        assert h.prometheus_ok    is False
        assert h.state            == Enum__Prom__Stack__State.UNKNOWN
        assert str(h.error)       == ''

    def test__round_trip_via_json(self):
        h = Schema__Prom__Health(stack_name    = 'prom-quiet-fermi'                ,
                                  state         = Enum__Prom__Stack__State.READY    ,
                                  prometheus_ok = True                              ,
                                  targets_total = 5                                 ,
                                  targets_up    = 4                                 )
        again = Schema__Prom__Health.from_json(h.json())
        assert str(again.stack_name)  == 'prom-quiet-fermi'
        assert again.state            == Enum__Prom__Stack__State.READY
        assert again.prometheus_ok    is True
        assert again.targets_total    == 5
        assert again.targets_up       == 4
