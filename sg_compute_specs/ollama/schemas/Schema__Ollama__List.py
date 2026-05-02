# ═══════════════════════════════════════════════════════════════════════════════
# Ephemeral EC2 — Schema__Ollama__List
# ═══════════════════════════════════════════════════════════════════════════════

from typing import List

from osbot_utils.type_safe.Type_Safe                            import Type_Safe
from sg_compute_specs.ollama.schemas.Schema__Ollama__Info  import Schema__Ollama__Info


class Schema__Ollama__List(Type_Safe):
    region  : str                        = ''
    stacks  : List[Schema__Ollama__Info]
    total   : int                        = 0
