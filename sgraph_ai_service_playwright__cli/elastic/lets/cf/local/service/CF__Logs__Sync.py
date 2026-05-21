# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — cf local: CF__Logs__Sync
# Syncs raw CF-logs from the Firehose S3 bucket into the local cache. Reuses the LETS
# S3 boundaries verbatim — S3__Inventory__Lister (list a scope) + S3__Object__Fetcher
# (download bytes) — so there is one boto3 path, and tests subclass those seams (no
# mocks). Two modes, both built on plan():
#   plan()             — "list" mode: diff S3 vs local for a date / day+hour
#   download_missing() — "download" mode: fetch only the absent objects
# CF objects are immutable, so a present file is never re-fetched; the only live
# question is whether today's partition is complete, which the plan answers directly.
# Every S3 call and local write is recorded to the injected Debug__Event_Log so the
# Debug Panel shows exactly what ran.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                              import Type_Safe

from sgraph_ai_service_playwright__cli.elastic.lets.cf.events.service.S3__Object__Fetcher import S3__Object__Fetcher
from sgraph_ai_service_playwright__cli.elastic.lets.cf.inventory.service.S3__Inventory__Lister import S3__Inventory__Lister
from sgraph_ai_service_playwright__cli.elastic.lets.cf.local.schemas.Schema__CF__Sync__File   import Schema__CF__Sync__File
from sgraph_ai_service_playwright__cli.elastic.lets.cf.local.schemas.Schema__CF__Sync__Plan   import Schema__CF__Sync__Plan
from sgraph_ai_service_playwright__cli.elastic.lets.cf.local.schemas.Schema__CF__Sync__Result import Schema__CF__Sync__Result
from sgraph_ai_service_playwright__cli.elastic.lets.cf.local.service.CF__Local__Store         import CF__Local__Store
from sgraph_ai_service_playwright__cli.elastic.lets.cf.tui.cf_tui__config          import CF_LOGS_BUCKET, CF_LOGS_PREFIX, CF_LOGS_REGION, cf_realtime_prefix
from sgraph_ai_service_playwright__cli.tui.debug.Debug__Event_Log                  import Debug__Event_Log


def _basename(key : str) -> str:
    return key.rsplit('/', 1)[-1]


class CF__Logs__Sync(Type_Safe):
    bucket  : str = CF_LOGS_BUCKET
    prefix  : str = CF_LOGS_PREFIX
    region  : str = CF_LOGS_REGION
    lister  : S3__Inventory__Lister
    fetcher : S3__Object__Fetcher
    store   : CF__Local__Store
    debug   : Debug__Event_Log

    def scoped_prefix(self, date_iso : str = '', hour : str = '') -> str:
        return cf_realtime_prefix(date_iso, hour, base=self.prefix)

    def plan(self, date_iso : str = '', hour : str = '') -> Schema__CF__Sync__Plan:
        prefix = self.scoped_prefix(date_iso, hour)
        self.debug.record('s3.list', f'list s3://{self.bucket}/{prefix}')
        objects, pages = self.lister.paginate(bucket=self.bucket, prefix=prefix, region=self.region)
        self.debug.record('s3.list', f'{len(objects)} object(s), {pages} page(s)', detail=prefix)
        plan = Schema__CF__Sync__Plan(bucket=self.bucket, prefix=prefix, date_iso=date_iso, hour=hour)
        for obj in objects:
            key = obj.get('Key', '')
            if not key or key.endswith('/'):                                         # skip folder markers
                continue
            size    = int(obj.get('Size', 0))
            present = self.store.has_key(key)
            plan.files.append(Schema__CF__Sync__File(key           = key,
                                                     local_path    = str(self.store.local_path_for_key(key)),
                                                     size          = size,
                                                     last_modified = str(obj.get('LastModified', '')),
                                                     present_local = present))
            if present: plan.present_bytes += size
            else:       plan.missing_bytes += size
        plan.remote_count  = len(plan.files)
        plan.local_count   = sum(1 for f in plan.files if f.present_local)
        plan.missing_count = plan.remote_count - plan.local_count
        self.debug.record('ui', f'plan: {plan.local_count} local / {plan.missing_count} missing of {plan.remote_count}')
        return plan

    def download_missing(self, plan : Schema__CF__Sync__Plan, on_file=None) -> Schema__CF__Sync__Result:
        result = Schema__CF__Sync__Result()
        for f in plan.files:
            if f.present_local:
                result.skipped += 1
                continue
            try:
                self.debug.record('s3.get', f'GET {_basename(f.key)}')
                data = self.fetcher.get_object_bytes(bucket=self.bucket, key=f.key, region=self.region)
                path = self.store.write_key(f.key, data)
                self.debug.record('fs.write', f'wrote {path.name}', detail=f'{len(data)} bytes')
                f.present_local    = True
                result.downloaded += 1
                result.bytes      += len(data)
            except Exception as exc:
                result.failed += 1
                self.debug.error('s3.get', f'failed {_basename(f.key)}', detail=str(exc)[:100])
            if on_file is not None:
                on_file(result, f)
        result.done = True
        self.debug.record('ui', f'sync done — {result.downloaded} downloaded, {result.skipped} present, {result.failed} failed')
        return result
