# ═══════════════════════════════════════════════════════════════════════════════
# Docker image build test — SG Playwright Service
#
# Runs through Build__Docker__SGraph_AI__Service__Playwright.build_docker_image()
# so the image is tagged with the ECR URI (<account>.dkr.ecr.<region>.amazonaws.com/
# sgraph_ai_service_playwright:latest). That's the tag the downstream jobs
# reference (ECR push, Local__Docker container start, Lambda image_uri), so
# using the class here guarantees the three paths agree on the image name.
#
# Gated on Docker daemon + AWS credentials — the class constructor probes STS
# to resolve account_id for the image URI. Skipped cleanly locally.
# ═══════════════════════════════════════════════════════════════════════════════

import os
import shutil
import subprocess

import pytest

from sgraph_ai_service_playwright.docker.Build__Docker__SGraph_AI__Service__Playwright import Build__Docker__SGraph_AI__Service__Playwright


def _docker_available() -> bool:
    if shutil.which('docker') is None:
        return False
    result = subprocess.run(['docker', 'info'], capture_output=True, text=True)
    return result.returncode == 0


def _aws_creds_available() -> bool:
    return bool(os.environ.get('AWS_ACCESS_KEY_ID'))    and \
           bool(os.environ.get('AWS_SECRET_ACCESS_KEY'))and \
           bool(os.environ.get('AWS_ACCOUNT_ID'))


@pytest.mark.skipif(not _docker_available()   , reason='docker daemon not available')
@pytest.mark.skipif(not _aws_creds_available(), reason='AWS credentials not set')
def test_build_docker_image():
    build   = Build__Docker__SGraph_AI__Service__Playwright().setup()
    result  = build.build_docker_image()                                            # Build + tag with ECR URI

    assert result is not None

    expected_tag = build.image_uri()                                                # <account>.dkr.ecr.<region>.amazonaws.com/sgraph_ai_service_playwright:latest
    inspect      = subprocess.run(['docker', 'inspect', '--format={{.Id}}', expected_tag],
                                  capture_output=True, text=True)
    assert inspect.returncode == 0, f'image not tagged as {expected_tag} (returncode={inspect.returncode}, stderr={inspect.stderr!r})'
    assert inspect.stdout.strip().startswith('sha256:')
