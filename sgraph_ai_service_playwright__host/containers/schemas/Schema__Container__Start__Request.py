# ═══════════════════════════════════════════════════════════════════════════════
# Host Control Plane — Schema__Container__Start__Request
# Body for POST /containers — starts a named container from an image.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe


class Schema__Container__Start__Request(Type_Safe):
    name    : str   # desired container name
    image   : str   # full image URI
    ports   : dict  # { "8080/tcp": "8080" } host→container port map
    env     : dict  # environment variables
    type_id : str   # plugin type tag
