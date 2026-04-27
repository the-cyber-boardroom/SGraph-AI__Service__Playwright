# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Events__Loader
# Orchestrator for `sp el lets cf events load`.  Pure logic; no boto3, no
# requests, no Typer.  Composition takes injected service classes — tests
# pass in the *__In_Memory variants for full no-mocks coverage.
#
# load() steps:
#   1. Resolve run_id (auto-generate if empty)
#   2. Build the work queue — two modes:
#        a. S3-listing (default)        — list cloudfront-realtime/ via slice 1's
#                                          S3__Inventory__Lister
#        b. from-inventory (--from-inventory) — query sg-cf-inventory-* for
#                                          content_processed=false via
#                                          Inventory__Manifest__Reader
#   3. If dry_run, return early with files_queued populated
#   4. Ensure Kibana data view "sg-cf-events-*" (idempotent)
#   5. For each file in the queue:
#        a. Fetch .gz bytes via S3__Object__Fetcher.get_object_bytes
#        b. gunzip → TSV string
#        c. Parse via CF__Realtime__Log__Parser → records + skipped count
#        d. Stamp source_bucket / source_key / source_etag / pipeline_run_id /
#           loaded_at on each record
#        e. Group records by event timestamp[:10] → per-day daily-rolling
#           index (sg-cf-events-{YYYY-MM-DD})
#        f. Bulk-post to each daily index via Inventory__HTTP__Client
#           (etag+line_index doc id keeps re-loads idempotent)
#        g. After ALL bulk-posts succeed for the file, flip the inventory
#           doc's content_processed=true via Inventory__Manifest__Updater
#   6. Return Schema__Events__Load__Response with aggregate counts
#
# Per-file failure (fetch error, parse error, bulk-post error) is counted
# as files_skipped — the loop continues with the next file.  No retry.
# ═══════════════════════════════════════════════════════════════════════════════

from datetime                                                                       import datetime, timezone

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe
from osbot_utils.type_safe.type_safe_core.decorators.type_safe                      import type_safe

from sgraph_ai_service_playwright__cli.elastic.service.Kibana__Saved_Objects__Client import Kibana__Saved_Objects__Client

# Slice 1 reused:
from sgraph_ai_service_playwright__cli.elastic.lets.cf.inventory.enums.Enum__LETS__Source__Slug   import Enum__LETS__Source__Slug
from sgraph_ai_service_playwright__cli.elastic.lets.cf.inventory.service.Inventory__HTTP__Client import Inventory__HTTP__Client
from sgraph_ai_service_playwright__cli.elastic.lets.cf.inventory.service.Run__Id__Generator    import Run__Id__Generator
from sgraph_ai_service_playwright__cli.elastic.lets.cf.inventory.service.S3__Inventory__Lister  import S3__Inventory__Lister, normalise_etag

# Slice 2:
from sgraph_ai_service_playwright__cli.elastic.lets.cf.events.collections.List__Schema__CF__Event__Record import List__Schema__CF__Event__Record
from sgraph_ai_service_playwright__cli.elastic.lets.cf.events.schemas.Schema__Events__Load__Request   import Schema__Events__Load__Request
from sgraph_ai_service_playwright__cli.elastic.lets.cf.events.schemas.Schema__Events__Load__Response  import Schema__Events__Load__Response
from sgraph_ai_service_playwright__cli.elastic.lets.cf.events.service.CF__Events__Dashboard__Builder import CF__Events__Dashboard__Builder
from sgraph_ai_service_playwright__cli.elastic.lets.cf.events.service.CF__Realtime__Log__Parser     import CF__Realtime__Log__Parser, gunzip
from sgraph_ai_service_playwright__cli.elastic.lets.cf.events.service.Inventory__Manifest__Reader  import Inventory__Manifest__Reader
from sgraph_ai_service_playwright__cli.elastic.lets.cf.events.service.Inventory__Manifest__Updater import Inventory__Manifest__Updater
from sgraph_ai_service_playwright__cli.elastic.lets.cf.events.service.Progress__Reporter            import Progress__Reporter
from sgraph_ai_service_playwright__cli.elastic.lets.cf.events.service.S3__Object__Fetcher          import S3__Object__Fetcher
from sgraph_ai_service_playwright__cli.elastic.lets.Step__Timings                                  import Step__Timings


