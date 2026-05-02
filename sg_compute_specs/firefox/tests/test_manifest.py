# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — Firefox: tests for manifest
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                       import TestCase

from sg_compute.core.spec.schemas.Schema__Spec__Manifest__Entry                     import Schema__Spec__Manifest__Entry
from sg_compute.primitives.enums.Enum__Spec__Capability                             import Enum__Spec__Capability
from sg_compute.primitives.enums.Enum__Spec__Nav_Group                              import Enum__Spec__Nav_Group
from sg_compute.primitives.enums.Enum__Spec__Stability                              import Enum__Spec__Stability
from sg_compute_specs.firefox.manifest                                               import MANIFEST


class test_manifest(TestCase):

    def test_manifest_is_schema_spec_manifest_entry(self):
        assert isinstance(MANIFEST, Schema__Spec__Manifest__Entry)

    def test_spec_id(self):
        assert MANIFEST.spec_id == 'firefox'

    def test_display_name(self):
        assert 'Firefox' in MANIFEST.display_name

    def test_icon(self):
        assert MANIFEST.icon == '🦊'

    def test_nav_group_is_browsers(self):
        assert MANIFEST.nav_group == Enum__Spec__Nav_Group.BROWSERS

    def test_stability_is_experimental(self):
        assert MANIFEST.stability == Enum__Spec__Stability.EXPERIMENTAL

    def test_capabilities_include_mitm_proxy(self):
        assert Enum__Spec__Capability.MITM_PROXY in MANIFEST.capabilities

    def test_capabilities_include_iframe_embed(self):
        assert Enum__Spec__Capability.IFRAME_EMBED in MANIFEST.capabilities

    def test_capabilities_include_ami_bake(self):
        assert Enum__Spec__Capability.AMI_BAKE in MANIFEST.capabilities

    def test_create_endpoint_path(self):
        assert MANIFEST.create_endpoint_path == '/api/specs/firefox/stack'

    def test_boot_seconds_typical(self):
        assert MANIFEST.boot_seconds_typical == 90

    def test_soon_is_false(self):
        assert MANIFEST.soon is False
