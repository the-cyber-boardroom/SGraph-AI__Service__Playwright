# ═══════════════════════════════════════════════════════════════════════════════
# vault-publish — Schema__VaultPublish__Wake__Request
# Body for POST /vault-publish/wake — the route the waker Lambda calls when
# CloudFront fails over to it for a cold slug.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                       import Type_Safe

from vault_publish.schemas.Safe_Str__Message               import Safe_Str__Message


class Schema__VaultPublish__Wake__Request(Type_Safe):
    slug : Safe_Str__Message                              # slug parsed from the Host header
