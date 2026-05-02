# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — Prometheus: manifest
# ═══════════════════════════════════════════════════════════════════════════════

from sg_compute.core.spec.schemas.Schema__Spec__Manifest__Entry                     import Schema__Spec__Manifest__Entry
from sg_compute.primitives.enums.Enum__Spec__Capability                             import Enum__Spec__Capability
from sg_compute.primitives.enums.Enum__Spec__Nav_Group                              import Enum__Spec__Nav_Group
from sg_compute.primitives.enums.Enum__Spec__Stability                              import Enum__Spec__Stability


MANIFEST = Schema__Spec__Manifest__Entry(
    spec_id               = 'prometheus'                       ,
    display_name          = 'Prometheus + cAdvisor'            ,
    icon                  = '🔥'                               ,
    version               = '0.1.0'                            ,
    stability             = Enum__Spec__Stability.STABLE       ,
    boot_seconds_typical  = 120                                ,
    capabilities          = [Enum__Spec__Capability.METRICS    ],
    nav_group             = Enum__Spec__Nav_Group.OBSERVABILITY ,
    extends               = []                                 ,
    soon                  = False                              ,
    create_endpoint_path  = '/api/specs/prometheus/stack'      ,
)
