# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Observability__Service
# Pure-logic entry point for observability-stack operations. Callable from both
# the typer CLI and a FastAPI route (see brief v0.1.72) without either layer
# knowing about the other.
#
# This slice covers the read-only surface: list_stacks, get_stack_info.
# Mutation operations (create/delete/backup/restore/dashboard-import) will be
# added in subsequent commits, one method per commit, so each is reviewable
# in isolation.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe
from osbot_utils.type_safe.type_safe_core.decorators.type_safe                      import type_safe

from osbot_aws.AWS_Config                                                           import AWS_Config

from sgraph_ai_service_playwright__cli.observability.collections.List__Stack__Component__Delete__Result import List__Stack__Component__Delete__Result
from sgraph_ai_service_playwright__cli.observability.collections.List__Stack__Info                      import List__Stack__Info
from sgraph_ai_service_playwright__cli.observability.primitives.Safe_Str__AWS__Region                   import Safe_Str__AWS__Region
from sgraph_ai_service_playwright__cli.observability.primitives.Safe_Str__Stack__Name                   import Safe_Str__Stack__Name
from sgraph_ai_service_playwright__cli.observability.schemas.Schema__Stack__Delete__Response            import Schema__Stack__Delete__Response
from sgraph_ai_service_playwright__cli.observability.schemas.Schema__Stack__Info                        import Schema__Stack__Info
from sgraph_ai_service_playwright__cli.observability.schemas.Schema__Stack__List                        import Schema__Stack__List
from sgraph_ai_service_playwright__cli.observability.service.Observability__AWS__Client                 import Observability__AWS__Client


DEFAULT_REGION          = 'eu-west-2'                                               # Matches the legacy CLI fallback
DEFAULT_OPENSEARCH_INDEX = 'sg-playwright-logs'                                     # Index the playwright service writes into


class Observability__Service(Type_Safe):                                            # Pure-logic orchestrator
    aws_client       : Observability__AWS__Client                                   # Injected; tests swap with an in-memory subclass
    opensearch_index : str                          = DEFAULT_OPENSEARCH_INDEX      # Where document_count reads from

    @type_safe
    def list_stacks(self, region: Safe_Str__AWS__Region = None) -> Schema__Stack__List:
        resolved_region = self.resolve_region(region)
        amp_by_name     = self.aws_client.amp_workspaces     (resolved_region)
        os_by_name      = self.aws_client.opensearch_domains (resolved_region)
        amg_by_name     = self.aws_client.amg_workspaces     (resolved_region)

        stacks = List__Stack__Info()
        for name in sorted(set(amp_by_name) | set(os_by_name) | set(amg_by_name)):
            stacks.append(Schema__Stack__Info(name       = name                     ,
                                              region     = resolved_region          ,
                                              amp        = amp_by_name .get(name)   ,
                                              opensearch = os_by_name  .get(name)   ,
                                              grafana    = amg_by_name .get(name)   ))
        return Schema__Stack__List(region = resolved_region,
                                   stacks = stacks         )

    @type_safe
    def get_stack_info(self, name   : Safe_Str__Stack__Name     ,
                             region : Safe_Str__AWS__Region = None
                        ) -> Schema__Stack__Info:
        resolved_region = self.resolve_region(region)
        amp_by_name     = self.aws_client.amp_workspaces     (resolved_region)
        os_by_name      = self.aws_client.opensearch_domains (resolved_region)
        amg_by_name     = self.aws_client.amg_workspaces     (resolved_region)

        lookup = str(name)                                                          # Safe_Str__Stack__Name has its own __hash__; plain-dict keys come from AWS
        info   = Schema__Stack__Info(name       = name                    ,
                                     region     = resolved_region         ,
                                     amp        = amp_by_name .get(lookup),
                                     opensearch = os_by_name  .get(lookup),
                                     grafana    = amg_by_name .get(lookup))

        if info.opensearch is not None and info.opensearch.endpoint:                # Top up the document count once we know the endpoint
            info.opensearch.document_count = self.aws_client.opensearch_document_count(
                endpoint = info.opensearch.endpoint ,
                region   = resolved_region          ,
                index    = self.opensearch_index    )
        return info

    @type_safe
    def delete_stack(self, name   : Safe_Str__Stack__Name     ,
                           region : Safe_Str__AWS__Region = None
                      ) -> Schema__Stack__Delete__Response:
        resolved_region = self.resolve_region(region)
        lookup          = str(name)                                                 # Plain-str key to match AWS response shapes

        results = List__Stack__Component__Delete__Result()
        results.append(self.aws_client.amp_delete_workspace   (region = resolved_region, alias       = lookup))
        results.append(self.aws_client.opensearch_delete_domain(region = resolved_region, domain_name = lookup))
        results.append(self.aws_client.amg_delete_workspace   (region = resolved_region, name        = lookup))

        return Schema__Stack__Delete__Response(name    = name            ,
                                               region  = resolved_region ,
                                               results = results         )

    def resolve_region(self, region: Safe_Str__AWS__Region = None) -> Safe_Str__AWS__Region:
        if region:                                                                  # Explicit argument wins
            return region
        try:
            from_config = AWS_Config().aws_session_region_name()
            if from_config:
                return Safe_Str__AWS__Region(from_config)
        except Exception:
            pass
        return Safe_Str__AWS__Region(DEFAULT_REGION)
