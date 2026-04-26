# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Stack__Naming
# Section-aware naming helpers shared by every sister stack section
# (sp el, sp os, sp prom, sp vnc). Single source of truth for the two
# AWS naming conventions that EVERY stack needs:
#
#   - aws_name_for_stack(): builds the EC2 Name tag with a section prefix,
#     skipping the prefix when the logical stack_name already carries it.
#     Avoids cosmetic doubles like "elastic-elastic-quiet-fermi" — see
#     CLAUDE.md "AWS Resource Naming" rule and the Elastic__AWS__Client
#     header comment for the full backstory.
#
#   - sg_name_for_stack(): SG GroupName helper. AWS reserves the literal
#     "sg-*" prefix for security group IDs, so the GroupName must NOT
#     start with "sg-". We use a "-sg" suffix instead.
#
# Each section binds an instance with its own section_prefix:
#     ELASTIC_NAMING = Stack__Naming(section_prefix='elastic')
#     OS_NAMING      = Stack__Naming(section_prefix='opensearch')
#     PROM_NAMING    = Stack__Naming(section_prefix='prometheus')
#     VNC_NAMING     = Stack__Naming(section_prefix='vnc')
#
# Plan reference: team/comms/plans/v0.1.96__playwright-stack-split__02__api-consolidation.md
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe


class Stack__Naming(Type_Safe):
    section_prefix : str = ''                                                       # e.g. 'elastic', 'opensearch', 'prometheus', 'vnc'

    def aws_name_for_stack(self, stack_name: str) -> str:                           # AWS Name tag — always carries the section prefix, never doubled
        s      = str(stack_name)
        prefix = f'{self.section_prefix}-'
        return s if s.startswith(prefix) else f'{prefix}{s}'

    def sg_name_for_stack(self, stack_name: str) -> str:                            # SG GroupName — never starts with "sg-" (AWS reserves that prefix for SG IDs)
        return f'{str(stack_name)}-sg'
