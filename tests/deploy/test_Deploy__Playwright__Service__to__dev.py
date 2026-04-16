# ═══════════════════════════════════════════════════════════════════════════════
# Lambda deploy test (dev) — SG Playwright Service
#
# Placeholder: gated on AWS credentials + successful ECR push. Test is skipped
# at function level so pytest collects one item and exits 0 (not exit-code 5).
# Will be populated when the Deploy__SGraph_AI__Service__Playwright__Lambda
# infra class lands.
# ═══════════════════════════════════════════════════════════════════════════════

import pytest

SKIP_REASON = 'Lambda deploy infra not yet implemented — placeholder.'


@pytest.mark.skip(reason=SKIP_REASON)
def test_deploy_to_dev():                                                           # Populated when infra lands
    pass
