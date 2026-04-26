# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Inventory__Wiper
# Matched pair to Inventory__Loader.  Drops every artifact the load pipeline
# creates, so `load → wipe -y → load` is the first-class developer loop.
#
# Order of operations (each step idempotent):
#   1. Delete every sg-cf-inventory-* index (count = number actually dropped)
#   2. Delete the Kibana data view "sg-cf-inventory-*"
#      Plus the legacy "sg-cf-inventory" title from the pre-fix data view
#      (harmless if absent — delete_data_view_by_title returns False/200)
#   3. Delete the dashboard + its visualisation saved-objects
#      (forward-compat: Phase 5 will populate these; Phase 4 wipes them
#       anyway so the developer loop works whatever phase the user is on)
#
# Wipe-twice idempotency contract: a second wipe returns all-zeros.
# ═══════════════════════════════════════════════════════════════════════════════

from datetime                                                                       import datetime, timezone

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe
from osbot_utils.type_safe.type_safe_core.decorators.type_safe                      import type_safe

from sgraph_ai_service_playwright__cli.elastic.primitives.Safe_Str__Elastic__Stack__Name import Safe_Str__Elastic__Stack__Name
from sgraph_ai_service_playwright__cli.elastic.service.Kibana__Saved_Objects__Client     import Kibana__Saved_Objects__Client

from sgraph_ai_service_playwright__cli.elastic.lets.cf.inventory.schemas.Schema__Inventory__Wipe__Response import Schema__Inventory__Wipe__Response
from sgraph_ai_service_playwright__cli.elastic.lets.cf.inventory.service.CF__Inventory__Dashboard__Ids   import all_inventory_dashboard_refs
from sgraph_ai_service_playwright__cli.elastic.lets.cf.inventory.service.Inventory__HTTP__Client          import Inventory__HTTP__Client


INDEX__PATTERN              = 'sg-cf-inventory-*'                                   # Matches every daily index
DATA_VIEW__TITLE__CURRENT   = 'sg-cf-inventory-*'                                   # Wildcard data view (current convention)
DATA_VIEW__TITLE__LEGACY    = 'sg-cf-inventory'                                     # Pre-fix non-wildcard data view; deleted defensively


class Inventory__Wiper(Type_Safe):
    http_client   : Inventory__HTTP__Client
    kibana_client : Kibana__Saved_Objects__Client

    @type_safe
    def wipe(self, base_url   : str ,
                   username   : str ,
                   password   : str ,
                   stack_name : Safe_Str__Elastic__Stack__Name = ''
              ) -> Schema__Inventory__Wipe__Response:
        started_at = datetime.now(timezone.utc)
        error_message = ''

        # ─── 1. Delete indices ───────────────────────────────────────────────
        indices_dropped, _, idx_err = self.http_client.delete_indices_by_pattern(
            base_url = base_url            ,
            username = username            ,
            password = password            ,
            pattern  = INDEX__PATTERN      )
        if idx_err and not error_message:
            error_message = idx_err

        # ─── 2. Delete data views (current + legacy) ─────────────────────────
        data_views_dropped = 0
        for title in (DATA_VIEW__TITLE__CURRENT, DATA_VIEW__TITLE__LEGACY):
            existed, _, dv_err = self.kibana_client.delete_data_view_by_title(
                base_url = base_url ,
                username = username ,
                password = password ,
                title    = title    )
            if existed:
                data_views_dropped += 1
            if dv_err and not error_message:
                error_message = dv_err

        # ─── 3. Delete dashboard saved-objects (slice 5 will populate these) ─
        saved_objects_dropped = self.kibana_client.delete_saved_objects(
            base_url = base_url                    ,
            username = username                    ,
            password = password                    ,
            objects  = all_inventory_dashboard_refs())

        finished_at = datetime.now(timezone.utc)
        duration_ms = int((finished_at - started_at).total_seconds() * 1000)

        return Schema__Inventory__Wipe__Response(stack_name            = stack_name           ,
                                                  indices_dropped       = indices_dropped      ,
                                                  data_views_dropped    = data_views_dropped   ,
                                                  saved_objects_dropped = int(saved_objects_dropped),
                                                  duration_ms           = duration_ms          ,
                                                  error_message         = error_message        )
