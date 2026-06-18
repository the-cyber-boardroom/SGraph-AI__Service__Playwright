# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — Content Proxy: Enum__Content_Proxy__Mode
# Deployment mode — drives the load-balancer choice (NLB for direct, ALB for web).
# ═══════════════════════════════════════════════════════════════════════════════

from enum import Enum


class Enum__Content_Proxy__Mode(str, Enum):
    DIRECT_PROXY = 'direct_proxy'                                                   # user's browser configured to use mitmproxy-ext (NLB / L4)
    VAULT_WEB    = 'vault_web'                                                      # user hits the vault app / web page (ALB / L7)
