# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Enum__IAM__Scope__Breadth
# Scope classification for IAM policy statements.
# WILDCARD = "*:*" or equivalent; PREFIX_SCOPED = service:*; SPECIFIC = named action+resource
# ═══════════════════════════════════════════════════════════════════════════════

from enum import Enum


class Enum__IAM__Scope__Breadth(str, Enum):
    WILDCARD       = 'wildcard'         # sts:* / *:*  / Resource=*
    PREFIX_SCOPED  = 'prefix_scoped'    # s3:Get* or Resource=arn:aws:s3:::bucket/*
    SPECIFIC       = 'specific'         # exact action + exact resource

    def __str__(self):
        return self.value
