# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — Content Proxy: Enum__Content_Proxy__Tls
# How the vault-app terminates TLS on :443 (via the cert-init sidecar, mirroring
# sg va). Values map to cert-init SG__CERT_INIT__MODE.
# ═══════════════════════════════════════════════════════════════════════════════

from enum import Enum


class Enum__Content_Proxy__Tls(str, Enum):
    NONE        = 'none'                                                            # local dev / vault plain HTTP behind :443
    SELF_SIGNED = 'self-signed'                                                     # cert-init self-signed (IP); browser warns, https works
    LETSENCRYPT = 'letsencrypt'                                                     # cert-init letsencrypt-ip — publicly-trusted IP cert (ACME :80)
    ACM         = 'acm'                                                            # AWS ACM on the ALB (fleet path — not wired on single instance)
