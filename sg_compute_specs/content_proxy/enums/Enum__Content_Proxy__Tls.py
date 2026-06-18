# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — Content Proxy: Enum__Content_Proxy__Tls
# How TLS is provisioned on :443. NONE = local / self-signed.
# ═══════════════════════════════════════════════════════════════════════════════

from enum import Enum


class Enum__Content_Proxy__Tls(str, Enum):
    NONE        = 'none'                                                            # local dev / vault-app self-signed default
    LETSENCRYPT = 'letsencrypt'                                                     # vault app self-terminates with an LE cert (IP/DNS)
    ACM         = 'acm'                                                             # AWS ACM cert on the ALB (L7)
