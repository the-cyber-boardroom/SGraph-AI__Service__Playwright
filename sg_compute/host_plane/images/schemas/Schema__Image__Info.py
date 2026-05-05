# ═══════════════════════════════════════════════════════════════════════════════
# Host Control Plane — Schema__Image__Info
# Per-image record returned by GET /images and GET /images/{name}.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe


class Schema__Image__Info(Type_Safe):
    id         : str       # short 12-char digest
    tags       : list      # list of "repo:tag" strings
    size_mb    : float     # compressed image size in MiB
    created_at : str       # ISO-8601
