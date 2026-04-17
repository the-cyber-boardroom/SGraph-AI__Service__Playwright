# ═══════════════════════════════════════════════════════════════════════════════
# ECR push integration test — SG Playwright Service
#
# Real ECR round-trip: create_repository (idempotent) → push_image. Gated on
# AWS credentials being set in the environment (GitHub secrets in CI). Runs
# AFTER the docker-build job has tagged the image locally.
#
# Skipped when AWS creds or Docker daemon are absent, so pytest still collects
# the item and exits 0 locally.
# ═══════════════════════════════════════════════════════════════════════════════

import os
import shutil
import subprocess

import pytest

from sgraph_ai_service_playwright.docker.ECR__Docker__SGraph_AI__Service__Playwright   import ECR__Docker__SGraph_AI__Service__Playwright


def _docker_available() -> bool:
    if shutil.which('docker') is None:
        return False
    result = subprocess.run(['docker', 'info'], capture_output=True, text=True)
    return result.returncode == 0


def _aws_creds_available() -> bool:
    return bool(os.environ.get('AWS_ACCESS_KEY_ID')) and bool(os.environ.get('AWS_SECRET_ACCESS_KEY'))


@pytest.mark.skipif(not _docker_available()   , reason='docker daemon not available')
@pytest.mark.skipif(not _aws_creds_available(), reason='AWS credentials not set')
def test_ecr_setup_and_push():
    ecr = ECR__Docker__SGraph_AI__Service__Playwright().setup()

    setup_result = ecr.ecr_setup()                                                      # Idempotent; succeeds if repo exists
    assert setup_result is not None

    push_result  = ecr.publish_docker_image()                                           # Blocking; streams layers
    assert push_result is not None
