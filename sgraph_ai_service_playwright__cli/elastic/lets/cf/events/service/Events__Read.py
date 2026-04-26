# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Events__Read
# Backs `sp el lets cf events list` and `... health`.  Pure logic.
#
# list_runs() — terms agg on pipeline_run_id over sg-cf-events-* with sub-aggs:
#   - event_count       : doc count (implicit)
#   - file_count        : cardinality on source_etag.keyword (distinct .gz files)
#   - bytes_total       : sum of sc_bytes
#   - earliest_event    : min(timestamp)
#   - latest_event      : max(timestamp)
#   - earliest_loaded   : min(loaded_at)
#   - latest_loaded     : max(loaded_at)
#
# health() — four checks:
#   1. events-indices    sg-cf-events-* count > 0
#   2. events-data-view  Kibana data view sg-cf-events-* exists
#   3. events-dashboard  Kibana dashboard sg-cf-events-overview exists
#   4. inventory-link    bonus: count of inventory docs where
#                        content_processed=true vs false — surfaces "X of Y
#                        files processed" so the operator sees how complete
#                        the events index is at a glance
# ═══════════════════════════════════════════════════════════════════════════════

import base64
import json
from typing                                                                         import Tuple

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe
from osbot_utils.type_safe.type_safe_core.decorators.type_safe                      import type_safe

from sgraph_ai_service_playwright__cli.elastic.collections.List__Schema__Elastic__Health__Check import List__Schema__Elastic__Health__Check
from sgraph_ai_service_playwright__cli.elastic.enums.Enum__Health__Status                  import Enum__Health__Status
from sgraph_ai_service_playwright__cli.elastic.enums.Enum__Saved_Object__Type              import Enum__Saved_Object__Type
from sgraph_ai_service_playwright__cli.elastic.primitives.Safe_Str__Elastic__Stack__Name   import Safe_Str__Elastic__Stack__Name
from sgraph_ai_service_playwright__cli.elastic.schemas.Schema__Elastic__Health__Check       import Schema__Elastic__Health__Check
from sgraph_ai_service_playwright__cli.elastic.schemas.Schema__Elastic__Health__Response    import Schema__Elastic__Health__Response
from sgraph_ai_service_playwright__cli.elastic.service.Kibana__Saved_Objects__Client         import Kibana__Saved_Objects__Client

from sgraph_ai_service_playwright__cli.elastic.lets.cf.inventory.service.Inventory__HTTP__Client import Inventory__HTTP__Client

from sgraph_ai_service_playwright__cli.elastic.lets.cf.events.collections.List__Schema__Events__Run__Summary import List__Schema__Events__Run__Summary
from sgraph_ai_service_playwright__cli.elastic.lets.cf.events.schemas.Schema__Events__Run__Summary           import Schema__Events__Run__Summary
from sgraph_ai_service_playwright__cli.elastic.lets.cf.events.service.CF__Events__Dashboard__Ids             import DASHBOARD_ID


INDEX__PATTERN              = 'sg-cf-events-*'
DATA_VIEW__TITLE            = 'sg-cf-events-*'
INVENTORY_INDEX_PATTERN     = 'sg-cf-inventory-*'                                   # For the inventory-link health check


def date_string_from_agg(value_dict: dict) -> str:
    if not isinstance(value_dict, dict):
        return ''
    return str(value_dict.get('value_as_string', '') or '')


def parse_run_bucket(bucket: dict) -> Schema__Events__Run__Summary:
    return Schema__Events__Run__Summary(pipeline_run_id  = str(bucket.get('key', ''))                  ,
                                          event_count      = int(bucket.get('doc_count', 0) or 0)        ,
                                          file_count       = int((bucket.get('file_count'  , {}) or {}).get('value', 0) or 0),
                                          bytes_total      = int((bucket.get('bytes_total' , {}) or {}).get('value', 0) or 0),
                                          earliest_event   = date_string_from_agg(bucket.get('earliest_event' , {})),
                                          latest_event     = date_string_from_agg(bucket.get('latest_event'   , {})),
                                          earliest_loaded  = date_string_from_agg(bucket.get('earliest_loaded', {})),
                                          latest_loaded    = date_string_from_agg(bucket.get('latest_loaded'  , {})))


