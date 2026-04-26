# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Inventory__Loader
# Orchestrator for `sp el lets cf inventory load`. Pure logic; no boto3, no
# requests, no Typer. Composition takes injected service classes — tests
# pass in the *__In_Memory variants for full no-mocks coverage.
#
# load() steps:
#   1. Resolve run_id (auto-generate if empty)
#   2. Resolve prefix  (default: "cloudfront-realtime/{today UTC}/")
#   3. Stamp loaded_at = now()
#   4. List S3 via S3__Inventory__Lister.paginate(...)
#   5. For each S3 object: parse filename, normalise etag, build Schema__S3__Object__Record
#   6. If dry_run, skip steps 7-8 and return summary
#   7. Ensure Kibana data view "sg-cf-inventory" exists (idempotent)
#   8. Bulk-post via Inventory__HTTP__Client.bulk_post_with_id(...)
#   9. Return Schema__Inventory__Load__Response with all metrics
#
# The Elastic index name is "sg-cf-inventory-{YYYY-MM-DD}" derived from the
# loaded_at date — daily rolling. Multi-day loads stay valid because the
# data view is the wider "sg-cf-inventory-*" pattern.
# ═══════════════════════════════════════════════════════════════════════════════

from datetime                                                                       import datetime, timezone

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe
from osbot_utils.type_safe.type_safe_core.decorators.type_safe                      import type_safe

from sgraph_ai_service_playwright__cli.elastic.service.Kibana__Saved_Objects__Client import Kibana__Saved_Objects__Client

from sgraph_ai_service_playwright__cli.elastic.lets.cf.inventory.collections.List__Schema__S3__Object__Record import List__Schema__S3__Object__Record
from sgraph_ai_service_playwright__cli.elastic.lets.cf.inventory.enums.Enum__LETS__Source__Slug   import Enum__LETS__Source__Slug
from sgraph_ai_service_playwright__cli.elastic.lets.cf.inventory.enums.Enum__S3__Storage_Class    import Enum__S3__Storage_Class
from sgraph_ai_service_playwright__cli.elastic.lets.cf.inventory.schemas.Schema__Inventory__Load__Request   import Schema__Inventory__Load__Request
from sgraph_ai_service_playwright__cli.elastic.lets.cf.inventory.schemas.Schema__Inventory__Load__Response  import Schema__Inventory__Load__Response
from sgraph_ai_service_playwright__cli.elastic.lets.cf.inventory.schemas.Schema__S3__Object__Record         import Schema__S3__Object__Record
from sgraph_ai_service_playwright__cli.elastic.lets.cf.inventory.service.Inventory__HTTP__Client import Inventory__HTTP__Client
from sgraph_ai_service_playwright__cli.elastic.lets.cf.inventory.service.Run__Id__Generator      import Run__Id__Generator
from sgraph_ai_service_playwright__cli.elastic.lets.cf.inventory.service.S3__Inventory__Lister   import S3__Inventory__Lister, normalise_etag, parse_firehose_filename


DEFAULT_BUCKET             = '745506449035--sgraph-send-cf-logs--eu-west-2'         # The CloudFront-realtime delivery bucket; CLI flag overrides
DEFAULT_PREFIX_ROOT        = 'cloudfront-realtime'                                  # Path prefix Firehose writes under
DATA_VIEW__TITLE           = 'sg-cf-inventory'                                      # Kibana data view (and pattern *)
DATA_VIEW__TIME_FIELD      = 'delivery_at'                                          # Time field for Discover histograms / dashboards
INDEX__PREFIX              = 'sg-cf-inventory'                                      # ES index prefix; daily indices = "sg-cf-inventory-{YYYY-MM-DD}"


def today_utc_iso() -> str:                                                         # "YYYY-MM-DD" UTC; used in default prefix and index suffix
    return datetime.now(timezone.utc).strftime('%Y-%m-%d')


