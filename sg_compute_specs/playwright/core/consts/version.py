# ═══════════════════════════════════════════════════════════════════════════════
# Playwright Service — version constant
#
# Single source of truth: the repo-root `version` file (auto-incremented by the
# CI increment-tag job; also the image tag — see ci-pipeline.yml). Read once at
# import time. The Dockerfile COPYs this file to /app/version so the container
# can read it; repo root is three levels up from the core package dir
# (core → playwright → sg_compute_specs → repo / app).
# ═══════════════════════════════════════════════════════════════════════════════

import os

from osbot_utils.type_safe.primitives.domains.common.safe_str.Safe_Str__Version                 import Safe_Str__Version

import sg_compute_specs.playwright.core as sgraph_ai_service_playwright


FALLBACK_VERSION = 'v0'                                                             # Sentinel if the root version file isn't present (defensive — it should always be COPY'd into the image)


def _read_version_file() -> str:
    core_dir  = sgraph_ai_service_playwright.path                                   # .../sg_compute_specs/playwright/core
    repo_root = os.path.dirname(os.path.dirname(os.path.dirname(core_dir)))         # → repo root (/app in the container)
    path      = os.path.join(repo_root, 'version')
    if os.path.exists(path):
        with open(path, 'r') as f:
            return f.read().strip()
    return FALLBACK_VERSION


version__sgraph_ai_service_playwright = Safe_Str__Version(_read_version_file())
