# ═══════════════════════════════════════════════════════════════════════════════
# ECR push test — SG Playwright Service
#
# Placeholder: gated on AWS credentials being set in GitHub secrets. The job
# only runs when check-aws-credentials == 'true', but this file still skips
# at function level so pytest collects an item and exits 0 (not exit-code 5).
# Will be populated to create the ECR repo, tag + push the image once the
# Docker__SGraph_AI__Service__Playwright__ECR infra class lands.
# ═══════════════════════════════════════════════════════════════════════════════

import pytest

SKIP_REASON = ('ECR push infra (Docker__SGraph_AI__Service__Playwright__ECR) not '
               'yet implemented — placeholder.')


@pytest.mark.skip(reason=SKIP_REASON)
def test_ecr_setup_and_push():                                                      # Populated when infra lands
    pass
