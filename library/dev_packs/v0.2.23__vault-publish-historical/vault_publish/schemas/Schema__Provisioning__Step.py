# ═══════════════════════════════════════════════════════════════════════════════
# vault-publish — Schema__Provisioning__Step
# One allowlisted provisioning step. Produced only by Manifest__Interpreter and
# consumed only by Control_Plane__Client. Pure data — no methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                          import Type_Safe

from vault_publish.schemas.Enum__Provisioning__Step_Kind      import Enum__Provisioning__Step_Kind
from vault_publish.schemas.Safe_Str__Message                  import Safe_Str__Message


class Schema__Provisioning__Step(Type_Safe):
    kind   : Enum__Provisioning__Step_Kind                   # which allowlisted operation
    target : Safe_Str__Message                               # the operand (runtime name, path, env pair, ...)
