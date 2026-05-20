# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — edge: tests for Schema__Edge__Fleet__State
# ═══════════════════════════════════════════════════════════════════════════════

from unittest import TestCase

from sg_compute.primitives.Safe_Str__IP__Address                 import Safe_Str__IP__Address
from sg_compute_specs.edge.enums.Enum__Edge__Fleet__State        import Enum__Edge__Fleet__State
from sg_compute_specs.edge.schemas.Schema__Edge__Fleet__State    import Schema__Edge__Fleet__State


class test_Schema__Edge__Fleet__State(TestCase):

    def test_defaults(self):
        state = Schema__Edge__Fleet__State()
        assert state.state              == Enum__Edge__Fleet__State.ZERO           # $0 baseline
        assert str(state.parent_domain) == ''
        assert list(state.proxy_ips)    == []
        assert int(state.zero_streak)   == 0
        assert int(state.updated_at)    == 0

    def test_proxy_ips_coerces_str_to_typed_ip(self):
        state = Schema__Edge__Fleet__State()
        state.proxy_ips.append('1.2.3.4')
        state.proxy_ips.append('1.2.3.5')
        assert len(state.proxy_ips) == 2
        assert type(state.proxy_ips[0]) is Safe_Str__IP__Address

    def test_json_round_trip(self):
        state = Schema__Edge__Fleet__State(parent_domain = 'cv.sgraph.ai'                ,
                                           state         = Enum__Edge__Fleet__State.ACTIVE,
                                           instance_id   = 'i-0abc123def4567890'         ,
                                           zero_streak   = 3                             ,
                                           updated_at    = 1747700000)
        state.proxy_ips.append('1.2.3.4')
        restored = Schema__Edge__Fleet__State.from_json(state.json())
        assert restored.json()             == state.json()
        assert restored.state              == Enum__Edge__Fleet__State.ACTIVE
        assert str(restored.parent_domain) == 'cv.sgraph.ai'
        assert list(map(str, restored.proxy_ips)) == ['1.2.3.4']
