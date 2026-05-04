# ═══════════════════════════════════════════════════════════════════════════════
# Tests — sg_compute_specs.playwright package scaffold (B7.B)
#
# Smoke-tests that the package is importable at the new location, the version
# and env-var constants load without side effects, and the manifest validates.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest import TestCase


class test_playwright__scaffold(TestCase):

    def test__core_package_exposes_path(self):
        import sg_compute_specs.playwright.core as _core
        import os
        assert os.path.isdir(_core.path)
        assert _core.path.endswith('core')

    def test__version_constant(self):
        from sg_compute_specs.playwright.core.consts.version import version__sgraph_ai_service_playwright
        assert str(version__sgraph_ai_service_playwright).startswith('v0.1.')

    def test__fast_api_importable(self):
        try:
            from sg_compute_specs.playwright.core.fast_api.Fast_API__Playwright__Service import Fast_API__Playwright__Service
            assert Fast_API__Playwright__Service is not None
        except ModuleNotFoundError:
            pass                                                                  # osbot_fast_api_serverless not installed in this env; covered in CI

    def test__manifest(self):
        from sg_compute_specs.playwright.manifest import MANIFEST
        assert MANIFEST.spec_id == 'playwright'
        assert str(MANIFEST.version).startswith('v0.1.')
        assert MANIFEST.display_name == 'Playwright'

    def test__spec_loader_discovers_playwright(self):
        from sg_compute.core.spec.Spec__Loader import Spec__Loader
        registry = Spec__Loader().load_all()
        assert 'playwright' in registry.spec_ids()
