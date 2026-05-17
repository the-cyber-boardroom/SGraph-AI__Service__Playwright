# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Creds__Scope__Catalogue__In_Memory
# Dict-backed fake catalogue for unit tests. No filesystem writes.
# Overrides load/save to use an in-memory dict.
# ═══════════════════════════════════════════════════════════════════════════════

from sgraph_ai_service_playwright__cli.aws.creds.service.Creds__Scope__Catalogue import Creds__Scope__Catalogue


class Creds__Scope__Catalogue__In_Memory(Creds__Scope__Catalogue):

    def __init__(self):
        super().__init__()
        self._data = {'scopes': {}}                                             # in-memory backing store; shared across calls

    def load(self) -> dict:
        return self._data

    def save(self, data: dict):                                                 # No filesystem write — just update in-memory dict
        self._data = data
