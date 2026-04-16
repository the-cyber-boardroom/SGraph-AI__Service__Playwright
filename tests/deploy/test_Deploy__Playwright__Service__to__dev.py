# ═══════════════════════════════════════════════════════════════════════════════
# Lambda deploy test (dev) — SG Playwright Service
#
# Placeholder: gated on AWS credentials + successful ECR push. Whole module
# skipped until the Deploy__SGraph_AI__Service__Playwright__Lambda infra
# class lands.
# ═══════════════════════════════════════════════════════════════════════════════

import pytest

pytest.skip(
    'Lambda deploy infra not yet implemented — placeholder.',
    allow_module_level=True,
)


def test_deploy_to_dev():                                                           # Populated when infra lands
    pass
