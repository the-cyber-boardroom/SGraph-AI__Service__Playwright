# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — runtime_version
# Resolves the version string the FastAPI app surfaces on /docs + /openapi.json
# at startup, in this order:
#
#   1. AGENTIC_APP_VERSION env var — set by Lambda__SP__CLI on the agentic
#      variant; matches the S3 zip key that was just hot-swapped in.
#   2. /var/task/sgraph_ai_service_playwright/version — baked into the image
#      by the Dockerfile. Used on the baseline variant and as a fallback when
#      the agentic env var is missing.
#   3. Hardcoded VERSION_FALLBACK — local dev / tests where neither source
#      is available.
#
# Without this resolver, osbot-fast-api defaults Schema__Fast_API__Config.version
# to its own package version (e.g. v0.38.0), which is meaningless to API
# consumers — they want to know which SP CLI deploy they are talking to.
# ═══════════════════════════════════════════════════════════════════════════════

import os
from pathlib                                                                        import Path


ENV_VAR__AGENTIC_APP_VERSION = 'AGENTIC_APP_VERSION'                                # Set on the agentic Lambda by Lambda__SP__CLI.set_env_vars
IMAGE_VERSION_FILE_RELATIVE  = 'sgraph_ai_service_playwright/version'               # Baked at /var/task/<this> by the dockerfile (same path resolves on local dev from repo root)
VERSION_FALLBACK             = 'v0.0.0'                                             # Local dev / tests with no env var and no version file


def resolve_version() -> str:
    env_value = os.environ.get(ENV_VAR__AGENTIC_APP_VERSION, '').strip()
    if env_value:
        return env_value

    for candidate in version_file_candidates():
        if candidate.is_file():
            text = candidate.read_text().strip()
            if text:
                return text

    return VERSION_FALLBACK


def version_file_candidates():                                                      # /var/task on Lambda + repo root for local dev
    yield Path('/var/task') / IMAGE_VERSION_FILE_RELATIVE
    repo_root = Path(__file__).resolve().parents[2]                                 # sgraph_ai_service_playwright__cli/fast_api/runtime_version.py -> repo root
    yield repo_root / IMAGE_VERSION_FILE_RELATIVE
