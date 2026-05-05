# ═══════════════════════════════════════════════════════════════════════════════
# Local container integration smoke — SG Playwright Service
#
# Real lifecycle: create_or_reuse_container → wait_for_uvicorn → GET /health/info.
# Gated on a reachable Docker daemon with the image pre-built (CI step earlier in
# the pipeline). Skipped locally when the daemon is absent.
# ═══════════════════════════════════════════════════════════════════════════════

import shutil
import subprocess

import pytest

from sg_compute_specs.playwright.core.docker.Local__Docker__SGraph_AI__Service__Playwright import Local__Docker__SGraph_AI__Service__Playwright


def _docker_available() -> bool:
    if shutil.which('docker') is None:
        return False
    return subprocess.run(['docker', 'info'], capture_output=True, text=True).returncode == 0


@pytest.mark.skipif(not _docker_available(), reason='docker daemon not available')
def test_local_container_health():
    local = Local__Docker__SGraph_AI__Service__Playwright().setup()
    try:
        local.create_or_reuse_container()
        is_running = local.wait_for_uvicorn_server_running()                             # Polls container logs for 'Uvicorn running on '
        if not is_running:                                                               # Dump logs + status so the CI failure is diagnosable
            status = local.container.status() if local.container else '<no container>'
            logs   = local.container.logs()   if local.container else '<no logs>'
            pytest.fail(f'uvicorn did not start. status={status!r}\nlogs:\n{logs}')
        body = local.GET('/health/info')                                                 # Fast_API API-key middleware returns 401 here — body still contains JSON, which is enough for a startup probe
        assert body is not None
    finally:
        local.delete_container()
