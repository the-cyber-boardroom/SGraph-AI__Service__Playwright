# ═══════════════════════════════════════════════════════════════════════════════
# Tests — user_journey manifest
# ═══════════════════════════════════════════════════════════════════════════════

from sg_compute.core.spec.schemas.Schema__Spec__Manifest__Entry import Schema__Spec__Manifest__Entry
from sg_compute.primitives.enums.Enum__Spec__Capability         import Enum__Spec__Capability
from sg_compute.primitives.enums.Enum__Spec__Nav_Group          import Enum__Spec__Nav_Group
from sg_compute.primitives.enums.Enum__Spec__Stability          import Enum__Spec__Stability
from sg_compute_specs.user_journey.manifest                     import MANIFEST


class TestUserJourneyManifest:

    def test__is_manifest_entry(self):
        assert isinstance(MANIFEST, Schema__Spec__Manifest__Entry)

    def test__identity(self):
        assert MANIFEST.spec_id      == 'user-journey'
        assert MANIFEST.display_name == 'User Journey'
        assert str(MANIFEST.version)[0].isdigit()

    def test__browsers_nav_group(self):
        assert MANIFEST.nav_group == Enum__Spec__Nav_Group.BROWSERS

    def test__experimental_and_soon(self):
        assert MANIFEST.stability == Enum__Spec__Stability.EXPERIMENTAL
        assert MANIFEST.soon      is True                                          # lifecycle pending

    def test__capabilities(self):
        assert Enum__Spec__Capability.BROWSER_AUTOMATION in MANIFEST.capabilities
        assert Enum__Spec__Capability.MITM_PROXY         in MANIFEST.capabilities
        assert Enum__Spec__Capability.CONTAINER_RUNTIME  in MANIFEST.capabilities

    def test__extends_the_substrate(self):
        assert set(MANIFEST.extends) == {'vault-app', 'playwright', 'mitmproxy'}
