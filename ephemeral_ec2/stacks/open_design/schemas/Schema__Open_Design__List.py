# ═══════════════════════════════════════════════════════════════════════════════
# Ephemeral EC2 — Schema__Open_Design__List
# ═══════════════════════════════════════════════════════════════════════════════

from typing                          import List

from osbot_utils.type_safe.Type_Safe import Type_Safe

from ephemeral_ec2.stacks.open_design.schemas.Schema__Open_Design__Info import Schema__Open_Design__Info


class Schema__Open_Design__List(Type_Safe):
    region  : str                       = ''
    stacks  : List[Schema__Open_Design__Info]
    total   : int                       = 0