def find_object_with_id(saved_objects, target_id: str) -> bool:
    for obj in saved_objects:
        if str(obj.id) == target_id:
            return True
    return False


def find_object_with_title(saved_objects, target_title: str) -> bool:
    for obj in saved_objects:
        if str(obj.title) == target_title:
            return True
    return False


class Events__Read(Type_Safe):
    http_client   : Inventory__HTTP__Client
    kibana_client : Kibana__Saved_Objects__Client

    @type_safe
    def list_runs(self, base_url : str ,
                        username : str ,
                        password : str ,
                        top_n    : int = 100
                  ) -> List__Schema__Events__Run__Summary:
        if top_n <= 0:
            return List__Schema__Events__Run__Summary()

        auth_token = base64.b64encode(f'{username}:{password}'.encode()).decode()
        headers    = {'Content-Type' : 'application/json'  ,
                      'Authorization': f'Basic {auth_token}'}
        body = json.dumps({
            'size'    : 0,
            'aggs'    : {
                'by_run': {
                    'terms': {'field' : 'pipeline_run_id.keyword'  ,
                              'size'  : top_n                       ,
                              'order' : {'latest_loaded': 'desc'}    },
                    'aggs': {
                        'file_count'       : {'cardinality': {'field': 'source_etag.keyword'}},
                        'bytes_total'      : {'sum'        : {'field': 'sc_bytes'           }},
                        'earliest_event'   : {'min'        : {'field': 'timestamp'          }},
                        'latest_event'     : {'max'        : {'field': 'timestamp'          }},
                        'earliest_loaded'  : {'min'        : {'field': 'loaded_at'          }},
                        'latest_loaded'    : {'max'        : {'field': 'loaded_at'          }},
                    },
                },
            },
        }).encode('utf-8')
        url = base_url.rstrip('/') + f'/_elastic/{INDEX__PATTERN}/_search'

        result = List__Schema__Events__Run__Summary()
        try:
            response = self.http_client.request('POST', url, headers=headers, data=body)
        except Exception:                                                            # No HTTP connectivity → empty list
            return result
        status = int(response.status_code)
        if status >= 300:
            return result
        try:
            payload = response.json() or {}
        except Exception:
            return result
        for bucket in payload.get('aggregations', {}).get('by_run', {}).get('buckets', []) or []:
            result.append(parse_run_bucket(bucket))
        return result

    @type_safe
    def health(self, base_url   : str ,
                     username   : str ,
                     password   : str ,
                     stack_name : Safe_Str__Elastic__Stack__Name = ''
              ) -> Schema__Elastic__Health__Response:
        checks = List__Schema__Elastic__Health__Check()

        # ─── check 1: indices ─────────────────────────────────────────────────
        idx_count, idx_status, idx_err = self.http_client.count_indices_by_pattern(
            base_url=base_url, username=username, password=password, pattern=INDEX__PATTERN)
        if idx_err:
            checks.append(Schema__Elastic__Health__Check(name='events-indices',
                                                          status=Enum__Health__Status.FAIL,
                                                          detail=f'count error: {idx_err}'[:200]))
        elif idx_count == 0:
            checks.append(Schema__Elastic__Health__Check(name='events-indices',
                                                          status=Enum__Health__Status.WARN,
                                                          detail=f'no indices match {INDEX__PATTERN} - run `sp el lets cf events load`'))
        else:
            checks.append(Schema__Elastic__Health__Check(name='events-indices',
                                                          status=Enum__Health__Status.OK,
                                                          detail=f'{idx_count} index(es) match {INDEX__PATTERN}'))

        # ─── check 2: data view ───────────────────────────────────────────────
        dv_resp = self.kibana_client.find(base_url=base_url, username=username, password=password,
                                            object_type=Enum__Saved_Object__Type.DATA_VIEW, page_size=200)
        if int(dv_resp.http_status) >= 300 and not dv_resp.objects:
            checks.append(Schema__Elastic__Health__Check(name='events-data-view',
                                                          status=Enum__Health__Status.FAIL,
                                                          detail=f'find error: {str(dv_resp.error)[:150]}'))
        elif find_object_with_title(dv_resp.objects, DATA_VIEW__TITLE):
            checks.append(Schema__Elastic__Health__Check(name='events-data-view',
                                                          status=Enum__Health__Status.OK,
                                                          detail=f'{DATA_VIEW__TITLE} present'))
        else:
            checks.append(Schema__Elastic__Health__Check(name='events-data-view',
                                                          status=Enum__Health__Status.WARN,
                                                          detail=f'{DATA_VIEW__TITLE} not found - load creates it idempotently'))

        # ─── check 3: dashboard ───────────────────────────────────────────────
        db_resp = self.kibana_client.find(base_url=base_url, username=username, password=password,
                                            object_type=Enum__Saved_Object__Type.DASHBOARD, page_size=200)
        if int(db_resp.http_status) >= 300 and not db_resp.objects:
            checks.append(Schema__Elastic__Health__Check(name='events-dashboard',
                                                          status=Enum__Health__Status.FAIL,
                                                          detail=f'find error: {str(db_resp.error)[:150]}'))
        elif find_object_with_id(db_resp.objects, DASHBOARD_ID):
            checks.append(Schema__Elastic__Health__Check(name='events-dashboard',
                                                          status=Enum__Health__Status.OK,
                                                          detail=f'{DASHBOARD_ID} present'))
        else:
            checks.append(Schema__Elastic__Health__Check(name='events-dashboard',
                                                          status=Enum__Health__Status.WARN,
                                                          detail=f'{DASHBOARD_ID} not found - load imports it idempotently'))

        # ─── check 4: inventory-link (bonus) ─────────────────────────────────
        inv_processed, inv_total, inv_err = self.inventory_processed_counts(
            base_url=base_url, username=username, password=password)
        if inv_err:
            checks.append(Schema__Elastic__Health__Check(name='inventory-link',
                                                          status=Enum__Health__Status.SKIP,
                                                          detail=f'inventory query error: {inv_err}'[:200]))
        elif inv_total == 0:
            checks.append(Schema__Elastic__Health__Check(name='inventory-link',
                                                          status=Enum__Health__Status.WARN,
                                                          detail='no inventory docs - run `sp el lets cf inventory load` first'))
        else:
            pct = int(round(100 * inv_processed / inv_total)) if inv_total else 0
            checks.append(Schema__Elastic__Health__Check(name='inventory-link',
                                                          status=Enum__Health__Status.OK,
                                                          detail=f'{inv_processed} of {inv_total} inventory docs processed ({pct}%)'))

        all_ok = all(str(chk.status) != 'fail' for chk in checks)
        return Schema__Elastic__Health__Response(stack_name=stack_name, all_ok=all_ok, checks=checks)

    def inventory_processed_counts(self, base_url : str ,
                                          username : str ,
                                          password : str
                                    ) -> Tuple[int, int, str]:                       # (processed_true_count, total_count, error)
        # Two _count queries on sg-cf-inventory-*: total and content_processed=true.
        auth_token = base64.b64encode(f'{username}:{password}'.encode()).decode()
        headers    = {'Content-Type' : 'application/json'  ,
                      'Authorization': f'Basic {auth_token}'}
        url        = base_url.rstrip('/') + f'/_elastic/{INVENTORY_INDEX_PATTERN}/_count'

        try:
            total_resp = self.http_client.request('POST', url, headers=headers, data=b'{}')
        except Exception as exc:
            return 0, 0, f'total count error: {str(exc)[:120]}'
        if int(total_resp.status_code) == 404:                                      # No inventory indices at all
            return 0, 0, ''
        if int(total_resp.status_code) >= 300:
            return 0, 0, f'total count HTTP {total_resp.status_code}'
        try:
            total = int((total_resp.json() or {}).get('count', 0) or 0)
        except Exception:
            return 0, 0, 'total count not JSON'

        body = json.dumps({'query': {'term': {'content_processed': True}}}).encode('utf-8')
        try:
            proc_resp = self.http_client.request('POST', url, headers=headers, data=body)
        except Exception as exc:
            return 0, total, f'processed count error: {str(exc)[:120]}'
        if int(proc_resp.status_code) >= 300:
            return 0, total, f'processed count HTTP {proc_resp.status_code}'
        try:
            processed = int((proc_resp.json() or {}).get('count', 0) or 0)
        except Exception:
            return 0, total, 'processed count not JSON'

        return processed, total, ''
