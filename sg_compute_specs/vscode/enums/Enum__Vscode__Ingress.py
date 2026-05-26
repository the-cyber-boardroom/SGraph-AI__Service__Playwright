# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — vscode: Enum__Vscode__Ingress
# How the editor is reached.
#   SSM_FORWARD  — editor binds to loopback; reached via SSM port-forward. No
#                  inbound ports. v1 default.
#   PUBLIC_HTTPS — Caddy terminates TLS on :443 + auth portal; SG opens :443.
#                  Slice 3.
# ═══════════════════════════════════════════════════════════════════════════════

from enum import Enum


class Enum__Vscode__Ingress(Enum):
    SSM_FORWARD  = 'ssm-forward'
    PUBLIC_HTTPS = 'public-https'
