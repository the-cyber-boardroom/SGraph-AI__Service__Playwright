# ═══════════════════════════════════════════════════════════════════════════════
# Ephemeral EC2 — Schema__Open_Design__Create__Response
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe

from ephemeral_ec2.stacks.open_design.schemas.Schema__Open_Design__Info            import Schema__Open_Design__Info


class Schema__Open_Design__Create__Response(Type_Safe):
    stack_info  : Schema__Open_Design__Info = None
    message     : str = ''
    elapsed_ms  : int = 0
