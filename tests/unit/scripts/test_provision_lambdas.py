# ═══════════════════════════════════════════════════════════════════════════════
# Tests — scripts/provision_lambdas.py (v0.1.31 — two-Lambda provisioning)
#
# Scope (unit-level, no real AWS):
#   • module surface             — exposes provision / provision_variant / main.
#   • iteration order            — baseline provisioned BEFORE agentic so the
#                                   always-available fallback is up first.
#
# End-to-end create_lambda verification lives in tests/deploy/.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                           import TestCase

from scripts                                                                            import provision_lambdas
from sgraph_ai_service_playwright.docker.Lambda__Docker__SGraph_AI__Service__Playwright import VARIANT__AGENTIC, VARIANT__BASELINE


class test_module_surface(TestCase):

    def test__exposes_expected_symbols(self):
        for attr in ('provision', 'provision_variant', 'main'):
            assert hasattr(provision_lambdas, attr), f'missing: {attr}'


class test_variant_ordering(TestCase):

    def test__baseline_is_provisioned_before_agentic(self):                             # Fallback-first: if the agentic S3 loader breaks, the baseline URL still works
        from sgraph_ai_service_playwright.docker.Lambda__Docker__SGraph_AI__Service__Playwright import VARIANTS__ALL
        assert VARIANTS__ALL.index(VARIANT__BASELINE) < VARIANTS__ALL.index(VARIANT__AGENTIC)
