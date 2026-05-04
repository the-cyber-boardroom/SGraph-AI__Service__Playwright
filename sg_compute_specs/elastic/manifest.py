# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — Elastic: manifest
# ═══════════════════════════════════════════════════════════════════════════════

from sg_compute.core.spec.schemas.Schema__Spec__Manifest__Entry                     import Schema__Spec__Manifest__Entry
from sg_compute.primitives.enums.Enum__Spec__Capability                             import Enum__Spec__Capability
from sg_compute.primitives.enums.Enum__Spec__Nav_Group                              import Enum__Spec__Nav_Group
from sg_compute.primitives.enums.Enum__Spec__Stability                              import Enum__Spec__Stability


MANIFEST = Schema__Spec__Manifest__Entry(
    spec_id              = 'elastic'                               ,
    display_name         = 'Elastic + Kibana'                     ,
    icon                 = '🔎'                                    ,
    version              = '0.1.0'                                 ,
    stability            = Enum__Spec__Stability.STABLE            ,
    boot_seconds_typical = 180                                     ,
    capabilities         = [Enum__Spec__Capability.METRICS]        ,
    nav_group            = Enum__Spec__Nav_Group.DATA              ,
    extends              = []                                      ,
    soon                 = False                                   ,
    create_endpoint_path = '/api/specs/elastic/stack'             ,
)
