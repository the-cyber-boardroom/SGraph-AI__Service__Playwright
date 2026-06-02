# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — playwright: manifest
# Typed manifest entry consumed by Spec__Loader.
# ═══════════════════════════════════════════════════════════════════════════════

from pathlib                                                                        import Path

from sg_compute.core.spec.schemas.Schema__Spec__Manifest__Entry                    import Schema__Spec__Manifest__Entry
from sg_compute.primitives.enums.Enum__Spec__Capability                            import Enum__Spec__Capability
from sg_compute.primitives.enums.Enum__Spec__Nav_Group                             import Enum__Spec__Nav_Group
from sg_compute.primitives.enums.Enum__Spec__Stability                             import Enum__Spec__Stability


def _read_version() -> str:                                                     # repo-root `version` (single source of truth; playwright → sg_compute_specs → repo)
    repo_root = Path(__file__).parent.parent.parent
    version_file = repo_root / 'version'
    return version_file.read_text().strip() if version_file.exists() else 'v0'


MANIFEST = Schema__Spec__Manifest__Entry(
    spec_id              = 'playwright'                                         ,
    display_name         = 'Playwright'                                        ,
    icon                 = '🎭'                                               ,
    version              = _read_version()                                    ,
    stability            = Enum__Spec__Stability.STABLE                       ,
    boot_seconds_typical = 30                                                  ,
    capabilities         = [Enum__Spec__Capability.BROWSER_AUTOMATION,
                             Enum__Spec__Capability.VAULT_WRITES      ,
                             Enum__Spec__Capability.SIDECAR_ATTACH    ] ,
    nav_group            = Enum__Spec__Nav_Group.BROWSERS                     ,
)
