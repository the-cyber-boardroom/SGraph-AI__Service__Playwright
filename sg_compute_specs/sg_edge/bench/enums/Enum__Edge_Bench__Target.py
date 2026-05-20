# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — sg_edge bench: Enum__Edge_Bench__Target
# Where a scenario runs (doc 05 `--target`): LOCAL = the in-process file-backed
# `sg edge local` stack (no AWS); AWS_BENCH = the live bench environment (the
# AWS-timing scenarios). The AWS_BENCH execution backend is Slice-5/6 live-AWS and
# is not built — those scenarios are registered but skipped with a clear note.
# ═══════════════════════════════════════════════════════════════════════════════

from enum import Enum


class Enum__Edge_Bench__Target(str, Enum):
    LOCAL     = 'local'
    AWS_BENCH = 'aws-bench'

    def __str__(self):
        return self.value
