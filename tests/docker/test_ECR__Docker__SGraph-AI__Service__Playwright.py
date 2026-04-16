# ═══════════════════════════════════════════════════════════════════════════════
# ECR push test — SG Playwright Service
#
# Placeholder: gated on AWS credentials being set in GitHub secrets. The job
# only runs when check-aws-credentials == 'true', but this module additionally
# skips so local pytest runs do not try to push.
# ═══════════════════════════════════════════════════════════════════════════════

import pytest

pytest.skip(
    'ECR push infra (Docker__SGraph_AI__Service__Playwright__ECR) not yet '
    'implemented — placeholder.',
    allow_module_level=True,
)


def test_ecr_setup_and_push():                                                      # Populated when infra lands
    pass