def now_utc_iso_full() -> str:                                                      # "YYYY-MM-DDTHH:MM:SSZ" — Elastic-friendly
    return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def default_prefix_for_today() -> str:                                              # "cloudfront-realtime/2026/04/25/"
    today = datetime.now(timezone.utc)
    return f'{DEFAULT_PREFIX_ROOT}/{today.year:04d}/{today.month:02d}/{today.day:02d}/'


def index_name_for_date(date_iso: str) -> str:                                      # "sg-cf-inventory-{YYYY-MM-DD}"
    return f'{INDEX__PREFIX}-{date_iso}'


def kibana_url_from_base(base_url: str) -> str:                                     # https://1.2.3.4/ → https://1.2.3.4/app/dashboards
    return base_url.rstrip('/') + '/app/dashboards'


def storage_class_from_string(raw: str) -> Enum__S3__Storage_Class:                 # Defensive — unknown values map to UNKNOWN rather than blowing up
    if not raw:
        return Enum__S3__Storage_Class.UNKNOWN
    try:
        return Enum__S3__Storage_Class(raw)
    except ValueError:
        return Enum__S3__Storage_Class.UNKNOWN


def build_record(s3_obj   : dict ,                                                  # The dict shape ListObjectsV2 returns per object
                  bucket   : str  ,
                  source   : Enum__LETS__Source__Slug,
                  run_id   : str  ,
                  loaded_at: str
              ) -> Schema__S3__Object__Record:
    key        = str(s3_obj.get('Key', ''))
    parsed     = parse_firehose_filename(key)
    last_mod   = s3_obj.get('LastModified', None)
    last_iso   = ''
    if last_mod is not None:
        if hasattr(last_mod, 'astimezone'):                                         # boto3 returns timezone-aware datetimes
            last_iso = last_mod.astimezone(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
        else:
            last_iso = str(last_mod)

    firehose_lag_ms = 0
    if parsed['parsed'] and last_mod is not None and hasattr(last_mod, 'astimezone'):
        delivery_dt = datetime(parsed['year'], parsed['month'], parsed['day'],
                                parsed['hour'], parsed['minute'], parsed['second'],
                                tzinfo=timezone.utc)
        last_dt     = last_mod.astimezone(timezone.utc)
        firehose_lag_ms = int((last_dt - delivery_dt).total_seconds() * 1000)

    return Schema__S3__Object__Record(bucket          = bucket                                              ,
                                       key             = key                                                 ,
                                       last_modified   = last_iso                                            ,
                                       size_bytes      = int(s3_obj.get('Size', 0))                          ,
                                       etag            = normalise_etag(str(s3_obj.get('ETag', '')))         ,
                                       storage_class   = storage_class_from_string(str(s3_obj.get('StorageClass', ''))),
                                       source          = source                                              ,
                                       delivery_year   = parsed['year']                                       ,
                                       delivery_month  = parsed['month']                                      ,
                                       delivery_day    = parsed['day']                                        ,
                                       delivery_hour   = parsed['hour']                                       ,
                                       delivery_minute = parsed['minute']                                     ,
                                       delivery_at     = parsed['iso']                                        ,
                                       firehose_lag_ms = firehose_lag_ms                                      ,
                                       pipeline_run_id = run_id                                              ,
                                       loaded_at       = loaded_at                                           )


class Inventory__Loader(Type_Safe):
    s3_lister     : S3__Inventory__Lister
    http_client   : Inventory__HTTP__Client
    kibana_client : Kibana__Saved_Objects__Client
    run_id_gen    : Run__Id__Generator

    @type_safe
    def load(self, request  : Schema__Inventory__Load__Request,
                   base_url : str ,                                                 # Stack base URL e.g. "https://1.2.3.4"
                   username : str ,
                   password : str
              ) -> Schema__Inventory__Load__Response:
        started_at = now_utc_iso_full()

        # ─── resolve inputs ───────────────────────────────────────────────────
        run_id     = str(request.run_id) or self.run_id_gen.generate(source = str(Enum__LETS__Source__Slug.CF_REALTIME),
                                                                      verb   = 'load')
        bucket     = str(request.bucket) or DEFAULT_BUCKET
        if request.prefix:
            prefix = str(request.prefix)
        elif request.all:
            prefix = ''
        else:
            prefix = default_prefix_for_today()
        loaded_at  = now_utc_iso_full()

        # ─── list S3 ──────────────────────────────────────────────────────────
        s3_objects, pages_listed = self.s3_lister.paginate(bucket   = bucket                 ,
                                                            prefix   = prefix                 ,
                                                            max_keys = int(request.max_keys)  ,
                                                            region   = str(request.region)    )    # Empty → boto3 falls through to AWS_DEFAULT_REGION; non-empty wins
        bytes_total = sum(int(obj.get('Size', 0)) for obj in s3_objects)

        # ─── parse → records (in memory; no disk write) ───────────────────────
        records = List__Schema__S3__Object__Record()
        for obj in s3_objects:
            records.append(build_record(s3_obj    = obj                              ,
                                          bucket    = bucket                          ,
                                          source    = Enum__LETS__Source__Slug.CF_REALTIME,
                                          run_id    = run_id                          ,
                                          loaded_at = loaded_at                       ))

        # ─── early return on dry-run ─────────────────────────────────────────
        if request.dry_run:
            finished_at = now_utc_iso_full()
            return Schema__Inventory__Load__Response(run_id           = run_id              ,
                                                      stack_name       = request.stack_name  ,
                                                      bucket           = bucket              ,
                                                      prefix_resolved  = prefix              ,
                                                      pages_listed     = pages_listed        ,
                                                      objects_scanned  = len(s3_objects)     ,
                                                      objects_indexed  = 0                   ,
                                                      objects_updated  = 0                   ,
                                                      bytes_total      = bytes_total         ,
                                                      started_at       = started_at          ,
                                                      finished_at      = finished_at         ,
                                                      duration_ms      = 0                   ,
                                                      last_http_status = 0                   ,
                                                      kibana_url       = kibana_url_from_base(base_url),
                                                      dry_run          = True                )

        # ─── ensure Kibana data view (idempotent) ────────────────────────────
        self.kibana_client.ensure_data_view(base_url        = base_url              ,
                                             username        = username              ,
                                             password        = password              ,
                                             title           = DATA_VIEW__TITLE      ,
                                             time_field_name = DATA_VIEW__TIME_FIELD )

        # ─── bulk-post (etag-as-_id) ─────────────────────────────────────────
        index_name                                              = index_name_for_date(today_utc_iso())
        created, updated, failed, http_status, error_message    = self.http_client.bulk_post_with_id(
            base_url = base_url                ,
            username = username                ,
            password = password                ,
            index    = index_name              ,
            docs     = records                 ,
            id_field = 'etag'                  )

        finished_at = now_utc_iso_full()
        return Schema__Inventory__Load__Response(run_id           = run_id                          ,
                                                  stack_name       = request.stack_name              ,
                                                  bucket           = bucket                          ,
                                                  prefix_resolved  = prefix                          ,
                                                  pages_listed     = pages_listed                    ,
                                                  objects_scanned  = len(s3_objects)                 ,
                                                  objects_indexed  = created                         ,
                                                  objects_updated  = updated                         ,
                                                  bytes_total      = bytes_total                     ,
                                                  started_at       = started_at                      ,
                                                  finished_at      = finished_at                     ,
                                                  duration_ms      = 0                               ,   # Wall-clock duration is computed by the CLI layer
                                                  last_http_status = http_status                     ,
                                                  error_message    = error_message                   ,
                                                  kibana_url       = kibana_url_from_base(base_url)  ,
                                                  dry_run          = False                           )
