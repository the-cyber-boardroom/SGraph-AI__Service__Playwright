# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — SG_Send__Inventory__Query
# Queries the slice 1 sg-cf-inventory-* index for files matching a date or
# hour.  Used by `sp el lets cf sg-send files {date}`.  One ES call.
#
# Returns a list of dicts: {key, size_bytes, etag, delivery_at, content_processed}
# sorted by delivery_at asc (chronological).
# ═══════════════════════════════════════════════════════════════════════════════

import base64
import json
from typing                                                                         import List, Optional, Tuple

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe

from sgraph_ai_service_playwright__cli.elastic.lets.cf.inventory.service.Inventory__HTTP__Client import Inventory__HTTP__Client


INVENTORY_INDEX_PATTERN = 'sg-cf-inventory-*'
SOURCE_FIELDS           = ['key', 'size_bytes', 'etag', 'delivery_at',
                            'delivery_hour', 'delivery_minute',
                            'content_processed', 'content_extract_run_id']


class SG_Send__Inventory__Query(Type_Safe):
    http_client : Inventory__HTTP__Client

    def list_files_for_date(self, base_url : str           ,
                                   username : str           ,
                                   password : str           ,
                                   year     : int           ,
                                   month    : int           ,
                                   day      : int           ,
                                   hour     : Optional[int] = None,
                                   page_size: int           = 1000
                              ) -> Tuple[List[dict], int, str]:                     # (rows, http_status, error_msg)
        # Build the ES query — bool must on year/month/day, optional hour
        must_clauses = [{'term': {'delivery_year' : int(year )}},
                        {'term': {'delivery_month': int(month)}},
                        {'term': {'delivery_day'  : int(day  )}}]
        if hour is not None:
            must_clauses.append({'term': {'delivery_hour': int(hour)}})

        auth_token = base64.b64encode(f'{username}:{password}'.encode()).decode()
        headers    = {'Content-Type' : 'application/json'  ,
                      'Authorization': f'Basic {auth_token}'}
        body = json.dumps({
            'size'    : page_size,
            'query'   : {'bool': {'must': must_clauses}}                              ,
            'sort'    : [{'delivery_at': {'order': 'asc'}}]                          ,
            '_source' : SOURCE_FIELDS                                                ,
        }).encode('utf-8')
        url = base_url.rstrip('/') + f'/_elastic/{INVENTORY_INDEX_PATTERN}/_search'

        try:
            response = self.http_client.request('POST', url, headers=headers, data=body)
        except Exception as exc:
            return [], 0, f'search error: {str(exc)[:200]}'
        status = int(response.status_code)
        if status == 404:                                                            # No inventory indices at all
            return [], status, ''
        if status >= 300:
            return [], status, f'HTTP {status}: {(response.text or "")[:300]}'

        try:
            payload = response.json() or {}
        except Exception:
            return [], status, 'response was not JSON'

        rows = []
        for hit in payload.get('hits', {}).get('hits', []) or []:
            source = hit.get('_source', {}) or {}
            rows.append({'key'              : str(source.get('key'              , '')),
                          'size_bytes'      : int(source.get('size_bytes'       , 0) or 0),
                          'etag'            : str(source.get('etag'             , '')),
                          'delivery_at'     : str(source.get('delivery_at'      , '')),
                          'delivery_hour'   : int(source.get('delivery_hour'    , 0) or 0),
                          'delivery_minute' : int(source.get('delivery_minute'  , 0) or 0),
                          'content_processed'      : bool(source.get('content_processed'     , False)),
                          'content_extract_run_id' : str (source.get('content_extract_run_id', ''))})
        return rows, status, ''
