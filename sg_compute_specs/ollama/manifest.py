# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — Ollama manifest
# ═══════════════════════════════════════════════════════════════════════════════

from pathlib                                                                  import Path

from sg_compute.core.spec.schemas.Schema__Spec__Manifest__Entry              import Schema__Spec__Manifest__Entry
from sg_compute.primitives.enums.Enum__Spec__Capability                      import Enum__Spec__Capability
from sg_compute.primitives.enums.Enum__Spec__Nav_Group                       import Enum__Spec__Nav_Group
from sg_compute.primitives.enums.Enum__Spec__Stability                       import Enum__Spec__Stability


def _read_version() -> str:
    return (Path(__file__).parent / 'version').read_text().strip()


MANIFEST = Schema__Spec__Manifest__Entry(
    spec_id              = 'ollama'                                ,
    display_name         = 'Ollama'                                ,
    icon                 = '🦙'                                    ,
    version              = _read_version()                         ,
    stability            = Enum__Spec__Stability.EXPERIMENTAL      ,
    boot_seconds_typical = 120                                     ,
    capabilities         = [Enum__Spec__Capability.LLM_INFERENCE]  ,
    nav_group            = Enum__Spec__Nav_Group.AI                ,
    extends              = []                                      ,
    soon                 = False                                   ,
    create_endpoint_path = '/api/specs/ollama'                     ,
)
