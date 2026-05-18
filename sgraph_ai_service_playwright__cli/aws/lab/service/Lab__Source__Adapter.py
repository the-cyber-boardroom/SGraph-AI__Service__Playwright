# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI aws/lab — Lab__Source__Adapter
# Implements Source__Contract so lab run results can appear as an sg aws observe
# source. register_all() is called LAZILY from Cli__Lab.py's callback — never
# at module import time, so running `sg aws dns zones list` pays zero cost.
# Foundation: empty streams — agents A/D add registrations.
# ═══════════════════════════════════════════════════════════════════════════════

from sgraph_ai_service_playwright__cli.aws._shared.source_contract.Source__Contract     import Source__Contract
from sgraph_ai_service_playwright__cli.aws._shared.source_contract.Source__Query        import Source__Query
from sgraph_ai_service_playwright__cli.aws._shared.source_contract.Source__Result__Page import Source__Result__Page
from sgraph_ai_service_playwright__cli.aws._shared.source_contract.Source__Stream       import Source__Stream
from sgraph_ai_service_playwright__cli.aws._shared.source_contract.Enum__Source__Aggregation      import Enum__Source__Aggregation
from sgraph_ai_service_playwright__cli.aws._shared.source_contract.Schema__Source__Stats          import Schema__Source__Stats
from sgraph_ai_service_playwright__cli.aws._shared.source_contract.Schema__Source__Stream__Schema import Schema__Source__Stream__Schema


class Lab__Source__Adapter(Source__Contract):

    def connect(self) -> bool:
        return True

    def list_streams(self) -> list:
        return []                                                                   # agents A/D populate this

    def tail(self, stream: str, since: str) -> Source__Stream:
        return Source__Stream()

    def query(self, q: Source__Query) -> Source__Result__Page:
        return Source__Result__Page()

    def stats(self, stream: str, agg: Enum__Source__Aggregation) -> Schema__Source__Stats:
        return Schema__Source__Stats()

    def schema(self, stream: str) -> Schema__Source__Stream__Schema:
        return Schema__Source__Stream__Schema()

    # ── lazy registration ─────────────────────────────────────────────────────

    @staticmethod
    def register_all(source_registry) -> int:
        adapter = Lab__Source__Adapter()
        source_registry.register('lab', adapter)
        return 1
