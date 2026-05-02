# ═══════════════════════════════════════════════════════════════════════════════
# sg_compute tests — Schema__Spec__Manifest__Entry
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                 import TestCase

from sg_compute.core.spec.schemas.Schema__Spec__Manifest__Entry              import Schema__Spec__Manifest__Entry
from sg_compute.primitives.enums.Enum__Spec__Stability                       import Enum__Spec__Stability
from sg_compute.primitives.enums.Enum__Spec__Nav_Group                       import Enum__Spec__Nav_Group
from sg_compute.primitives.enums.Enum__Spec__Capability                      import Enum__Spec__Capability


class test_Schema__Spec__Manifest__Entry(TestCase):

    def test_default_values(self):
        entry = Schema__Spec__Manifest__Entry()
        assert entry.spec_id              == ''
        assert entry.display_name         == ''
        assert entry.version              == '0.0.0'
        assert entry.stability            == Enum__Spec__Stability.EXPERIMENTAL
        assert entry.nav_group            == Enum__Spec__Nav_Group.OTHER
        assert entry.soon                 is False
        assert entry.capabilities         == []
        assert entry.extends              == []

    def test_full_construction(self):
        entry = Schema__Spec__Manifest__Entry(
            spec_id              = 'firefox'                              ,
            display_name         = 'Firefox'                              ,
            icon                 = '🦊'                                   ,
            version              = '1.2.3'                                ,
            stability            = Enum__Spec__Stability.STABLE           ,
            boot_seconds_typical = 90                                     ,
            capabilities         = [Enum__Spec__Capability.IFRAME_EMBED]  ,
            nav_group            = Enum__Spec__Nav_Group.BROWSERS         ,
            extends              = ['linux', 'docker']                    ,
            soon                 = False                                  ,
            create_endpoint_path = '/api/specs/firefox'                   ,
        )
        assert entry.spec_id     == 'firefox'
        assert entry.version     == '1.2.3'
        assert entry.stability   == Enum__Spec__Stability.STABLE
        assert entry.extends     == ['linux', 'docker']
        assert len(entry.capabilities) == 1
        assert entry.capabilities[0]   == Enum__Spec__Capability.IFRAME_EMBED
