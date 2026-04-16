# ═══════════════════════════════════════════════════════════════════════════════
# Docker image build smoke test — SG Playwright Service
#
# Placeholder until the Docker__SGraph_AI__Service__Playwright__Build infra
# class lands. Invokes `docker build` directly via subprocess.
#
# The CI job runs: pytest ...::test_build_docker_image
# Locally: requires Docker daemon; otherwise skipped via env gate.
# ═══════════════════════════════════════════════════════════════════════════════

import os
import shutil
import subprocess
from pathlib      import Path

import pytest

import sgraph_ai_service_playwright


PACKAGE_ROOT   = Path(sgraph_ai_service_playwright.path)                            # .../sgraph_ai_service_playwright
IMAGE_CONTEXT  = PACKAGE_ROOT / 'docker' / 'images' / 'sgraph_ai_service_playwright'
DOCKERFILE     = IMAGE_CONTEXT / 'dockerfile'
IMAGE_NAME     = 'sgraph_ai_service_playwright'
IMAGE_TAG      = 'ci-build'


def _docker_available() -> bool:                                                    # True if a docker CLI + daemon is reachable
    if shutil.which('docker') is None:
        return False
    result = subprocess.run(['docker', 'info'], capture_output=True, text=True)
    return result.returncode == 0


@pytest.mark.skipif(not _docker_available(), reason='docker daemon not available')
def test_build_docker_image():
    assert DOCKERFILE.is_file(), f"dockerfile not found at {DOCKERFILE}"

    cmd = [
        'docker', 'build'                                   ,
        '-f'                , str(DOCKERFILE)               ,                       # Explicit dockerfile (lowercase name)
        '-t'                , f'{IMAGE_NAME}:{IMAGE_TAG}'   ,                       # Tag
        str(PACKAGE_ROOT.parent)                            ,                       # Build context = repo root
    ]

    env = os.environ.copy()
    env['DOCKER_BUILDKIT'] = '1'                                                    # BuildKit for --from=<image> syntax

    result = subprocess.run(cmd, env=env, capture_output=True, text=True)
    print('STDOUT:', result.stdout[-2000:])                                         # Last 2 KB for CI logs
    print('STDERR:', result.stderr[-2000:])
    assert result.returncode == 0, f"docker build failed with exit code {result.returncode}"

    inspect = subprocess.run(
        ['docker', 'inspect', '--format={{.Id}}', f'{IMAGE_NAME}:{IMAGE_TAG}'],
        capture_output=True, text=True,
    )
    assert inspect.returncode == 0, 'built image not found in local registry'
    assert inspect.stdout.strip().startswith('sha256:')
