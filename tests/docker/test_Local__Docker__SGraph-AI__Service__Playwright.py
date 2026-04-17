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

from sgraph_ai_service_playwright.docker.Local__Docker__SGraph_AI__Service__Playwright import Local__Docker__SGraph_AI__Service__Playwright


def _docker_available() -> bool:
    if shutil.which('docker') is None:
        return False
    return subprocess.run(['docker', 'info'], capture_output=True, text=True).returncode == 0


@pytest.mark.skipif(not _docker_available(), reason='docker daemon not available')
def test_local_container_health():
    local = Local__Docker__SGraph_AI__Service__Playwright().setup()
    try:
        local.create_or_reuse_container()
        assert local.wait_for_uvicorn_server_running() is True                           # Polls container logs for 'Uvicorn running on '
        body = local.GET('/health/info')
        assert 'sg-playwright' in body                                                   # service_name leaks through
    finally:
        local.delete_container()
