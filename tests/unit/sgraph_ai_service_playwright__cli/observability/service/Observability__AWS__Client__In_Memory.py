# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI (tests) — Observability__AWS__Client__In_Memory
# In-memory replacement for the real AWS client. Tests configure the four
# dictionaries / callable and the service sees deterministic data. Not a mock
# — it is a real subclass that honours the same public surface.
# ═══════════════════════════════════════════════════════════════════════════════

from typing                                                                         import Dict

from sgraph_ai_service_playwright__cli.observability.enums.Enum__Component__Delete__Outcome      import Enum__Component__Delete__Outcome
from sgraph_ai_service_playwright__cli.observability.enums.Enum__Stack__Component__Kind          import Enum__Stack__Component__Kind
from sgraph_ai_service_playwright__cli.observability.schemas.Schema__Stack__Component__AMP                import Schema__Stack__Component__AMP
from sgraph_ai_service_playwright__cli.observability.schemas.Schema__Stack__Component__Delete__Result     import Schema__Stack__Component__Delete__Result
from sgraph_ai_service_playwright__cli.observability.schemas.Schema__Stack__Component__OpenSearch         import Schema__Stack__Component__OpenSearch
from sgraph_ai_service_playwright__cli.observability.schemas.Schema__Stack__Component__Grafana            import Schema__Stack__Component__Grafana
from sgraph_ai_service_playwright__cli.observability.service.Observability__AWS__Client                   import Observability__AWS__Client


class Observability__AWS__Client__In_Memory(Observability__AWS__Client):
    fixture_amp              : Dict[str, Schema__Stack__Component__AMP]             # alias   → AMP component
    fixture_opensearch       : Dict[str, Schema__Stack__Component__OpenSearch]      # domain  → OS  component
    fixture_grafana          : Dict[str, Schema__Stack__Component__Grafana]         # ws name → AMG component
    fixture_doc_counts       : Dict[str, int]                                       # endpoint → count
    fixture_delete_failures  : Dict[str, list]                                      # kind.value → [names that should force FAILED]
    fixture_delete_errors    : Dict[str, Dict[str, str]]                            # kind.value → {name → error_message}

    def amp_workspaces(self, region: str) -> Dict[str, Schema__Stack__Component__AMP]:
        return dict(self.fixture_amp)

    def opensearch_domains(self, region: str) -> Dict[str, Schema__Stack__Component__OpenSearch]:
        return dict(self.fixture_opensearch)

    def amg_workspaces(self, region: str) -> Dict[str, Schema__Stack__Component__Grafana]:
        return dict(self.fixture_grafana)

    def opensearch_document_count(self, endpoint: str, region: str, index: str) -> int:
        return int(self.fixture_doc_counts.get(str(endpoint), -1))                  # Safe_Str primitive hash ≠ plain-str hash — normalise for lookup

    def amp_delete_workspace(self, region: str, alias: str) -> Schema__Stack__Component__Delete__Result:
        return self.build_delete_result(kind        = Enum__Stack__Component__Kind.AMP,
                                        lookup_dict = self.fixture_amp               ,
                                        lookup_key  = alias                           ,
                                        resource_id = self.fixture_amp.get(str(alias)).workspace_id if self.fixture_amp.get(str(alias)) else '')

    def opensearch_delete_domain(self, region: str, domain_name: str) -> Schema__Stack__Component__Delete__Result:
        return self.build_delete_result(kind        = Enum__Stack__Component__Kind.OPENSEARCH,
                                        lookup_dict = self.fixture_opensearch                ,
                                        lookup_key  = domain_name                            ,
                                        resource_id = str(domain_name)                       )  # OpenSearch uses the domain name directly as the id

    def amg_delete_workspace(self, region: str, name: str) -> Schema__Stack__Component__Delete__Result:
        return self.build_delete_result(kind        = Enum__Stack__Component__Kind.GRAFANA,
                                        lookup_dict = self.fixture_grafana                ,
                                        lookup_key  = name                                 ,
                                        resource_id = self.fixture_grafana.get(str(name)).workspace_id if self.fixture_grafana.get(str(name)) else '')

    def build_delete_result(self, kind        : Enum__Stack__Component__Kind ,       # Shared helper — fixture_delete_failures forces FAILED for deterministic error-path tests
                                  lookup_dict : dict                          ,
                                  lookup_key  : str                           ,
                                  resource_id : str
                           ) -> Schema__Stack__Component__Delete__Result:
        key = str(lookup_key)
        if key in self.fixture_delete_failures.get(kind.value, []):
            return Schema__Stack__Component__Delete__Result(kind          = kind                                                    ,
                                                            outcome       = Enum__Component__Delete__Outcome.FAILED                  ,
                                                            resource_id   = resource_id                                              ,
                                                            error_message = self.fixture_delete_errors.get(kind.value, {}).get(key, 'simulated failure'))
        if key not in lookup_dict:
            return Schema__Stack__Component__Delete__Result(kind        = kind                                         ,
                                                            outcome     = Enum__Component__Delete__Outcome.NOT_FOUND    ,
                                                            resource_id = ''                                           )
        return Schema__Stack__Component__Delete__Result(kind        = kind                                          ,
                                                        outcome     = Enum__Component__Delete__Outcome.DELETED       ,
                                                        resource_id = resource_id                                    )

