# ═══════════════════════════════════════════════════════════════════════════════
# Lambda smoke test (dev) — SG Playwright Service
#
# Placeholder: invoked after deploy-lambda succeeds. Whole module skipped
# until there is a deployed Lambda to exercise.
# ═══════════════════════════════════════════════════════════════════════════════

import pytest

pytest.skip(
    'No deployed Lambda yet — placeholder smoke test.',
    allow_module_level=True,
)


def test_smoke_dev_lambda():                                                        # Populated when deploy lands
    pass
