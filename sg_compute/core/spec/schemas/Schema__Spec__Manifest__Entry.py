# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute — Schema__Spec__Manifest__Entry
# The typed catalogue entry for one spec. Single source of truth.
# Every spec's manifest.py exposes MANIFEST: Schema__Spec__Manifest__Entry.
# ═══════════════════════════════════════════════════════════════════════════════

from typing                                                                   import List

from osbot_utils.type_safe.Type_Safe                                          import Type_Safe

from sg_compute.primitives.enums.Enum__Spec__Capability                      import Enum__Spec__Capability
from sg_compute.primitives.enums.Enum__Spec__Nav_Group                       import Enum__Spec__Nav_Group
from sg_compute.primitives.enums.Enum__Spec__Stability                       import Enum__Spec__Stability


class Schema__Spec__Manifest__Entry(Type_Safe):
    spec_id               : str                        = ''
    display_name          : str                        = ''
    icon                  : str                        = ''
    version               : str                        = '0.0.0'
    stability             : Enum__Spec__Stability      = Enum__Spec__Stability.EXPERIMENTAL
    boot_seconds_typical  : int                        = 60
    capabilities          : List[Enum__Spec__Capability]
    nav_group             : Enum__Spec__Nav_Group      = Enum__Spec__Nav_Group.OTHER
    extends               : List[str]                  # spec_ids this spec composes on top of
    soon                  : bool                       = False
    create_endpoint_path  : str                        = ''
