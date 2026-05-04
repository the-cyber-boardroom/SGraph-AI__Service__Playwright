# ═══════════════════════════════════════════════════════════════════════════════
# Agent Mitmproxy — version constant
#
# Reads the package-root `version` file once at import time so every call site
# shares a single Safe_Str__Version instance without re-reading the file.
# ═══════════════════════════════════════════════════════════════════════════════

import os

from osbot_utils.type_safe.primitives.domains.common.safe_str.Safe_Str__Version import Safe_Str__Version

import sg_compute_specs.mitmproxy as _mitmproxy_pkg


def _read_version_file() -> str:
    path = os.path.join(_mitmproxy_pkg.path, 'version')
    with open(path, 'r') as f:
        return f.read().strip()


version__agent_mitmproxy = Safe_Str__Version(_read_version_file())
