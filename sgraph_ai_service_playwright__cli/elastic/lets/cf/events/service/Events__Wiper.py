# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Events__Wiper
# Matched pair to Events__Loader.  Drops every artifact the events pipeline
# creates AND resets slice 1's manifest so events load --from-inventory finds
# the full queue again.
#
# Order of operations (each step idempotent):
#   1. Delete every sg-cf-events-* index
#   2. Delete the Kibana data view "sg-cf-events-*"
#   3. Delete the dashboard + its visualisation saved-objects (deterministic
#      ids from CF__Events__Dashboard__Ids — Phase 6 will populate them; this
#      wiper is forward-compat)
#   4. Reset the inventory manifest — _update_by_query flips every
#      content_processed=true back to false so the next events load
#      --from-inventory finds the full queue again
#
# Wipe-twice idempotency: a second wipe returns all-zeros.
# ═══════════════════════════════════════════════════════════════════════════════

from datetime                                                                       import datetime, timezone

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe
from osbot_utils.type_safe.type_safe_core.decorators.type_safe                      import type_safe

from sgraph_ai_service_playwright__cli.elastic.primitives.Safe_Str__Elastic__Stack__Name import Safe_Str__Elastic__Stack__Name
from sgraph_ai_service_playwright__cli.elastic.service.Kibana__Saved_Objects__Client     import Kibana__Saved_Objects__Client

from sgraph_ai_service_playwright__cli.elastic.lets.cf.inventory.service.Inventory__HTTP__Client import Inventory__HTTP__Client

from sgraph_ai_service_playwright__cli.elastic.lets.cf.events.schemas.Schema__Events__Wipe__Response import Schema__Events__Wipe__Response
from sgraph_ai_service_playwright__cli.elastic.lets.cf.events.service.CF__Events__Dashboard__Ids   import all_events_dashboard_refs
from sgraph_ai_service_playwright__cli.elastic.lets.cf.events.service.Inventory__Manifest__Updater import Inventory__Manifest__Updater


INDEX__PATTERN          = 'sg-cf-events-*'                                          # Matches every daily events index
DATA_VIEW__TITLE        = 'sg-cf-events-*'                                          # Wildcard data view


class Events__Wiper(Type_Safe):
    http_client      : Inventory__HTTP__Client
    kibana_client    : Kibana__Saved_Objects__Client
    manifest_updater : Inventory__Manifest__Updater

    @type_safe
    def wipe(self, base_url   : str ,
                   username   : str ,
                   password   : str ,
                   stack_name : Safe_Str__Elastic__Stack__Name = ''
              ) -> Schema__Events__Wipe__Response:
        started_at    = datetime.now(timezone.utc)
        error_message = ''

        # ─── 1. Delete events indices ────────────────────────────────────────
        indices_dropped, _, idx_err = self.http_client.delete_indices_by_pattern(
            base_url = base_url        ,
            username = username        ,
            password = password        ,
            pattern  = INDEX__PATTERN  )
        if idx_err and not error_message:
            error_message = idx_err

        # ─── 2. Delete the events data view ──────────────────────────────────
        existed, _, dv_err = self.kibana_client.delete_data_view_by_title(
            base_url = base_url           ,
            username = username           ,
            password = password           ,
            title    = DATA_VIEW__TITLE   )
        data_views_dropped = 1 if existed else 0
        if dv_err and not error_message:
            error_message = dv_err

        # ─── 3. Delete dashboard saved-objects (Phase 6 will populate them) ──
        saved_objects_dropped = self.kibana_client.delete_saved_objects(
            base_url = base_url                  ,
            username = username                  ,
            password = password                  ,
            objects  = all_events_dashboard_refs())

        # ─── 4. Reset inventory manifest content_processed=true → false ──────
        inventory_reset_count, _, reset_err = self.manifest_updater.reset_all_processed(
            base_url = base_url ,
            username = username ,
            password = password )
        if reset_err and not error_message:
            error_message = reset_err

        finished_at = datetime.now(timezone.utc)
        duration_ms = int((finished_at - started_at).total_seconds() * 1000)

        return Schema__Events__Wipe__Response(stack_name             = stack_name                 ,
                                                indices_dropped        = indices_dropped            ,
                                                data_views_dropped     = data_views_dropped         ,
                                                saved_objects_dropped  = int(saved_objects_dropped) ,
                                                inventory_reset_count  = inventory_reset_count      ,
                                                duration_ms            = duration_ms                ,
                                                error_message          = error_message              )
