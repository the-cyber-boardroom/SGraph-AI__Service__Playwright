# ═══════════════════════════════════════════════════════════════════════════════
# Playwright Service — image_version constant (v0.1.28 — S3-zip hot-swap)
#
# Tracks the CONTAINER IMAGE version (distinct from the code version in
# `version`). Kept separate because:
#   • Code in the S3 zip is hot-swapped every commit — its version file lives
#     INSIDE the zip, so `version__sgraph_ai_service_playwright` is the code.
#   • The image is rebuilt rarely — its version lives OUTSIDE the zip, at
#     `/var/task/image_version` inside the container (copied by the Dockerfile
#     from the repo-root `image_version` file at build time).
#
# Lookup order:
#   1. `AGENTIC_IMAGE_VERSION` env var — set by `lambda_entry.py` after
#      it reads /var/task/image_version at container start. Wins everywhere
#      once the boot shim has run.
#   2. File next to the package parent (repo-root `image_version`) — local dev,
#      unit tests, in-process imports that bypass the boot shim.
#   3. Hardcoded absolute `/var/task/image_version` — container fallback if
#      the boot shim didn't set the env var (defensive; shouldn't happen).
#   4. Fallback sentinel — `v0`.
# ═══════════════════════════════════════════════════════════════════════════════

import os

from osbot_utils.type_safe.primitives.domains.common.safe_str.Safe_Str__Version                 import Safe_Str__Version

import sg_compute_specs.playwright.core as sgraph_ai_service_playwright


FALLBACK_IMAGE_VERSION = 'v0'                                                       # Sentinel — matches Safe_Str__Version regex; means "unknown / pre-v0.1.28"
ENV_VAR_NAME           = 'AGENTIC_IMAGE_VERSION'
CONTAINER_IMAGE_PATH   = '/var/task/image_version'


def _read_image_version() -> str:
    env_value = os.environ.get(ENV_VAR_NAME)
    if env_value:
        return env_value

    package_dir  = sgraph_ai_service_playwright.path
    repo_root    = os.path.dirname(package_dir)
    repo_file    = os.path.join(repo_root, 'image_version')
    if os.path.exists(repo_file):
        with open(repo_file, 'r') as f:
            return f.read().strip()

    if os.path.exists(CONTAINER_IMAGE_PATH):
        with open(CONTAINER_IMAGE_PATH, 'r') as f:
            return f.read().strip()

    return FALLBACK_IMAGE_VERSION


image_version__sgraph_ai_service_playwright = Safe_Str__Version(_read_image_version())
