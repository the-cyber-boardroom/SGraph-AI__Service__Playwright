# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — Firefox: manifest
# Typed manifest entry consumed by Spec__Loader.
# ═══════════════════════════════════════════════════════════════════════════════

from sg_compute.core.spec.schemas.Schema__Spec__Manifest__Entry                     import Schema__Spec__Manifest__Entry
from sg_compute.primitives.enums.Enum__Spec__Capability                             import Enum__Spec__Capability
from sg_compute.primitives.enums.Enum__Spec__Nav_Group                              import Enum__Spec__Nav_Group
from sg_compute.primitives.enums.Enum__Spec__Stability                              import Enum__Spec__Stability


MANIFEST = Schema__Spec__Manifest__Entry(
    spec_id               = 'firefox'                               ,
    display_name          = 'Firefox (noVNC browser)'               ,
    icon                  = '🦊'                                    ,
    version               = '0.1.0'                                 ,
    stability             = Enum__Spec__Stability.EXPERIMENTAL      ,
    boot_seconds_typical  = 90                                      ,
    capabilities          = [Enum__Spec__Capability.MITM_PROXY      ,
                              Enum__Spec__Capability.IFRAME_EMBED   ,
                              Enum__Spec__Capability.AMI_BAKE       ],
    nav_group             = Enum__Spec__Nav_Group.BROWSERS          ,
    extends               = []                                      ,
    soon                  = False                                   ,
    create_endpoint_path  = '/api/specs/firefox/stack'              ,
)
