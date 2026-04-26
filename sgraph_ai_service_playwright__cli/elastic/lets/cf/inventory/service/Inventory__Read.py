# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Inventory__Read
# Backs the read-only verbs `sp el lets cf inventory list` and `... health`.
# Pure logic; no boto3, no Typer.
#
# list_runs() — terms agg on pipeline_run_id over sg-cf-inventory-* with
#               sub-aggs for byte sum + delivery / loaded date ranges.
#               Returns List__Schema__Inventory__Run__Summary (one row per
#               distinct run id).
#
# health()   — three checks, mirroring the artifacts wipe deletes:
#                 1. indices       — sg-cf-inventory-* count > 0
#                 2. data view     — title sg-cf-inventory-* exists
#                 3. dashboard     — saved-object id sg-cf-inventory-overview
#                                    exists
#               Each check yields a Schema__Elastic__Health__Check; the
#               rollup all_ok is False on a single FAIL.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe
from osbot_utils.type_safe.type_safe_core.decorators.type_safe                      import type_safe

from sgraph_ai_service_playwright__cli.elastic.collections.List__Schema__Elastic__Health__Check import List__Schema__Elastic__Health__Check
from sgraph_ai_service_playwright__cli.elastic.enums.Enum__Health__Status                  import Enum__Health__Status
from sgraph_ai_service_playwright__cli.elastic.enums.Enum__Saved_Object__Type              import Enum__Saved_Object__Type
from sgraph_ai_service_playwright__cli.elastic.primitives.Safe_Str__Elastic__Stack__Name   import Safe_Str__Elastic__Stack__Name
from sgraph_ai_service_playwright__cli.elastic.schemas.Schema__Elastic__Health__Check       import Schema__Elastic__Health__Check
from sgraph_ai_service_playwright__cli.elastic.schemas.Schema__Elastic__Health__Response    import Schema__Elastic__Health__Response
from sgraph_ai_service_playwright__cli.elastic.service.Kibana__Saved_Objects__Client         import Kibana__Saved_Objects__Client

from sgraph_ai_service_playwright__cli.elastic.lets.cf.inventory.collections.List__Schema__Inventory__Run__Summary import List__Schema__Inventory__Run__Summary
from sgraph_ai_service_playwright__cli.elastic.lets.cf.inventory.schemas.Schema__Inventory__Run__Summary           import Schema__Inventory__Run__Summary
from sgraph_ai_service_playwright__cli.elastic.lets.cf.inventory.service.CF__Inventory__Dashboard__Ids             import DASHBOARD_ID
from sgraph_ai_service_playwright__cli.elastic.lets.cf.inventory.service.Inventory__HTTP__Client                    import Inventory__HTTP__Client


INDEX__PATTERN          = 'sg-cf-inventory-*'                                       # Matches every daily index
DATA_VIEW__TITLE        = 'sg-cf-inventory-*'                                       # Wildcard pattern — matches every daily index


def date_string_from_agg(value_dict: dict) -> str:                                  # ES min/max on a date field returns {'value': ms_since_epoch, 'value_as_string': '2026-04-26T11:34:48.000Z'}; we want the string form
    if not isinstance(value_dict, dict):
        return ''
    return str(value_dict.get('value_as_string', '') or '')


def parse_run_bucket(bucket: dict) -> Schema__Inventory__Run__Summary:              # Translate one ES aggregation bucket into a Schema__Inventory__Run__Summary
    return Schema__Inventory__Run__Summary(pipeline_run_id   = str(bucket.get('key', ''))                  ,
                                            object_count      = int(bucket.get('doc_count', 0))             ,
                                            bytes_total       = int((bucket.get('bytes_total'      , {}) or {}).get('value', 0) or 0),
                                            earliest_loaded   = date_string_from_agg(bucket.get('earliest_loaded'  , {})),
                                            latest_loaded     = date_string_from_agg(bucket.get('latest_loaded'    , {})),
                                            earliest_delivery = date_string_from_agg(bucket.get('earliest_delivery', {})),
                                            latest_delivery   = date_string_from_agg(bucket.get('latest_delivery'  , {})))


