# ═══════════════════════════════════════════════════════════════════════════════
# ECR push integration test — SG Playwright Service
#
# Real ECR round-trip: create_repository (idempotent) → push_image → verify
# the image actually landed in the registry. The Docker SDK's images.push()
# does NOT raise when the local image is missing — it streams JSON lines with
# errorDetail entries and returns normally. Asserting on push_result alone
# lets silent failures through, so this test scans the push output for
# errorDetail and re-checks ECR for the image tag.
#
# Gated on AWS credentials + Docker daemon.
# ═══════════════════════════════════════════════════════════════════════════════

import json
import os
import shutil
import subprocess

import pytest

from sgraph_ai_service_playwright.docker.ECR__Docker__SGraph_AI__Service__Playwright   import ECR__Docker__SGraph_AI__Service__Playwright


IMAGE_NAME = 'sgraph_ai_service_playwright'
IMAGE_TAG  = 'latest'


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
    assert setup_result is True or setup_result is not None

    push_result  = ecr.publish_docker_image()                                           # Blocking; streams layers
    assert push_result is not None

    push_lines   = push_result.get('push_json_lines', '') or ''                         # Scan stream for errorDetail (silent-failure detector)
    errors       = []
    for raw_line in push_lines.splitlines() if isinstance(push_lines, str) else push_lines:
        try    : entry = json.loads(raw_line) if isinstance(raw_line, str) else raw_line
        except Exception: continue
        if isinstance(entry, dict) and entry.get('errorDetail'):
            errors.append(entry['errorDetail'].get('message', str(entry['errorDetail'])))
    assert not errors, f'docker push reported errorDetail entries: {errors}'

    image_tags   = []                                                                   # describe_images returns imageTags (plural list) per imageDetails entry
    for detail in (ecr.create_image_ecr.ecr.images(IMAGE_NAME) or []):
        image_tags.extend(detail.get('imageTags', []) or [])
    assert IMAGE_TAG in image_tags, f'expected tag {IMAGE_TAG!r} in ECR repo {IMAGE_NAME!r}; got {image_tags}'
