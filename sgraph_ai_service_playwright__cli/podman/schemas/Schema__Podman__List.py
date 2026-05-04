# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Schema__Podman__List
# Returned by `sp podman list`. Pure data.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe

from sgraph_ai_service_playwright__cli.observability.primitives.Safe_Str__AWS__Region   import Safe_Str__AWS__Region
from sgraph_ai_service_playwright__cli.podman.collections.List__Schema__Podman__Info import List__Schema__Podman__Info


class Schema__Podman__List(Type_Safe):
    region       : Safe_Str__AWS__Region
    stacks       : List__Schema__Podman__Info
    total        : int = 0
