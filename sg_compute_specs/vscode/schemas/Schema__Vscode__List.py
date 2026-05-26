# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — vscode: Schema__Vscode__List
# ═══════════════════════════════════════════════════════════════════════════════

from typing import List

from osbot_utils.type_safe.Type_Safe                      import Type_Safe
from sg_compute_specs.vscode.schemas.Schema__Vscode__Info import Schema__Vscode__Info


class Schema__Vscode__List(Type_Safe):
    region : str                       = ''
    stacks : List[Schema__Vscode__Info]
    total  : int                       = 0
