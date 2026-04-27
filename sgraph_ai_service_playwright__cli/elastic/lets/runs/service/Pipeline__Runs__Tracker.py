# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Pipeline__Runs__Tracker
# The single writer for the LETS journal index `sg-pipeline-runs-{YYYY-MM-DD}`.
# Each loader builds a Schema__Pipeline__Run at the end of load() and hands it
# here.  One bulk-post, one doc, _id = run_id (so re-recording the same run
# overwrites in place — idempotent for retries / replays).
#
# The index date is keyed on `started_at[:10]` (the run's own start day),
# so a long run that crosses midnight UTC still lands in the day it began —
# avoids backfilling stale indices.
#
# Tests subclass and override record_run() to capture the call without
# touching Elastic.  The wired-in Inventory__HTTP__Client__In_Memory works
# unchanged because bulk_post_with_id already handles arbitrary
# Type_Safe__List instances.
# ═══════════════════════════════════════════════════════════════════════════════

from typing                                                                         import Tuple

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe
from osbot_utils.type_safe.type_safe_core.decorators.type_safe                      import type_safe

from sgraph_ai_service_playwright__cli.elastic.lets.cf.inventory.service.Inventory__HTTP__Client import Inventory__HTTP__Client
from sgraph_ai_service_playwright__cli.elastic.lets.runs.collections.List__Schema__Pipeline__Run import List__Schema__Pipeline__Run
from sgraph_ai_service_playwright__cli.elastic.lets.runs.schemas.Schema__Pipeline__Run            import Schema__Pipeline__Run


INDEX__PREFIX = 'sg-pipeline-runs'                                                  # Daily index = sg-pipeline-runs-{YYYY-MM-DD}


def index_name_for_run(record: Schema__Pipeline__Run) -> str:                       # Key on started_at — a midnight-crossing run still lands on the day it began
    started_at = str(record.started_at)
    if len(started_at) >= 10:
        date_iso = started_at[:10]
    else:
        date_iso = '1970-01-01'                                                     # Defensive — empty started_at is a bug, but don't crash
    return f'{INDEX__PREFIX}-{date_iso}'


class Pipeline__Runs__Tracker(Type_Safe):
    http_client : Inventory__HTTP__Client

    @type_safe
    def record_run(self, base_url : str                  ,
                         username : str                  ,
                         password : str                  ,
                         record   : Schema__Pipeline__Run
                    ) -> Tuple[int, int, int, int, str]:                             # (created, updated, failed, http_status, error_message) — passthrough from bulk_post_with_id
        index_name = index_name_for_run(record)
        docs       = List__Schema__Pipeline__Run()
        docs.append(record)
        return self.http_client.bulk_post_with_id(base_url = base_url     ,
                                                    username = username     ,
                                                    password = password     ,
                                                    index    = index_name   ,
                                                    docs     = docs         ,
                                                    id_field = 'run_id'     )       # _id = run_id → re-recording overwrites
