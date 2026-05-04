# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Schema__Image__Build__Result
# Output of Image__Build__Service.build(). Captures everything a caller
# might want without exposing the docker SDK image object — keeps the
# service free to swap implementations later.
#
# Pure data.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe

from sgraph_ai_service_playwright__cli.image.collections.List__Str                  import List__Str


class Schema__Image__Build__Result(Type_Safe):
    image_id    : str                                                               # Docker image id, e.g. 'sha256:...'
    image_tags  : List__Str                                                         # Every tag assigned at build time (usually one)
    duration_ms : int                  = 0                                          # Build wall-clock; 0 if the caller did not time it
