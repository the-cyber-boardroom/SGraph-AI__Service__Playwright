# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — Content Proxy: Enum__Content_Proxy__Edge
# Front-door strategy. NONE = vault-as-edge (current: TLS + /pw runtime injection).
# CADDY = a dedicated Caddy edge terminates TLS + routes paths; backends are plain
# origins (no vault patch). See the edge-front-door-options review.
# ═══════════════════════════════════════════════════════════════════════════════

from enum import Enum


class Enum__Content_Proxy__Edge(str, Enum):
    NONE  = 'none'                                                                  # vault terminates TLS + hosts /pw via runtime injection
    CADDY = 'caddy'                                                                 # dedicated Caddy edge; vault/playwright become plain origins
