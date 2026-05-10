# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute — Safe_Str__Ollama__Model
# Ollama model reference (e.g. gpt-oss:20b, llama3.3, qwen2.5-coder:7b).
# ═══════════════════════════════════════════════════════════════════════════════

import re

from osbot_utils.type_safe.primitives.core.Safe_Str            import Safe_Str
from osbot_utils.type_safe.primitives.core.enums.Enum__Safe_Str__Regex_Mode import Enum__Safe_Str__Regex_Mode


class Safe_Str__Ollama__Model(Safe_Str):
    regex             = re.compile(r'^[a-z0-9._\-:]+$')
    regex_mode        = Enum__Safe_Str__Regex_Mode.MATCH
    max_length        = 64
    allow_empty       = True
    strict_validation = True
