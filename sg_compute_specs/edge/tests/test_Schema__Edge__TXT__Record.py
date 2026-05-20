# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — edge: tests for Schema__Edge__TXT__Record
# ═══════════════════════════════════════════════════════════════════════════════

from unittest import TestCase

from sg_compute.primitives.Safe_Str__IP__Address              import Safe_Str__IP__Address
from sg_compute.primitives.Safe_Int__Port                     import Safe_Int__Port
from sg_compute_specs.edge.enums.Enum__Edge__Backend__Type    import Enum__Edge__Backend__Type
from sg_compute_specs.edge.schemas.Schema__Edge__TXT__Record  import Schema__Edge__TXT__Record


class test_Schema__Edge__TXT__Record(TestCase):

    def test_defaults(self):
        record = Schema__Edge__TXT__Record()
        assert int(record.version) == 1                                          # version-prefixed, defaults to current
        assert str(record.ip)      == ''                                         # empty = not yet assigned
        assert record.type         == Enum__Edge__Backend__Type.EC2
        assert int(record.launched) == 0                                         # 0 = unset

    def test_coerces_primitive_types(self):
        record = Schema__Edge__TXT__Record(ip='10.0.1.5', port=8080, launched=1747700000)
        assert type(record.ip)   is Safe_Str__IP__Address
        assert type(record.port) is Safe_Int__Port

    def test_json_round_trip(self):
        record = Schema__Edge__TXT__Record(ip       = '10.0.1.5'                     ,
                                           port     = 8080                           ,
                                           type     = Enum__Edge__Backend__Type.FARGATE,
                                           launched = 1747700000                     ,
                                           instance = 'i-0abc123def4567890')
        restored = Schema__Edge__TXT__Record.from_json(record.json())
        assert restored.json() == record.json()
        assert restored.type   == Enum__Edge__Backend__Type.FARGATE
