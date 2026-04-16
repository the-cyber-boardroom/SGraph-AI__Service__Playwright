# ═══════════════════════════════════════════════════════════════════════════════
# Local container integration smoke — SG Playwright Service
#
# Placeholder: the Docker__SGraph_AI__Service__Playwright__Local infra class
# and /health route are not yet implemented. Test is skipped at function level
# so pytest still collects one item and exits 0 (not exit-code 5).
# Will be populated to start the container and poll /health once the infra
# class and route land.
# ═══════════════════════════════════════════════════════════════════════════════

import pytest

SKIP_REASON = ('Local container runner and /health route not yet implemented — '
               'placeholder until Phase 1 fast_api routes land.')


@pytest.mark.skip(reason=SKIP_REASON)
def test_local_container_health():                                                  # Populated when infra lands
    pass