def find_object_with_id(saved_objects, target_id: str) -> bool:                     # True iff any Schema__Kibana__Saved_Object in the collection has the target id
    for obj in saved_objects:
        if str(obj.id) == target_id:
            return True
    return False


def find_object_with_title(saved_objects, target_title: str) -> bool:               # True iff any Schema__Kibana__Saved_Object has the target title
    for obj in saved_objects:
        if str(obj.title) == target_title:
            return True
    return False


class Inventory__Read(Type_Safe):
    http_client   : Inventory__HTTP__Client
    kibana_client : Kibana__Saved_Objects__Client

    @type_safe
    def list_runs(self, base_url : str ,
                        username : str ,
                        password : str ,
                        top_n    : int = 100
                  ) -> List__Schema__Inventory__Run__Summary:
        buckets, _, _  = self.http_client.aggregate_run_summaries(base_url      = base_url        ,
                                                                    username      = username        ,
                                                                    password      = password        ,
                                                                    index_pattern = INDEX__PATTERN  ,
                                                                    top_n         = top_n           )
        result = List__Schema__Inventory__Run__Summary()
        for bucket in buckets:
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
            checks.append(Schema__Elastic__Health__Check(name='indices',
                                                          status=Enum__Health__Status.FAIL,
                                                          detail=f'count error: {idx_err}'[:200]))
        elif idx_count == 0:
            checks.append(Schema__Elastic__Health__Check(name='indices',
                                                          status=Enum__Health__Status.WARN,
                                                          detail=f'no indices match {INDEX__PATTERN} - run `sp el lets cf inventory load`'))
        else:
            checks.append(Schema__Elastic__Health__Check(name='indices',
                                                          status=Enum__Health__Status.OK,
                                                          detail=f'{idx_count} index(es) match {INDEX__PATTERN}'))

        # ─── check 2: data view ───────────────────────────────────────────────
        dv_resp = self.kibana_client.find(base_url=base_url, username=username, password=password,
                                            object_type=Enum__Saved_Object__Type.DATA_VIEW, page_size=200)
        if int(dv_resp.http_status) >= 300 and not dv_resp.objects:
            checks.append(Schema__Elastic__Health__Check(name='data-view',
                                                          status=Enum__Health__Status.FAIL,
                                                          detail=f'find error: {str(dv_resp.error)[:150]}'))
        elif find_object_with_title(dv_resp.objects, DATA_VIEW__TITLE):
            checks.append(Schema__Elastic__Health__Check(name='data-view',
                                                          status=Enum__Health__Status.OK,
                                                          detail=f'{DATA_VIEW__TITLE} present'))
        else:
            checks.append(Schema__Elastic__Health__Check(name='data-view',
                                                          status=Enum__Health__Status.WARN,
                                                          detail=f'{DATA_VIEW__TITLE} not found - load creates it idempotently'))

        # ─── check 3: dashboard ───────────────────────────────────────────────
        db_resp = self.kibana_client.find(base_url=base_url, username=username, password=password,
                                            object_type=Enum__Saved_Object__Type.DASHBOARD, page_size=200)
        if int(db_resp.http_status) >= 300 and not db_resp.objects:
            checks.append(Schema__Elastic__Health__Check(name='dashboard',
                                                          status=Enum__Health__Status.FAIL,
                                                          detail=f'find error: {str(db_resp.error)[:150]}'))
        elif find_object_with_id(db_resp.objects, DASHBOARD_ID):
            checks.append(Schema__Elastic__Health__Check(name='dashboard',
                                                          status=Enum__Health__Status.OK,
                                                          detail=f'{DASHBOARD_ID} present'))
        else:
            checks.append(Schema__Elastic__Health__Check(name='dashboard',
                                                          status=Enum__Health__Status.WARN,
                                                          detail=f'{DASHBOARD_ID} not found - load imports it idempotently'))

        # WARN does not fail the rollup; only FAIL flips all_ok to False
        all_ok = all(str(chk.status) != 'fail' for chk in checks)
        return Schema__Elastic__Health__Response(stack_name=stack_name, all_ok=all_ok, checks=checks)
