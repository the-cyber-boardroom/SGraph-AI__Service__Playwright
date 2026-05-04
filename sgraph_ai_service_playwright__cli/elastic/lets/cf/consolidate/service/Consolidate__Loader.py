# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Consolidate__Loader
# Orchestrator for `sp el lets cf consolidate load`.  Pure logic; no boto3,
# no requests, no Typer.  All collaborators injected — tests use *__In_Memory.
#
# load() steps:
#   1. Resolve run_id (auto-generate if empty), date_iso (today if empty)
#   2. Build work queue (from-inventory default, or s3-listing)
#   3. Dry_run: return early with files_queued populated
#   4. Read or create lets-config.json at compat-region root
#   5. Accumulation loop: fetch .gz → gunzip → parse → accumulate all records
#   6. Write events.ndjson.gz via NDJSON__Writer + S3__Object__Writer
#   7. Build + write manifest.json via Manifest__Builder + S3__Object__Writer
#   8. Index manifest doc into sg-cf-consolidated-{date} (refresh=False — E-1)
#   9. Batch-flip consolidation_run_id on all source inventory docs (E-6)
#  10. Record Schema__Pipeline__Run via Pipeline__Runs__Tracker
# ═══════════════════════════════════════════════════════════════════════════════

import base64
import json
from datetime                                                                       import datetime, timezone

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe
from osbot_utils.type_safe.type_safe_core.decorators.type_safe                      import type_safe

from sgraph_ai_service_playwright__cli.elastic.lets.cf.inventory.enums.Enum__LETS__Source__Slug   import Enum__LETS__Source__Slug
from sgraph_ai_service_playwright__cli.elastic.lets.cf.inventory.service.Inventory__HTTP__Client  import Inventory__HTTP__Client
from sgraph_ai_service_playwright__cli.elastic.lets.cf.inventory.service.Run__Id__Generator       import Run__Id__Generator
from sgraph_ai_service_playwright__cli.elastic.lets.cf.inventory.service.S3__Inventory__Lister    import S3__Inventory__Lister, normalise_etag
from sgraph_ai_service_playwright__cli.elastic.lets.cf.events.collections.List__Schema__CF__Event__Record import List__Schema__CF__Event__Record
from sgraph_ai_service_playwright__cli.elastic.lets.cf.events.service.CF__Realtime__Log__Parser    import CF__Realtime__Log__Parser, gunzip
from sgraph_ai_service_playwright__cli.elastic.lets.cf.events.service.S3__Object__Fetcher          import S3__Object__Fetcher
from sgraph_ai_service_playwright__cli.elastic.lets.cf.consolidate.enums.Enum__Lets__Workflow__Type import Enum__Lets__Workflow__Type
from sgraph_ai_service_playwright__cli.elastic.lets.cf.consolidate.schemas.Schema__Consolidate__Load__Request  import Schema__Consolidate__Load__Request, DEFAULT_COMPAT_REGION
from sgraph_ai_service_playwright__cli.elastic.lets.cf.consolidate.schemas.Schema__Consolidate__Load__Response import Schema__Consolidate__Load__Response
from sgraph_ai_service_playwright__cli.elastic.lets.cf.consolidate.schemas.Schema__Lets__Config    import Schema__Lets__Config
from sgraph_ai_service_playwright__cli.elastic.lets.cf.consolidate.service.Lets__Config__Reader    import Lets__Config__Reader
from sgraph_ai_service_playwright__cli.elastic.lets.cf.consolidate.service.Lets__Config__Writer    import Lets__Config__Writer
from sgraph_ai_service_playwright__cli.elastic.lets.cf.consolidate.service.Manifest__Builder       import Manifest__Builder
from sgraph_ai_service_playwright__cli.elastic.lets.cf.consolidate.service.NDJSON__Writer          import NDJSON__Writer
from sgraph_ai_service_playwright__cli.elastic.lets.cf.consolidate.service.S3__Object__Writer      import S3__Object__Writer
from sgraph_ai_service_playwright__cli.elastic.lets.runs.collections.List__Schema__Pipeline__Run   import List__Schema__Pipeline__Run
from sgraph_ai_service_playwright__cli.elastic.lets.runs.enums.Enum__Pipeline__Verb                import Enum__Pipeline__Verb
from sgraph_ai_service_playwright__cli.elastic.lets.runs.schemas.Schema__Pipeline__Run             import Schema__Pipeline__Run
from sgraph_ai_service_playwright__cli.elastic.lets.runs.service.Pipeline__Runs__Tracker           import Pipeline__Runs__Tracker


