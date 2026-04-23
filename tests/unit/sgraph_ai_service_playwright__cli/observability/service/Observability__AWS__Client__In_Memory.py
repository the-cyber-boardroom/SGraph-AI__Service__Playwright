# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI (tests) — Observability__AWS__Client__In_Memory
# In-memory replacement for the real AWS client. Tests configure the four
# dictionaries / callable and the service sees deterministic data. Not a mock
# — it is a real subclass that honours the same public surface.
# ═══════════════════════════════════════════════════════════════════════════════

from typing                                                                         import Dict

from osbot_utils.type_safe.type_safe_core.collections.Type_Safe__Dict               import Type_Safe__Dict

from sgraph_ai_service_playwright__cli.observability.schemas.Schema__Stack__Component__AMP        import Schema__Stack__Component__AMP
from sgraph_ai_service_playwright__cli.observability.schemas.Schema__Stack__Component__OpenSearch import Schema__Stack__Component__OpenSearch
from sgraph_ai_service_playwright__cli.observability.schemas.Schema__Stack__Component__Grafana    import Schema__Stack__Component__Grafana
from sgraph_ai_service_playwright__cli.observability.service.Observability__AWS__Client           import Observability__AWS__Client


class Observability__AWS__Client__In_Memory(Observability__AWS__Client):
    fixture_amp        : Dict[str, Schema__Stack__Component__AMP]                   # alias   → AMP component
    fixture_opensearch : Dict[str, Schema__Stack__Component__OpenSearch]            # domain  → OS  component
    fixture_grafana    : Dict[str, Schema__Stack__Component__Grafana]               # ws name → AMG component
    fixture_doc_counts : Dict[str, int]                                             # endpoint → count

    def amp_workspaces(self, region: str) -> Dict[str, Schema__Stack__Component__AMP]:
        return dict(self.fixture_amp)

    def opensearch_domains(self, region: str) -> Dict[str, Schema__Stack__Component__OpenSearch]:
        return dict(self.fixture_opensearch)

    def amg_workspaces(self, region: str) -> Dict[str, Schema__Stack__Component__Grafana]:
        return dict(self.fixture_grafana)

    def opensearch_document_count(self, endpoint: str, region: str, index: str) -> int:
        return int(self.fixture_doc_counts.get(str(endpoint), -1))                  # Safe_Str primitive hash ≠ plain-str hash — normalise for lookup

