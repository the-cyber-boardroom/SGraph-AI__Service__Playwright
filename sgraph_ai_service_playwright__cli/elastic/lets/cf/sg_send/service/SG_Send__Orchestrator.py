# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — SG_Send__Orchestrator
# Daily-refresh coordinator for the SGraph-Send CloudFront bucket.
# Runs inventory load → events load (from_inventory=True) in sequence while
# sharing ONE Call__Counter across all collaborators.  Returns a single
# Schema__SG_Send__Sync__Response covering both pipeline phases.
#
# Construction: use the build_sg_send_orchestrator() factory in elastic_lets.py
# which injects a shared Call__Counter into every collaborator so the final
# tallies span the whole run.
#
# Rules (per the three-tier design):
#   • Pure logic — no boto3, no requests, no Console, no typer
#   • Injected collaborators — tests pass in *__In_Memory variants
#   • Idempotent — re-running sync for the same date is safe
# ═══════════════════════════════════════════════════════════════════════════════

from datetime                                                                       import datetime, timezone

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe

from sgraph_ai_service_playwright__cli.elastic.lets.Call__Counter                  import Call__Counter
from sgraph_ai_service_playwright__cli.elastic.lets.cf.events.service.Events__Loader          import Events__Loader
from sgraph_ai_service_playwright__cli.elastic.lets.cf.events.service.Progress__Reporter      import Progress__Reporter
from sgraph_ai_service_playwright__cli.elastic.lets.cf.inventory.primitives.Safe_Str__Pipeline__Run__Id import Safe_Str__Pipeline__Run__Id
from sgraph_ai_service_playwright__cli.elastic.lets.cf.inventory.primitives.Safe_Str__S3__Bucket        import Safe_Str__S3__Bucket
from sgraph_ai_service_playwright__cli.elastic.lets.cf.inventory.primitives.Safe_Str__S3__Key__Prefix   import Safe_Str__S3__Key__Prefix
from sgraph_ai_service_playwright__cli.elastic.lets.cf.inventory.schemas.Schema__Inventory__Load__Request import Schema__Inventory__Load__Request
from sgraph_ai_service_playwright__cli.elastic.lets.cf.inventory.service.Inventory__Loader   import Inventory__Loader
from sgraph_ai_service_playwright__cli.elastic.lets.cf.events.schemas.Schema__Events__Load__Request import Schema__Events__Load__Request
from sgraph_ai_service_playwright__cli.elastic.primitives.Safe_Str__Elastic__Stack__Name    import Safe_Str__Elastic__Stack__Name
from sgraph_ai_service_playwright__cli.observability.primitives.Safe_Str__AWS__Region       import Safe_Str__AWS__Region

from sgraph_ai_service_playwright__cli.elastic.lets.cf.sg_send.schemas.Schema__SG_Send__Sync__Request  import Schema__SG_Send__Sync__Request
from sgraph_ai_service_playwright__cli.elastic.lets.cf.sg_send.schemas.Schema__SG_Send__Sync__Response import Schema__SG_Send__Sync__Response

DEFAULT_BUCKET = '745506449035--sgraph-send-cf-logs--eu-west-2'


def _today_utc_iso() -> str:                                                        # "YYYY-MM-DD" UTC
    return datetime.now(timezone.utc).strftime('%Y-%m-%d')


def _prefix_for_date_iso(date_iso: str) -> str:                                    # "YYYY-MM-DD" → "cloudfront-realtime/YYYY/MM/DD/"
    parts = date_iso.split('-')                                                     # ["YYYY", "MM", "DD"]
    if len(parts) != 3:
        return ''
    return f'cloudfront-realtime/{parts[0]}/{parts[1]}/{parts[2]}/'


class SG_Send__Orchestrator(Type_Safe):
    counter           : Call__Counter
    inventory_loader  : Inventory__Loader
    events_loader     : Events__Loader
    progress_reporter : Progress__Reporter

    def sync(self,
             request  : Schema__SG_Send__Sync__Request,
             base_url : str,
             username : str,
             password : str
             ) -> Schema__SG_Send__Sync__Response:

        import time as _time
        t0 = _time.time()

        # ─── resolve date and prefix ─────────────────────────────────────────
        sync_date = str(request.sync_date) or _today_utc_iso()
        prefix    = _prefix_for_date_iso(sync_date)
        bucket    = str(request.bucket) or DEFAULT_BUCKET
        region    = str(request.region)
        stack     = str(request.stack_name)

        # ─── phase 1: inventory load ─────────────────────────────────────────
        inv_request = Schema__Inventory__Load__Request(
            bucket     = Safe_Str__S3__Bucket(bucket)                              ,
            prefix     = Safe_Str__S3__Key__Prefix(prefix)                         ,
            stack_name = Safe_Str__Elastic__Stack__Name(stack)                     ,
            region     = Safe_Str__AWS__Region(region)                             ,
            run_id     = Safe_Str__Pipeline__Run__Id('')                           ,
            dry_run    = request.dry_run                                           )

        inventory_response = self.inventory_loader.load(request  = inv_request ,
                                                         base_url = base_url    ,
                                                         username = username    ,
                                                         password = password    )

        # ─── phase 2: events load (from_inventory=True) ──────────────────────
        events_request = Schema__Events__Load__Request(
            bucket         = Safe_Str__S3__Bucket(bucket)                          ,
            prefix         = Safe_Str__S3__Key__Prefix(prefix)                     ,
            stack_name     = Safe_Str__Elastic__Stack__Name(stack)                 ,
            region         = Safe_Str__AWS__Region(region)                         ,
            run_id         = Safe_Str__Pipeline__Run__Id('')                       ,
            from_inventory = True                                                   ,
            skip_processed = False                                                  ,
            max_files      = int(request.max_files)                                ,
            dry_run        = request.dry_run                                       )

        events_response = self.events_loader.load(request  = events_request ,
                                                   base_url = base_url      ,
                                                   username = username      ,
                                                   password = password      )

        wall_ms = int((_time.time() - t0) * 1000)

        return Schema__SG_Send__Sync__Response(
            sync_date           = sync_date                    ,
            inventory_response  = inventory_response           ,
            events_response     = events_response             ,
            s3_calls_total      = self.counter.s3_calls       ,
            elastic_calls_total = self.counter.elastic_calls   ,
            wall_ms             = wall_ms                      ,
            dry_run             = request.dry_run             )
