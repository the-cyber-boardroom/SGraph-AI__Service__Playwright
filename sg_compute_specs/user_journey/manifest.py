# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — user_journey: manifest
# Typed manifest entry consumed by Spec__Loader. Discoverable now; the EC2
# lifecycle service lands with the gated deploy harness (soon=True until then).
# ═══════════════════════════════════════════════════════════════════════════════

from pathlib                                                                        import Path

from sg_compute.core.spec.schemas.Schema__Spec__Manifest__Entry                    import Schema__Spec__Manifest__Entry
from sg_compute.primitives.enums.Enum__Spec__Capability                            import Enum__Spec__Capability
from sg_compute.primitives.enums.Enum__Spec__Nav_Group                             import Enum__Spec__Nav_Group
from sg_compute.primitives.enums.Enum__Spec__Stability                             import Enum__Spec__Stability


def _read_version() -> str:
    return (Path(__file__).parent / 'core' / 'version').read_text().strip()


MANIFEST = Schema__Spec__Manifest__Entry(
    spec_id              = 'user-journey'                                       ,
    display_name         = 'User Journey'                                       ,
    icon                 = '🧭'                                                ,
    version              = _read_version()                                      ,
    stability            = Enum__Spec__Stability.EXPERIMENTAL                   ,
    boot_seconds_typical = 45                                                   ,
    capabilities         = [Enum__Spec__Capability.BROWSER_AUTOMATION,
                            Enum__Spec__Capability.MITM_PROXY        ,
                            Enum__Spec__Capability.CONTAINER_RUNTIME ,
                            Enum__Spec__Capability.VAULT_WRITES      ] ,
    nav_group            = Enum__Spec__Nav_Group.BROWSERS                       ,
    extends              = ['vault-app', 'playwright', 'mitmproxy']             ,   # composes on the shipped substrate
    soon                 = True                                                 ,   # lifecycle service lands with the deploy harness
)
