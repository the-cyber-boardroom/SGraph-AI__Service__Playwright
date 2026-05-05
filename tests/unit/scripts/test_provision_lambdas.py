# ═══════════════════════════════════════════════════════════════════════════════
# Tests — scripts/provision_lambdas.py (v0.1.31 — two-Lambda provisioning)
#
# Scope (unit-level, no real AWS):
#   • module surface             — exposes provision / provision_variant / main.
#   • iteration order            — baseline provisioned BEFORE agentic so the
#                                   always-available fallback is up first.
#   • mode routing               — --mode=full upserts both variants;
#                                   --mode=code-only touches agentic only.
#
# End-to-end create_lambda verification lives in tests/deploy/.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                           import TestCase

from scripts                                                                            import provision_lambdas
from sg_compute_specs.playwright.core.docker.Lambda__Docker__SGraph_AI__Service__Playwright import (MODE__CODE_ONLY ,
                                                                                                MODE__FULL      ,
                                                                                                MODES__ALL      ,
                                                                                                VARIANT__AGENTIC,
                                                                                                VARIANT__BASELINE)


class test_module_surface(TestCase):

    def test__exposes_expected_symbols(self):
        for attr in ('provision', 'provision_variant', 'main'):
            assert hasattr(provision_lambdas, attr), f'missing: {attr}'


class test_variant_ordering(TestCase):

    def test__baseline_is_provisioned_before_agentic(self):                             # Fallback-first: if the agentic S3 loader breaks, the baseline URL still works
        from sg_compute_specs.playwright.core.docker.Lambda__Docker__SGraph_AI__Service__Playwright import VARIANTS__ALL
        assert VARIANTS__ALL.index(VARIANT__BASELINE) < VARIANTS__ALL.index(VARIANT__AGENTIC)


class test_mode_constants(TestCase):

    def test__modes_are_full_and_code_only(self):
        assert MODE__FULL      == 'full'
        assert MODE__CODE_ONLY == 'code-only'
        assert MODES__ALL      == (MODE__FULL, MODE__CODE_ONLY)


class test_provision_mode_routing(TestCase):

    def test__code_only_targets_agentic_only(self):                                     # Baseline bakes code in the image — env refresh there is a no-op, so code-only skips it entirely
        calls = []

        def fake_provision_variant(variant, stage, wait_for_active, mode):
            calls.append((variant, mode))
            return {'variant': variant, 'mode': mode, 'lambda_name': f'sg-playwright-{variant}', 'function_url': None, 'create_result': None}

        original = provision_lambdas.provision_variant
        try:
            provision_lambdas.provision_variant = fake_provision_variant
            result = provision_lambdas.provision(stage='dev', wait_for_active=False, mode=MODE__CODE_ONLY)
        finally:
            provision_lambdas.provision_variant = original

        assert calls          == [(VARIANT__AGENTIC, MODE__CODE_ONLY)]
        assert set(result)    == {VARIANT__AGENTIC}

    def test__full_iterates_both_variants_baseline_first(self):
        calls = []

        def fake_provision_variant(variant, stage, wait_for_active, mode):
            calls.append((variant, mode))
            return {'variant': variant, 'mode': mode, 'lambda_name': f'sg-playwright-{variant}', 'function_url': None, 'create_result': None}

        original = provision_lambdas.provision_variant
        try:
            provision_lambdas.provision_variant = fake_provision_variant
            result = provision_lambdas.provision(stage='dev', wait_for_active=False, mode=MODE__FULL)
        finally:
            provision_lambdas.provision_variant = original

        assert calls       == [(VARIANT__BASELINE, MODE__FULL), (VARIANT__AGENTIC, MODE__FULL)]
        assert set(result) == {VARIANT__BASELINE, VARIANT__AGENTIC}

    def test__unknown_mode_is_rejected(self):
        with self.assertRaises(ValueError) as ctx:
            provision_lambdas.provision(stage='dev', mode='rollback')
        assert "unknown mode 'rollback'" in str(ctx.exception)


class test_argparse_mode_default(TestCase):

    def test__mode_defaults_to_full(self):                                              # CI passes --mode explicitly, but local operators invoking without --mode still get the safe full-upsert path
        import argparse
        parser = argparse.ArgumentParser()
        parser.add_argument('--mode', default=MODE__FULL, choices=MODES__ALL)
        args = parser.parse_args([])
        assert args.mode == MODE__FULL
