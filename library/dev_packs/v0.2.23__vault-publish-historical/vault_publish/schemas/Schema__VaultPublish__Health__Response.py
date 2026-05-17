# ═══════════════════════════════════════════════════════════════════════════════
# vault-publish — Schema__VaultPublish__Health__Response
# Returned by GET /vault-publish/health. Reports the four infrastructure layers.
# In the Python-package build the layer checks are not yet wired to live AWS —
# they report their wiring status, not live AWS reachability.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                       import Type_Safe

from vault_publish.schemas.Safe_Str__Message               import Safe_Str__Message


class Schema__VaultPublish__Health__Response(Type_Safe):
    dns_ok          : bool                                # layer 1 — wildcard DNS
    cert_ok         : bool                                # layer 2 — wildcard ACM certificate
    distribution_ok : bool                                # layer 3 — CloudFront distribution
    waker_ok        : bool                                # layer 4 — waker Lambda
    detail          : Safe_Str__Message                   # human-readable summary
