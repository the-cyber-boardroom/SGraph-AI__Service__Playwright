# ═══════════════════════════════════════════════════════════════════════════════
# Playwright Service — version constant
#
# Reads the repo-root `version` file once at import time so every call site can
# share a single Safe_Str__Version instance without re-reading the file.
# ═══════════════════════════════════════════════════════════════════════════════

import os

from osbot_utils.type_safe.primitives.domains.common.safe_str.Safe_Str__Version                 import Safe_Str__Version

import sgraph_ai_service_playwright


def _read_version_file() -> str:
    path = os.path.join(sgraph_ai_service_playwright.path, 'version')
    with open(path, 'r') as f:
        return f.read().strip()


version__sgraph_ai_service_playwright = Safe_Str__Version(_read_version_file())