DEFAULT_BUCKET             = '745506449035--sgraph-send-cf-logs--eu-west-2'
DEFAULT_PREFIX_ROOT        = 'cloudfront-realtime'
DATA_VIEW__TITLE           = 'sg-cf-events-*'                                       # Wildcard pattern, matches every daily events index
DATA_VIEW__TIME_FIELD      = 'timestamp'                                            # The event's own timestamp; not loaded_at
INDEX__PREFIX              = 'sg-cf-events'                                         # Daily index = sg-cf-events-{YYYY-MM-DD}


def now_utc_iso_full() -> str:
    return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def today_utc_iso() -> str:
    return datetime.now(timezone.utc).strftime('%Y-%m-%d')


def default_prefix_for_today() -> str:
    today = datetime.now(timezone.utc)
    return f'{DEFAULT_PREFIX_ROOT}/{today.year:04d}/{today.month:02d}/{today.day:02d}/'


def index_name_for_date(date_iso: str) -> str:
    return f'{INDEX__PREFIX}-{date_iso}'


def kibana_url_from_base(base_url: str) -> str:
    return base_url.rstrip('/') + '/app/dashboards'


class Events__Loader(Type_Safe):
    s3_lister         : S3__Inventory__Lister
    s3_fetcher        : S3__Object__Fetcher
    parser            : CF__Realtime__Log__Parser
    http_client       : Inventory__HTTP__Client
    kibana_client     : Kibana__Saved_Objects__Client
    manifest_reader   : Inventory__Manifest__Reader
    manifest_updater  : Inventory__Manifest__Updater
    run_id_gen        : Run__Id__Generator
    progress_reporter : Progress__Reporter                                          # Default no-op base class — Type_Safe auto-instantiates.  CLI passes a Rich subclass.

    @type_safe
    def load(self, request  : Schema__Events__Load__Request,
                   base_url : str ,
                   username : str ,
                   password : str
              ) -> Schema__Events__Load__Response:
        started_at = now_utc_iso_full()

        # ─── resolve inputs ──────────────────────────────────────────────────
        run_id    = str(request.run_id) or self.run_id_gen.generate(source = str(Enum__LETS__Source__Slug.CF_REALTIME),
                                                                     verb   = 'events-load')
        bucket    = str(request.bucket) or DEFAULT_BUCKET
        loaded_at = now_utc_iso_full()

        # ─── build the work queue (S3-listing OR from-inventory) ─────────────
        work_items, queue_mode, prefix_resolved, queue_error = self.build_queue(
            request  = request  ,
            bucket   = bucket   ,
            base_url = base_url ,
            username = username ,
            password = password )
        if queue_error:
            return self.error_response(run_id=run_id, request=request, bucket=bucket,
                                        prefix_resolved=prefix_resolved, queue_mode=queue_mode,
                                        started_at=started_at, base_url=base_url,
                                        error_message=queue_error)

        # ─── apply --skip-processed filter (queries events index for known etags) ──
        if request.skip_processed and len(work_items) > 0:
            before_count    = len(work_items)
            processed_etags = self.list_processed_etags(base_url=base_url, username=username, password=password)
            work_items      = [w for w in work_items if str(w.get('etag', '')) not in processed_etags]
            self.progress_reporter.on_skip_filter_done(before=before_count, after=len(work_items))

        files_queued = len(work_items)
        bytes_total  = sum(int(item.get('size_bytes', 0)) for item in work_items)
        self.progress_reporter.on_queue_built(files_queued=files_queued, queue_mode=queue_mode)

        # ─── early return on dry_run ─────────────────────────────────────────
        if request.dry_run:
            finished_at = now_utc_iso_full()
            return Schema__Events__Load__Response(run_id            = run_id              ,
                                                   stack_name        = request.stack_name  ,
                                                   bucket            = bucket              ,
                                                   prefix_resolved   = prefix_resolved     ,
                                                   queue_mode        = queue_mode          ,
                                                   files_queued      = files_queued        ,
                                                   files_processed   = 0                   ,
                                                   files_skipped     = files_queued        ,   # All of them, since we're not processing
                                                   events_indexed    = 0                   ,
                                                   events_updated    = 0                   ,
                                                   bytes_total       = bytes_total         ,
                                                   inventory_updated = 0                   ,
                                                   started_at        = started_at          ,
                                                   finished_at       = finished_at         ,
                                                   duration_ms       = 0                   ,
                                                   last_http_status  = 0                   ,
                                                   error_message     = ''                  ,
                                                   kibana_url        = kibana_url_from_base(base_url),
                                                   dry_run           = True                )

        # ─── ensure Kibana data view (idempotent) ────────────────────────────
        data_view_result = self.kibana_client.ensure_data_view(base_url        = base_url              ,
                                                                username        = username              ,
                                                                password        = password              ,
                                                                title           = DATA_VIEW__TITLE      ,
                                                                time_field_name = DATA_VIEW__TIME_FIELD )

        # ─── ensure dashboard (idempotent — overwrite=true) ──────────────────
        # Skip silently if data view ensure failed (no id to bind panels to).
        if str(data_view_result.id) and not str(data_view_result.error):
            ndjson_bytes = CF__Events__Dashboard__Builder().build_ndjson(data_view_id = str(data_view_result.id),
                                                                          time_field   = DATA_VIEW__TIME_FIELD)
            self.kibana_client.import_objects(base_url     = base_url     ,
                                               username     = username     ,
                                               password     = password     ,
                                               ndjson_bytes = ndjson_bytes ,
                                               overwrite    = True         )

        # ─── per-file fetch → parse → bulk-post → manifest update ────────────
        files_processed   = 0
        files_skipped     = 0
        events_indexed    = 0
        events_updated    = 0
        inventory_updated = 0
        last_status       = 0
        first_error       = ''

        import time as _time
        for queue_idx, item in enumerate(work_items, start=1):
            item_bucket = str(item.get('bucket', '')) or bucket
            item_key    = str(item.get('key'   , ''))
            item_etag   = str(item.get('etag'  , ''))
            if not item_key:
                files_skipped += 1
                self.progress_reporter.on_file_error(idx=queue_idx, total=files_queued,
                                                       key='(empty key)', error_msg='no key on queue item')
                continue

            file_t0   = _time.time()
            timings   = Step__Timings()
            try:
                t_get = _time.time()
                gz_bytes = self.s3_fetcher.get_object_bytes(bucket=item_bucket, key=item_key, region=str(request.region))
                timings.s3_get_ms = int((_time.time() - t_get) * 1000)
                t_gz  = _time.time()
                tsv_text = gunzip(gz_bytes)
                timings.gunzip_ms = int((_time.time() - t_gz) * 1000)
            except Exception as exc:
                files_skipped += 1
                if not first_error:
                    # Avoid "/" in the message — Safe_Str__Text sanitises it (slice 1 lesson)
                    first_error = f'fetch error on {item_key}: {str(exc)[:200]}'
                self.progress_reporter.on_file_error(idx=queue_idx, total=files_queued,
                                                       key=item_key, error_msg=str(exc)[:200])
                continue

            t_parse = _time.time()
            records, _ = self.parser.parse(tsv_text)
            timings.parse_ms = int((_time.time() - t_parse) * 1000)
            if len(records) == 0:                                                    # Empty file — count as processed (nothing went wrong) but contribute zero events
                files_processed += 1
                # Still mark inventory as content_processed=true: we DID look at it
                t_mark = _time.time()
                up_count, up_status, up_err = self.manifest_updater.mark_processed(
                    base_url=base_url, username=username, password=password,
                    etag=item_etag, run_id=run_id)
                timings.manifest_update_ms = int((_time.time() - t_mark) * 1000)
                if up_status:
                    last_status = up_status
                inventory_updated += up_count
                if up_err and not first_error:
                    first_error = up_err
                file_ms = int((_time.time() - file_t0) * 1000)
                self.progress_reporter.on_file_done(idx=queue_idx, total=files_queued,
                                                      key=item_key, events_count=0, duration_ms=file_ms,
                                                      timings=timings)
                continue

            # Stamp source-lineage + pipeline metadata + per-line doc_id on each record
            for record in records:
                record.source_bucket   = item_bucket
                record.source_key      = item_key
                record.source_etag     = item_etag
                record.pipeline_run_id = run_id
                record.loaded_at       = loaded_at
                record.doc_id          = f'{item_etag}__{record.line_index}'         # Per-event uniqueness — re-loads of the same .gz overwrite in place

            # Group by event delivery date (the event's own timestamp) for per-day indexing
            buckets_by_date: dict = {}
            for record in records:
                day = str(record.timestamp)[:10] or today_utc_iso()
                if day not in buckets_by_date:
                    buckets_by_date[day] = List__Schema__CF__Event__Record()
                buckets_by_date[day].append(record)

            file_failed = False
            t_post      = _time.time()
            for day, group_records in sorted(buckets_by_date.items()):
                index_name = index_name_for_date(day)
                created, updated, failed, http_status, err = self.http_client.bulk_post_with_id(
                    base_url = base_url       ,
                    username = username       ,
                    password = password       ,
                    index    = index_name     ,
                    docs     = group_records  ,
                    id_field = 'doc_id'       )                                      # _id = "{source_etag}__{line_index}" — set just above
                events_indexed += created
                events_updated += updated
                last_status     = http_status
                if err and not first_error:
                    first_error = err
                if failed > 0 and not file_failed:                                   # Any per-day batch failed → file partially-failed
                    file_failed = True
            timings.bulk_post_ms = int((_time.time() - t_post) * 1000)

            if file_failed:
                files_skipped += 1
                self.progress_reporter.on_file_error(idx=queue_idx, total=files_queued,
                                                       key=item_key, error_msg=first_error[:200])
                continue

            # File processed cleanly — update the manifest
            t_mark = _time.time()
            up_count, up_status, up_err = self.manifest_updater.mark_processed(
                base_url=base_url, username=username, password=password,
                etag=item_etag, run_id=run_id)
            timings.manifest_update_ms = int((_time.time() - t_mark) * 1000)
            if up_status:
                last_status = up_status
            inventory_updated += up_count
            if up_err and not first_error:
                first_error = up_err
            files_processed += 1
            file_ms = int((_time.time() - file_t0) * 1000)
            self.progress_reporter.on_file_done(idx=queue_idx, total=files_queued,
                                                  key=item_key, events_count=len(records),
                                                  duration_ms=file_ms,
                                                  timings=timings)

        self.progress_reporter.on_load_complete()
        finished_at = now_utc_iso_full()
        return Schema__Events__Load__Response(run_id            = run_id              ,
                                               stack_name        = request.stack_name  ,
                                               bucket            = bucket              ,
                                               prefix_resolved   = prefix_resolved     ,
                                               queue_mode        = queue_mode          ,
                                               files_queued      = files_queued        ,
                                               files_processed   = files_processed     ,
                                               files_skipped     = files_skipped       ,
                                               events_indexed    = events_indexed      ,
                                               events_updated    = events_updated      ,
                                               bytes_total       = bytes_total         ,
                                               inventory_updated = inventory_updated   ,
                                               started_at        = started_at          ,
                                               finished_at       = finished_at         ,
                                               duration_ms       = 0                   ,   # Wall-clock filled by CLI layer
                                               last_http_status  = last_status         ,
                                               error_message     = first_error         ,
                                               kibana_url        = kibana_url_from_base(base_url),
                                               dry_run           = False               )

    def list_processed_etags(self, base_url : str ,
                                    username : str ,
                                    password : str
                              ) -> set:                                              # Returns a set of source_etag values currently present in sg-cf-events-*. One ES call.
        # Used by --skip-processed to filter the queue before fetching anything.
        # Cheap: terms agg with size 10000 (covers >100 days of typical sg-send
        # cadence at ~375 files/day).  When the events index is larger than
        # this, the filter degrades gracefully — we'd just re-fetch a few
        # files unnecessarily, which is correct just not optimal.
        import base64, json
        auth_token = base64.b64encode(f'{username}:{password}'.encode()).decode()
        headers    = {'Content-Type' : 'application/json'  ,
                      'Authorization': f'Basic {auth_token}'}
        body = json.dumps({
            'size'    : 0,
            'aggs'    : {'distinct_etags': {'terms': {'field': 'source_etag.keyword', 'size': 10000}}},
        }).encode('utf-8')
        url = base_url.rstrip('/') + '/_elastic/sg-cf-events-*/_search'

        result : set = set()
        try:
            response = self.http_client.request('POST', url, headers=headers, data=body)
        except Exception:
            return result                                                            # No connectivity → empty set means "nothing skipped" (safe — we just fetch normally)
        if int(response.status_code) >= 300:                                        # Index doesn't exist yet, or auth failed — empty set, fetch normally
            return result
        try:
            payload = response.json() or {}
        except Exception:
            return result
        for bucket in payload.get('aggregations', {}).get('distinct_etags', {}).get('buckets', []) or []:
            etag = str(bucket.get('key', ''))
            if etag:
                result.add(etag)
        return result

    def build_queue(self, request, bucket, base_url, username, password):           # Returns (work_items, queue_mode, prefix_resolved, error_message)
        if request.from_inventory:
            top_n = int(request.max_files) if request.max_files > 0 else 1000        # Default to 1000 when no cap supplied
            docs, _, err = self.manifest_reader.list_unprocessed(
                base_url=base_url, username=username, password=password, top_n=top_n)
            return docs, 'from-inventory', '', err

        if request.prefix:
            prefix = str(request.prefix)
        elif request.all:
            prefix = ''
        else:
            prefix = default_prefix_for_today()

        s3_objects, _ = self.s3_lister.paginate(bucket   = bucket               ,
                                                 prefix   = prefix               ,
                                                 max_keys = int(request.max_files),
                                                 region   = str(request.region)   )
        work_items = []
        for obj in s3_objects:
            work_items.append({'bucket'     : bucket                                                 ,
                                'key'        : str(obj.get('Key', ''))                                ,
                                'etag'       : normalise_etag(str(obj.get('ETag', '')))               ,
                                'size_bytes' : int(obj.get('Size', 0) or 0)                           ,
                                'delivery_at': ''                                                     })
        return work_items, 's3-listing', prefix, ''

    def error_response(self, run_id, request, bucket, prefix_resolved, queue_mode,
                        started_at, base_url, error_message):                       # Helper for early-error returns
        finished_at = now_utc_iso_full()
        return Schema__Events__Load__Response(run_id            = run_id              ,
                                               stack_name        = request.stack_name  ,
                                               bucket            = bucket              ,
                                               prefix_resolved   = prefix_resolved     ,
                                               queue_mode        = queue_mode          ,
                                               started_at        = started_at          ,
                                               finished_at       = finished_at         ,
                                               kibana_url        = kibana_url_from_base(base_url),
                                               error_message     = error_message       )
