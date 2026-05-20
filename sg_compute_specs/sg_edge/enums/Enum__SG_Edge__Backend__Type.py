# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — sg_edge: Enum__SG_Edge__Backend__Type
# The `type=` field of an _sg.<slug> routing TXT record. Informational — lets the
# proxy adjust behaviour per backend kind if needed. Values are the lowercase
# tokens that appear verbatim in the TXT record.
# ═══════════════════════════════════════════════════════════════════════════════

from enum import Enum


class Enum__SG_Edge__Backend__Type(str, Enum):
    EC2     = 'ec2'
    FARGATE = 'fargate'

    def __str__(self):
        return self.value
