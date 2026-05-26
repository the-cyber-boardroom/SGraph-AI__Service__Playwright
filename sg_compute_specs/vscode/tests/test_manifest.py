# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — vscode: manifest contract test
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                       import TestCase

from sg_compute.core.spec.schemas.Schema__Spec__Manifest__Entry     import Schema__Spec__Manifest__Entry
from sg_compute.primitives.enums.Enum__Spec__Nav_Group              import Enum__Spec__Nav_Group
from sg_compute_specs.vscode.manifest                               import MANIFEST


class test_manifest(TestCase):

    def test_manifest_is_typed(self):
        assert isinstance(MANIFEST, Schema__Spec__Manifest__Entry)

    def test_spec_id(self):
        assert MANIFEST.spec_id == 'vscode'

    def test_version_is_semver(self):
        parts = MANIFEST.version.split('.')
        assert len(parts) == 3
        assert all(p.isdigit() for p in parts)

    def test_capabilities_non_empty(self):
        assert len(MANIFEST.capabilities) >= 1

    def test_nav_group_is_dev(self):
        assert MANIFEST.nav_group == Enum__Spec__Nav_Group.DEV

    def test_create_endpoint_path(self):
        assert MANIFEST.create_endpoint_path.startswith('/api/specs/')