DEFAULT_BUCKET             = '745506449035--sgraph-send-cf-logs--eu-west-2'
DEFAULT_CF_PREFIX_ROOT     = 'cloudfront-realtime'
INVENTORY_INDEX_PATTERN    = 'sg-cf-inventory-*'
CONSOLIDATED_INDEX_PREFIX  = 'sg-cf-consolidated'

PAINLESS_MARK_CONSOLIDATED = ('ctx._source.consolidation_run_id = params.run_id; '
                               'ctx._source.consolidated_at = params.consolidated_at;')

# Version stamps written into lets-config.json — bump when parser/schema breaks compat
_PARSER_VERSION         = '1.0.0'
_BOT_CLASSIFIER_VERSION = '1.0.0'
_CONSOLIDATOR_VERSION   = '0.1.100'


def now_utc_iso() -> str:
    return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def today_utc_date() -> str:
    return datetime.now(timezone.utc).strftime('%Y-%m-%d')


def s3_key_for_events(compat_region: str, date_iso: str) -> str:
    y, m, d = date_iso[:4], date_iso[5:7], date_iso[8:10]
    return f'lets/{compat_region}/{y}/{m}/{d}/events.ndjson.gz'


def s3_key_for_manifest(compat_region: str, date_iso: str) -> str:
    y, m, d = date_iso[:4], date_iso[5:7], date_iso[8:10]
    return f'lets/{compat_region}/{y}/{m}/{d}/manifest.json'


def s3_key_for_config(compat_region: str) -> str:
    return f'lets/{compat_region}/lets-config.json'


def cf_prefix_for_date(date_iso: str) -> str:
    y, m, d = date_iso[:4], date_iso[5:7], date_iso[8:10]
    return f'{DEFAULT_CF_PREFIX_ROOT}/{y}/{m}/{d}/'


def consolidated_index_for_date(date_iso: str) -> str:
    return f'{CONSOLIDATED_INDEX_PREFIX}-{date_iso}'


