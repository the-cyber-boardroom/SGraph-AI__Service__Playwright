# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — vscode: Enum__Vscode__Distribution
# Which VS Code server build runs on the box.
#   CODE_SERVER       — Coder's code-server (Open VSX marketplace). v1 default.
#   OPENVSCODE_SERVER — Gitpod's openvscode-server (Open VSX).
#   SERVE_WEB         — official `code serve-web` (full MS marketplace). Slice 5.
# ═══════════════════════════════════════════════════════════════════════════════

from enum import Enum


class Enum__Vscode__Distribution(Enum):
    CODE_SERVER       = 'code-server'
    OPENVSCODE_SERVER = 'openvscode-server'
    SERVE_WEB         = 'serve-web'
