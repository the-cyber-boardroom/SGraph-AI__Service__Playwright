# ═══════════════════════════════════════════════════════════════════════════════
# Ephemeral EC2 — Stack__Naming
# AWS Name-tag and SG GroupName helpers. Rules:
#   - aws_name_for_stack: prefixes with stack_type, never doubles the prefix
#   - sg_name_for_stack: always uses -{stack_name}-sg suffix (never sg-* prefix,
#     which AWS reserves for security group IDs)
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe


class Stack__Naming(Type_Safe):
    section_prefix : str = ''                                                       # e.g. 'open-design', 'ollama'

    def aws_name_for_stack(self, stack_name: str) -> str:
        s      = str(stack_name)
        prefix = f'{self.section_prefix}-'
        return s if s.startswith(prefix) else f'{prefix}{s}'

    def sg_name_for_stack(self, stack_name: str) -> str:                            # never starts with 'sg-'
        return f'{str(stack_name)}-sg'
