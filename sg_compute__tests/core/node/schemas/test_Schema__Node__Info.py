# ═══════════════════════════════════════════════════════════════════════════════
# sg_compute tests — Schema__Node__Info
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                 import TestCase

from sg_compute.core.node.schemas.Schema__Node__Info                         import Schema__Node__Info
from sg_compute.primitives.enums.Enum__Node__State                           import Enum__Node__State


class test_Schema__Node__Info(TestCase):

    def test_defaults(self):
        info = Schema__Node__Info()
        assert info.node_id        == ''
        assert info.spec_id        == ''
        assert info.state          == Enum__Node__State.BOOTING
        assert info.public_ip      == ''
        assert info.uptime_seconds == 0

    def test_full_construction(self):
        info = Schema__Node__Info(
            node_id       = 'firefox-quiet-fermi-7421'  ,
            spec_id       = 'firefox'                   ,
            region        = 'eu-west-2'                 ,
            state         = Enum__Node__State.READY     ,
            public_ip     = '1.2.3.4'                   ,
            private_ip    = '10.0.0.5'                  ,
            instance_id   = 'i-0a1b2c3d4e5f67890'      ,
            instance_type = 't3.large'                  ,
            ami_id        = 'ami-0a1b2c3d4e5f67890'     ,
            uptime_seconds= 300                          ,
        )
        assert info.node_id  == 'firefox-quiet-fermi-7421'
        assert info.state    == Enum__Node__State.READY
        assert info.region   == 'eu-west-2'
