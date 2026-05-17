# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute — Enum__Spec__Capability
# Closed set of capabilities a spec can advertise.
# Seed values per architecture §8.1; Architect locks set before phase 3.
# ═══════════════════════════════════════════════════════════════════════════════

from enum import Enum


class Enum__Spec__Capability(str, Enum):
    VAULT_WRITES      = 'vault-writes'
    AMI_BAKE          = 'ami-bake'
    SIDECAR_ATTACH    = 'sidecar-attach'
    REMOTE_SHELL      = 'remote-shell'
    METRICS           = 'metrics'
    MITM_PROXY        = 'mitm-proxy'
    IFRAME_EMBED      = 'iframe-embed'
    WEBRTC            = 'webrtc'
    CONTAINER_RUNTIME = 'container-runtime'
    BROWSER_AUTOMATION= 'browser-automation'
    LLM_INFERENCE     = 'llm-inference'
    DESIGN_TOOL       = 'design-tool'
    SUBDOMAIN_ROUTING = 'subdomain-routing'
