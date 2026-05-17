# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Enum__Lambda__Url__Auth_Type
# Authentication mode for Lambda Function URLs.
# NONE = public; AWS_IAM = IAM SigV4 signed requests only.
# ═══════════════════════════════════════════════════════════════════════════════

from enum import Enum


class Enum__Lambda__Url__Auth_Type(str, Enum):
    NONE    = 'NONE'
    AWS_IAM = 'AWS_IAM'

    def __str__(self):
        return self.value
