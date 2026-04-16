# ═══════════════════════════════════════════════════════════════════════════════
# Lambda smoke test (dev) — SG Playwright Service
#
# Placeholder: invoked after deploy-lambda succeeds. Test is skipped at
# function level so pytest collects one item and exits 0 (not exit-code 5).
# Will be populated when there is a deployed Lambda to exercise.
# ═══════════════════════════════════════════════════════════════════════════════

import pytest

SKIP_REASON = 'No deployed Lambda yet — placeholder smoke test.'


@pytest.mark.skip(reason=SKIP_REASON)
def test_smoke_dev_lambda():                                                        # Populated when deploy lands
    pass
