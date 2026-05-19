# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Schema__ECS__Port_Mapping
# Single container port mapping entry. Pure data — no methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe


class Schema__ECS__Port_Mapping(Type_Safe):
    container_port : int = 0
    protocol       : str = 'tcp'                                                  # values: 'tcp', 'udp'
