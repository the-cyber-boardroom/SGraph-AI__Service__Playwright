# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — vault_app: manifest
# Typed manifest entry consumed by Spec__Loader.
# ═══════════════════════════════════════════════════════════════════════════════

from pathlib                                                                        import Path

from sg_compute.core.spec.schemas.Schema__Spec__Manifest__Entry                    import Schema__Spec__Manifest__Entry
from sg_compute.primitives.enums.Enum__Spec__Capability                            import Enum__Spec__Capability
from sg_compute.primitives.enums.Enum__Spec__Nav_Group                             import Enum__Spec__Nav_Group
from sg_compute.primitives.enums.Enum__Spec__Stability                             import Enum__Spec__Stability


def _read_version() -> str:
    return (Path(__file__).parent / 'version').read_text().strip()


MANIFEST = Schema__Spec__Manifest__Entry(
    spec_id              = 'vault_app'                                                         ,
    display_name         = 'Vault App'                                                         ,
    icon                 = '🗄️'                                                               ,
    version              = _read_version()                                                     ,
    stability            = Enum__Spec__Stability.EXPERIMENTAL                                  ,
    boot_seconds_typical = 45                                                                  ,  # just-vault; faster from a baked AMI
    capabilities         = [Enum__Spec__Capability.VAULT_WRITES       ,                            # core (just-vault mode)
                             Enum__Spec__Capability.SIDECAR_ATTACH     ,
                             Enum__Spec__Capability.CONTAINER_RUNTIME  ,
                             Enum__Spec__Capability.BROWSER_AUTOMATION ,                           # optional — --with-playwright
                             Enum__Spec__Capability.MITM_PROXY         ] ,                         # optional — --with-playwright
    nav_group            = Enum__Spec__Nav_Group.STORAGE                                       ,
)
