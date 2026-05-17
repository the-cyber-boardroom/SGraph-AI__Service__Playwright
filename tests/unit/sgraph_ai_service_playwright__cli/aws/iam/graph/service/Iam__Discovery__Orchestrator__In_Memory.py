# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Iam__Discovery__Orchestrator__In_Memory
# Subclass of Iam__Discovery__Orchestrator that uses IAM__AWS__Client__In_Memory.
# Lets tests inject fake IAM data without any real AWS calls.
# ═══════════════════════════════════════════════════════════════════════════════

from sgraph_ai_service_playwright__cli.aws.iam.graph.service.Iam__Discovery__Orchestrator import Iam__Discovery__Orchestrator
from tests.unit.sgraph_ai_service_playwright__cli.aws.iam.service.IAM__AWS__Client__In_Memory import IAM__AWS__Client__In_Memory


class Iam__Discovery__Orchestrator__In_Memory(Iam__Discovery__Orchestrator):

    def __init__(self):
        self.iam_client = IAM__AWS__Client__In_Memory()

    def setup(self):
        return self                                                              # already set up
