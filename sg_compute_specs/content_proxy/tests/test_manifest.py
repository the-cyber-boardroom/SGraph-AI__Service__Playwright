# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — Content Proxy: manifest contract test
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                       import TestCase

from sg_compute.core.spec.schemas.Schema__Spec__Manifest__Entry                     import Schema__Spec__Manifest__Entry
from sg_compute.primitives.enums.Enum__Spec__Capability                             import Enum__Spec__Capability
from sg_compute_specs.content_proxy.manifest                                         import MANIFEST


class test_manifest(TestCase):

    def test_manifest_is_typed(self):
        assert isinstance(MANIFEST, Schema__Spec__Manifest__Entry)

    def test_spec_id(self):
        assert MANIFEST.spec_id == 'content_proxy'

    def test_version_is_semver(self):
        parts = MANIFEST.version.split('.')
        assert len(parts) == 3
        assert all(p.isdigit() for p in parts)

    def test_capabilities_non_empty(self):
        assert len(MANIFEST.capabilities) >= 1

    def test_create_endpoint_path(self):
        assert MANIFEST.create_endpoint_path == '/api/specs/content_proxy/stack'

    def test_has_mitm_proxy_capability(self):
        assert Enum__Spec__Capability.MITM_PROXY in MANIFEST.capabilities
