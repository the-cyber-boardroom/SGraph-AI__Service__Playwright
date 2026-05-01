# ═══════════════════════════════════════════════════════════════════════════════
# Ephemeral EC2 — Schema__Ollama__Create__Response
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                            import Type_Safe
from ephemeral_ec2.stacks.ollama.schemas.Schema__Ollama__Info  import Schema__Ollama__Info


class Schema__Ollama__Create__Response(Type_Safe):
    stack_info  : Schema__Ollama__Info = None
    message     : str = ''
    elapsed_ms  : int = 0
