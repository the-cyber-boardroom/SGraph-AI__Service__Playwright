# ═══════════════════════════════════════════════════════════════════════════════
# Ephemeral EC2 — Schema__Local_Claude__List
# ═══════════════════════════════════════════════════════════════════════════════

from typing import List

from osbot_utils.type_safe.Type_Safe                                             import Type_Safe
from sg_compute_specs.local_claude.schemas.Schema__Local_Claude__Info import Schema__Local_Claude__Info


class Schema__Local_Claude__List(Type_Safe):
    region  : str                              = ''
    stacks  : List[Schema__Local_Claude__Info]
    total   : int                              = 0
