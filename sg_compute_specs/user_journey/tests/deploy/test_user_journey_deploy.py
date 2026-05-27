# ═══════════════════════════════════════════════════════════════════════════════
# Deploy-via-pytest — user-journey conductor image (GATED, author-only)
#
# Numbered tests run top-down: build the conductor image, run it, confirm uvicorn
# answered, tear it down. The whole module SKIPS cleanly when no Docker daemon is
# reachable — so it never runs (or fails) in the unit-test environment. It has NOT been
# executed here (no daemon); it is the harness an operator/CI runs on a Docker host.
#
#   SG_UJ__DEPLOY_TEST=1  docker present  →  python -m pytest sg_compute_specs/user_journey/tests/deploy/
# ═══════════════════════════════════════════════════════════════════════════════

import os
import socket
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path

import pytest

from sg_compute_specs.user_journey.core.conductor.Worker__Runtime__Docker import docker_available

REPO_ROOT   = Path(__file__).resolve().parents[4]
DOCKERFILE  = 'sg_compute_specs/user_journey/docker/conductor/Dockerfile'
IMAGE_TAG   = 'sg-uj-conductor:deploy-test'
CONTAINER   = 'sg-uj-conductor-deploy-test'
HOST_PORT   = 8077

pytestmark = pytest.mark.skipif(
    not (os.environ.get('SG_UJ__DEPLOY_TEST') == '1' and docker_available()),
    reason='gated deploy test — needs SG_UJ__DEPLOY_TEST=1 and a reachable Docker daemon')


def _run(cmd, check=True, timeout=600):
    proc = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True, timeout=timeout)
    if check and proc.returncode != 0:
        raise AssertionError(f'{" ".join(cmd[:3])} failed:\n{proc.stderr}')
    return proc


def _wait_port(port, timeout=60):
    deadline = time.time() + timeout
    while time.time() < deadline:
        with socket.socket() as sock:
            sock.settimeout(2)
            if sock.connect_ex(('127.0.0.1', port)) == 0:
                return True
        time.sleep(1)
    return False


def test_1__build_conductor_image():
    _run(['docker', 'build', '-f', DOCKERFILE, '-t', IMAGE_TAG, '.'])


def test_2__run_conductor():
    _run(['docker', 'rm', '-f', CONTAINER], check=False)                            # clear any stale container
    _run(['docker', 'run', '-d', '--name', CONTAINER, '-p', f'{HOST_PORT}:8000',
          '-e', 'FAST_API__AUTH__API_KEY__VALUE=deploy-test-key', IMAGE_TAG])
    assert _wait_port(HOST_PORT), 'conductor port never opened'


def test_3__conductor_answers_http():                                               # any HTTP response = uvicorn booted
    try:
        status = urllib.request.urlopen(f'http://127.0.0.1:{HOST_PORT}/openapi.json', timeout=5).status
    except urllib.error.HTTPError as http_error:
        status = http_error.code                                                    # 401/404 still means the app answered
    assert status is not None


def test_4__teardown():
    _run(['docker', 'rm', '-f', CONTAINER], check=False)
