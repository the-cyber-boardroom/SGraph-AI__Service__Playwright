# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — sg_edge: tests for sg_edge schemas
# ═══════════════════════════════════════════════════════════════════════════════

from unittest import TestCase

from sg_compute.primitives.Safe_Str__IP__Address                       import Safe_Str__IP__Address
from sg_compute.primitives.Safe_Int__Port                              import Safe_Int__Port
from sg_compute_specs.sg_edge.enums.Enum__SG_Edge__Backend__Type        import Enum__SG_Edge__Backend__Type
from sg_compute_specs.sg_edge.enums.Enum__SG_Edge__Idle__Action          import Enum__SG_Edge__Idle__Action
from sg_compute_specs.sg_edge.schemas.Schema__SG_Edge__TXT__Record       import Schema__SG_Edge__TXT__Record
from sg_compute_specs.sg_edge.schemas.Schema__SG_Edge__State__Record     import Schema__SG_Edge__State__Record
from sg_compute_specs.sg_edge.schemas.Schema__SG_Edge__Reconcile__Result import Schema__SG_Edge__Reconcile__Result
from sg_compute_specs.sg_edge.schemas.Schema__SG_Edge__Idle__Result      import Schema__SG_Edge__Idle__Result


class test_Schema__SG_Edge__TXT__Record(TestCase):

    def test_defaults(self):
        record = Schema__SG_Edge__TXT__Record()
        assert int(record.version)  == 1                                         # version-prefixed, defaults to current
        assert str(record.ip)       == ''                                        # empty = not yet assigned
        assert record.type          == Enum__SG_Edge__Backend__Type.EC2
        assert int(record.launched) == 0                                         # 0 = unset

    def test_coerces_primitive_types(self):
        record = Schema__SG_Edge__TXT__Record(ip='10.0.1.5', port=8080, launched=1747700000)
        assert type(record.ip)   is Safe_Str__IP__Address
        assert type(record.port) is Safe_Int__Port

    def test_json_round_trip(self):
        record = Schema__SG_Edge__TXT__Record(ip       = '10.0.1.5'                       ,
                                              port     = 8080                             ,
                                              type     = Enum__SG_Edge__Backend__Type.FARGATE,
                                              launched = 1747700000                       ,
                                              instance = 'i-0abc123def4567890')
        restored = Schema__SG_Edge__TXT__Record.from_json(record.json())
        assert restored.json() == record.json()
        assert restored.type   == Enum__SG_Edge__Backend__Type.FARGATE


class test_Schema__SG_Edge__State__Record(TestCase):

    def test_defaults(self):
        record = Schema__SG_Edge__State__Record()
        assert int(record.zero_streak) == 0
        assert int(record.updated)     == 0

    def test_json_round_trip(self):
        record   = Schema__SG_Edge__State__Record(zero_streak=3, updated=1747700000)
        restored = Schema__SG_Edge__State__Record.from_json(record.json())
        assert restored.json()           == record.json()
        assert int(restored.zero_streak) == 3


class test_Schema__SG_Edge__Reconcile__Result(TestCase):

    def test_defaults(self):
        result = Schema__SG_Edge__Reconcile__Result()
        assert result.current        == 0
        assert result.target         == 0
        assert list(result.launched) == []

    def test_json__coerces_and_serialises(self):
        result = Schema__SG_Edge__Reconcile__Result(current=0, target=2,
                                                    launched=['i-0abc123def4567890', 'i-0def456abc1237890'])
        assert result.json() == {'current': 0, 'target': 2,
                                 'launched': ['i-0abc123def4567890', 'i-0def456abc1237890']}
        restored = Schema__SG_Edge__Reconcile__Result.from_json(result.json())
        assert restored.json() == result.json()


class test_Schema__SG_Edge__Idle__Result(TestCase):

    def test_defaults(self):
        result = Schema__SG_Edge__Idle__Result()
        assert result.action         == Enum__SG_Edge__Idle__Action.INCREMENT
        assert list(result.drained)  == []

    def test_json__teardown_serialises_enum_and_ips(self):
        result = Schema__SG_Edge__Idle__Result(active=0, zero_streak=0,
                                               action=Enum__SG_Edge__Idle__Action.TEARDOWN,
                                               drained=['10.0.0.1', '10.0.0.2'])
        assert result.json() == {'active': 0, 'zero_streak': 0, 'action': 'teardown',
                                 'drained': ['10.0.0.1', '10.0.0.2']}
        restored = Schema__SG_Edge__Idle__Result.from_json(result.json())
        assert restored.json()  == result.json()
        assert restored.action  == Enum__SG_Edge__Idle__Action.TEARDOWN