class Consolidate__Loader(Type_Safe):
    s3_fetcher       : S3__Object__Fetcher
    s3_writer        : S3__Object__Writer
    s3_lister        : S3__Inventory__Lister
    parser           : CF__Realtime__Log__Parser
    http_client      : Inventory__HTTP__Client
    ndjson_writer    : NDJSON__Writer
    manifest_builder : Manifest__Builder
    config_reader    : Lets__Config__Reader
    config_writer    : Lets__Config__Writer
    run_id_gen       : Run__Id__Generator
    runs_tracker     : Pipeline__Runs__Tracker

    @type_safe
    def load(self, request  : Schema__Consolidate__Load__Request ,
                   base_url : str                                  ,
                   username : str                                  ,
                   password : str
              ) -> Schema__Consolidate__Load__Response:
        started_at = now_utc_iso()

        run_id       = str(request.run_id)   or self.run_id_gen.generate(source='cf-realtime', verb='consolidate-load')
        date_iso     = str(request.date_iso) or today_utc_date()
        bucket       = str(request.bucket)  or DEFAULT_BUCKET
        compat_region = str(request.compat_region) or DEFAULT_COMPAT_REGION

        # ─── build work queue ─────────────────────────────────────────────────
        work_items, queue_mode, queue_error = self._build_queue(
            request=request, bucket=bucket, date_iso=date_iso,
            base_url=base_url, username=username, password=password)
        if queue_error:
            return self._error_response(run_id=run_id, request=request, bucket=bucket,
                                         date_iso=date_iso, compat_region=compat_region,
                                         queue_mode=queue_mode, started_at=started_at,
                                         error_message=queue_error)

        files_queued = len(work_items)
        bytes_total  = sum(int(item.get('size_bytes', 0)) for item in work_items)

        if request.dry_run:
            finished_at = now_utc_iso()
            return Schema__Consolidate__Load__Response(
                run_id              = run_id              ,
                stack_name          = request.stack_name  ,
                date_iso            = date_iso            ,
                bucket              = bucket              ,
                compat_region       = compat_region       ,
                queue_mode          = queue_mode          ,
                files_queued        = files_queued        ,
                files_processed     = 0                   ,
                files_skipped       = files_queued        ,
                events_consolidated = 0                   ,
                bytes_total         = bytes_total         ,
                bytes_written       = 0                   ,
                inventory_updated   = 0                   ,
                started_at          = started_at          ,
                finished_at         = finished_at         ,
                dry_run             = True                )

        # ─── read or create lets-config.json ──────────────────────────────────
        config_key   = s3_key_for_config(compat_region)
        config, config_err = self._read_or_create_config(
            bucket=bucket, config_key=config_key, compat_region=compat_region,
            run_id=run_id, region=str(request.region),
            base_url=base_url, username=username, password=password)
        if config_err:
            return self._error_response(run_id=run_id, request=request, bucket=bucket,
                                         date_iso=date_iso, compat_region=compat_region,
                                         queue_mode=queue_mode, started_at=started_at,
                                         error_message=config_err)

        # ─── accumulation loop ────────────────────────────────────────────────
        all_records      = List__Schema__CF__Event__Record()
        source_etags     = []
        files_processed  = 0
        files_skipped    = 0
        first_error      = ''
        consolidated_at  = now_utc_iso()

        for item in work_items:
            item_bucket = str(item.get('bucket', '')) or bucket
            item_key    = str(item.get('key',    ''))
            item_etag   = str(item.get('etag',   ''))
            if not item_key:
                files_skipped += 1
                continue
            try:
                gz_bytes = self.s3_fetcher.get_object_bytes(bucket=item_bucket, key=item_key,
                                                             region=str(request.region))
                tsv_text = gunzip(gz_bytes)
            except Exception as exc:
                files_skipped += 1
                if not first_error:
                    first_error = f'fetch error on {item_key}: {str(exc)[:200]}'
                continue

            records, _ = self.parser.parse(tsv_text)
            for rec in records:
                rec.source_bucket   = item_bucket
                rec.source_key      = item_key
                rec.source_etag     = item_etag
                rec.pipeline_run_id = run_id
                rec.loaded_at       = consolidated_at
                rec.doc_id          = f'{item_etag}__{rec.line_index}'
            all_records.extend(records)
            if item_etag:
                source_etags.append(item_etag)
            files_processed += 1

        # ─── write events.ndjson.gz ───────────────────────────────────────────
        events_key    = s3_key_for_events(compat_region, date_iso)
        ndjson_bytes  = self.ndjson_writer.records_to_bytes(all_records)
        _, _, write_err = self.s3_writer.put_object_bytes(bucket=bucket, key=events_key,
                                                           body=ndjson_bytes, region=str(request.region))
        if write_err and not first_error:
            first_error = write_err
        bytes_written = len(ndjson_bytes)

        # ─── write manifest.json ──────────────────────────────────────────────
        finished_at   = now_utc_iso()
        manifest      = self.manifest_builder.build(
            run_id                 = run_id                  ,
            date_iso               = date_iso                ,
            source_count           = files_processed         ,
            event_count            = len(all_records)        ,
            bucket                 = bucket                  ,
            s3_output_key          = events_key              ,
            bytes_written          = bytes_written           ,
            parser_version         = _PARSER_VERSION         ,
            bot_classifier_version = _BOT_CLASSIFIER_VERSION ,
            compat_region          = compat_region           ,
            started_at             = started_at              ,
            finished_at            = finished_at             ,
            consolidated_at        = consolidated_at         )
        manifest_key  = s3_key_for_manifest(compat_region, date_iso)
        manifest_json = json.dumps(manifest.json(), indent=2, sort_keys=True).encode('utf-8')
        self.s3_writer.put_object_bytes(bucket=bucket, key=manifest_key,
                                         body=manifest_json, region=str(request.region))

        # ─── index manifest doc into sg-cf-consolidated-{date} (E-1: no refresh) ─
        from sgraph_ai_service_playwright__cli.elastic.lets.cf.consolidate.collections.List__Schema__Consolidated__Manifest import List__Schema__Consolidated__Manifest
        manifest_docs = List__Schema__Consolidated__Manifest()
        manifest_docs.append(manifest)
        last_status = 0
        _, _, _, http_status, es_err = self.http_client.bulk_post_with_id(
            base_url = base_url                              ,
            username = username                              ,
            password = password                              ,
            index    = consolidated_index_for_date(date_iso) ,
            docs     = manifest_docs                         ,
            id_field = 'run_id'                              ,
            refresh  = False                                 )                      # E-1: batch refresh — caller does explicit refresh later if needed
        last_status = http_status
        if es_err and not first_error:
            first_error = es_err

        # ─── batch-flip consolidation_run_id on all source inventory docs (E-6) ─
        inventory_updated = 0
        if source_etags:
            updated, up_status, up_err = self.http_client.update_by_query_terms(
                base_url      = base_url                   ,
                username      = username                   ,
                password      = password                   ,
                index_pattern = INVENTORY_INDEX_PATTERN    ,
                field         = 'etag'                     ,
                values        = source_etags               ,
                script_source = PAINLESS_MARK_CONSOLIDATED ,
                script_params = {'run_id'         : run_id        ,
                                  'consolidated_at': consolidated_at})
            inventory_updated = updated
            last_status       = up_status
            if up_err and not first_error:
                first_error = up_err

        # ─── journal this run ─────────────────────────────────────────────────
        s3_total      = (int(self.s3_lister.counter.s3_calls)
                          + int(self.s3_fetcher.counter.s3_calls)
                          + int(self.s3_writer.counter.s3_calls))
        elastic_total = int(self.http_client.counter.elastic_calls)
        journal = Schema__Pipeline__Run(
            run_id            = run_id                             ,
            source            = Enum__LETS__Source__Slug.CF_REALTIME,
            verb              = Enum__Pipeline__Verb.CONSOLIDATE_LOAD,
            stack_name        = request.stack_name                 ,
            bucket            = request.bucket                     ,
            queue_mode        = queue_mode                         ,
            dry_run           = False                              ,
            files_queued      = files_queued                       ,
            files_processed   = files_processed                    ,
            files_skipped     = files_skipped                      ,
            inventory_updated = inventory_updated                  ,
            bytes_total       = bytes_total                        ,
            s3_calls          = s3_total                           ,
            elastic_calls     = elastic_total                      ,
            started_at        = started_at                         ,
            finished_at       = finished_at                        ,
            last_http_status  = last_status                        ,
            error_message     = first_error                        )
        self.runs_tracker.record_run(base_url=base_url, username=username, password=password, record=journal)

        return Schema__Consolidate__Load__Response(
            run_id              = run_id              ,
            stack_name          = request.stack_name  ,
            date_iso            = date_iso            ,
            bucket              = bucket              ,
            compat_region       = compat_region       ,
            queue_mode          = queue_mode          ,
            files_queued        = files_queued        ,
            files_processed     = files_processed     ,
            files_skipped       = files_skipped       ,
            events_consolidated = len(all_records)    ,
            bytes_total         = bytes_total         ,
            bytes_written       = bytes_written       ,
            inventory_updated   = inventory_updated   ,
            s3_output_key       = events_key          ,
            started_at          = started_at          ,
            finished_at         = finished_at         ,
            last_http_status    = last_status         ,
            error_message       = first_error         )

    def _build_queue(self, request, bucket, date_iso, base_url, username, password):
        if request.from_inventory:
            items, err = self._query_inventory_for_date(
                base_url=base_url, username=username, password=password,
                date_iso=date_iso, max_files=int(request.max_files))
            return items, 'from-inventory', err

        prefix     = cf_prefix_for_date(date_iso)
        s3_objects, _ = self.s3_lister.paginate(bucket=bucket, prefix=prefix,
                                                  max_keys=int(request.max_files),
                                                  region=str(request.region))
        items = [{'bucket'    : bucket,
                   'key'       : str(o.get('Key', '')),
                   'etag'      : normalise_etag(str(o.get('ETag', ''))),
                   'size_bytes': int(o.get('Size', 0) or 0)} for o in s3_objects]
        return items, 's3-listing', ''

    def _query_inventory_for_date(self, base_url, username, password, date_iso, max_files):
        top_n      = max_files if max_files > 0 else 1000
        auth_token = base64.b64encode(f'{username}:{password}'.encode()).decode()
        headers    = {'Content-Type' : 'application/json'  ,
                      'Authorization': f'Basic {auth_token}'}
        body = json.dumps({
            'size'   : top_n,
            'query'  : {'bool': {'must': [
                {'prefix': {'delivery_at': date_iso}},
                {'term'  : {'consolidation_run_id': ''}}]}},
            'sort'   : [{'delivery_at': {'order': 'asc'}}],
            '_source': ['bucket', 'key', 'etag', 'size_bytes'],
        }).encode('utf-8')
        url = base_url.rstrip('/') + f'/_elastic/{INVENTORY_INDEX_PATTERN}/_search'
        try:
            resp = self.http_client.request('POST', url, headers=headers, data=body)
        except Exception as exc:
            return [], f'inventory query error: {str(exc)[:200]}'
        if int(resp.status_code) == 404:
            return [], ''
        if int(resp.status_code) >= 300:
            return [], f'HTTP {resp.status_code}'
        try:
            payload = resp.json() or {}
        except Exception:
            return [], 'response not JSON'
        hits = (payload.get('hits') or {}).get('hits') or []
        items = []
        for h in hits:
            src = h.get('_source') or {}
            items.append({'bucket'    : str(src.get('bucket', '')),
                           'key'       : str(src.get('key', '')),
                           'etag'      : str(src.get('etag', '')),
                           'size_bytes': int(src.get('size_bytes', 0) or 0)})
        return items, ''

    def _read_or_create_config(self, bucket, config_key, compat_region, run_id, region,
                                 base_url, username, password):
        try:
            config_bytes = self.s3_fetcher.get_object_bytes(bucket=bucket, key=config_key, region=region)
            if config_bytes:
                config, err = self.config_reader.from_bytes(config_bytes)
                if err:
                    return Schema__Lets__Config(), f'lets-config.json parse error: {err}'
                current_config = self._make_config(compat_region=compat_region, run_id=run_id)
                compat_err = self.config_reader.check_compat(stored=config, current=current_config)
                if compat_err:
                    return Schema__Lets__Config(), f'compat-region mismatch: {compat_err}'
                return config, ''
        except Exception:
            pass                                                                     # First use — config doesn't exist yet
        new_config     = self._make_config(compat_region=compat_region, run_id=run_id)
        config_bytes   = self.config_writer.to_bytes(new_config)
        _, _, write_err = self.s3_writer.put_object_bytes(bucket=bucket, key=config_key,
                                                           body=config_bytes, region=region)
        if write_err:
            return Schema__Lets__Config(), f'failed to write lets-config.json: {write_err}'
        return new_config, ''

    def _make_config(self, compat_region: str, run_id: str) -> Schema__Lets__Config:
        return Schema__Lets__Config(
            workflow_type          = Enum__Lets__Workflow__Type.CONSOLIDATE ,
            input_type             = 's3'                                    ,
            input_bucket           = DEFAULT_BUCKET                          ,
            input_prefix           = f'{DEFAULT_CF_PREFIX_ROOT}/'           ,
            input_format           = 'cf-realtime-tsv-gz'                   ,
            output_type            = 'ndjson-gz'                             ,
            output_schema          = 'Schema__CF__Event__Record'             ,
            output_schema_version  = 'v1'                                    ,
            output_compression     = 'gzip'                                  ,
            parser                 = 'CF__Realtime__Log__Parser'             ,
            parser_version         = _PARSER_VERSION                         ,
            bot_classifier         = 'Bot__Classifier'                       ,
            bot_classifier_version = _BOT_CLASSIFIER_VERSION                 ,
            consolidator           = 'Consolidate__Loader'                   ,
            consolidator_version   = _CONSOLIDATOR_VERSION                   ,
            created_at             = now_utc_iso()                           ,
            created_by             = f'sp el lets cf consolidate load (run {run_id})',
        )

    def _error_response(self, run_id, request, bucket, date_iso, compat_region,
                          queue_mode, started_at, error_message):
        finished_at = now_utc_iso()
        return Schema__Consolidate__Load__Response(
            run_id        = run_id             ,
            stack_name    = request.stack_name ,
            date_iso      = date_iso           ,
            bucket        = bucket             ,
            compat_region = compat_region      ,
            queue_mode    = queue_mode         ,
            started_at    = started_at         ,
            finished_at   = finished_at        ,
            error_message = error_message      )
