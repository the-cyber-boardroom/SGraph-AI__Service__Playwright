# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tests for Schema__OS__Health
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                       import TestCase

from sgraph_ai_service_playwright__cli.opensearch.enums.Enum__OS__Stack__State      import Enum__OS__Stack__State
from sgraph_ai_service_playwright__cli.opensearch.schemas.Schema__OS__Health        import Schema__OS__Health


class test_Schema__OS__Health(TestCase):

    def test__defaults_are_unreachable(self):                                       # -1 sentinels ⇒ "couldn't probe"
        h = Schema__OS__Health()
        assert h.node_count       == -1
        assert h.active_shards    == -1
        assert h.doc_count        == -1
        assert h.dashboards_ok    is False
        assert h.os_endpoint_ok   is False
        assert h.state            == Enum__OS__Stack__State.UNKNOWN
        assert str(h.cluster_status) == ''

    def test__round_trip_via_json(self):
        h = Schema__OS__Health(stack_name='os-quiet-fermi'                      ,
                               state          = Enum__OS__Stack__State.READY    ,
                               cluster_status = 'green'                          ,
                               node_count     = 1                                ,
                               active_shards  = 5                                ,
                               doc_count      = 1234                             ,
                               dashboards_ok  = True                             ,
                               os_endpoint_ok = True                             )
        again = Schema__OS__Health.from_json(h.json())
        assert str(again.stack_name)     == 'os-quiet-fermi'
        assert again.state               == Enum__OS__Stack__State.READY
        assert str(again.cluster_status) == 'green'
        assert again.node_count          == 1
        assert again.dashboards_ok       is True
