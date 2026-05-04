# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Enum__Plugin__Capability
# Closed vocabulary of capabilities a plugin may declare in its manifest.
# The UI uses these to decide which configuration panels to show.
# ═══════════════════════════════════════════════════════════════════════════════

from enum import Enum


class Enum__Plugin__Capability(str, Enum):
    VAULT_WRITES    = 'vault-writes'     # plugin persists secrets/blobs via /vault/plugin/...
    AMI_BAKE        = 'ami-bake'         # plugin supports FROM_AMI / BAKE_AMI creation modes
    SIDECAR_ATTACH  = 'sidecar-attach'   # plugin supports container sidecar attachment
    REMOTE_SHELL    = 'remote-shell'     # plugin supports SSM shell (sp connect)
    METRICS         = 'metrics'          # plugin exposes Prometheus-compatible metrics
    MITM_PROXY      = 'mitm-proxy'       # plugin includes a MITM proxy (mitmproxy/mitmweb)
    IFRAME_EMBED    = 'iframe-embed'     # plugin's UI is safe to embed in an iframe
