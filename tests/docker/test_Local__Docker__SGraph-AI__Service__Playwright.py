# ═══════════════════════════════════════════════════════════════════════════════
# Local container integration smoke — SG Playwright Service
#
# Placeholder: the Docker__SGraph_AI__Service__Playwright__Local infra class
# and /health route are not yet implemented. Whole module is skipped until
# both exist; then this file will start the container and poll /health.
# ═══════════════════════════════════════════════════════════════════════════════

import pytest

pytest.skip(
    'Local container runner and /health route not yet implemented — '
    'placeholder until Phase 1 fast_api routes land.',
    allow_module_level=True,
)


def test_local_container_health():                                                  # Populated when infra lands
    pass
