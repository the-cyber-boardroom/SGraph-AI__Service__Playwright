# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Inventory__Manifest__Reader
# Queries sg-cf-inventory-* for documents where content_processed=false.
# Each returned dict has { bucket, key, etag, size_bytes, delivery_at } —
# exactly what Events__Loader needs to fetch the .gz file and update the
# inventory back-pointer afterwards.
#
# Sole consumer of slice 1's "content_processed: false" forward declaration.
# Sorted delivery_at desc so the most recent files are fetched first.
#
# Test seam is `list_unprocessed()` itself — the In_Memory subclass returns
# canned dicts, so tests don't need to mock HTTP.
# ═══════════════════════════════════════════════════════════════════════════════

import base64
import json
from typing                                                                         import List, Tuple

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe
from osbot_utils.type_safe.type_safe_core.decorators.type_safe                      import type_safe

from sgraph_ai_service_playwright__cli.elastic.lets.cf.inventory.service.Inventory__HTTP__Client import Inventory__HTTP__Client


INVENTORY_INDEX_PATTERN = 'sg-cf-inventory-*'                                       # Same pattern slice 1 uses
SOURCE_FIELDS           = ['bucket', 'key', 'etag', 'size_bytes', 'delivery_at']


class Inventory__Manifest__Reader(Type_Safe):
    http_client : Inventory__HTTP__Client

    @type_safe
    def list_unprocessed(self, base_url : str ,
                                username : str ,
                                password : str ,
                                top_n    : int = 100
                          ) -> Tuple[List[dict], int, str]:                         # (docs, http_status, error_message)
        if top_n <= 0:
            return [], 0, 'top_n must be positive'

        auth_token = base64.b64encode(f'{username}:{password}'.encode()).decode()
        headers    = {'Content-Type' : 'application/json'  ,
                      'Authorization': f'Basic {auth_token}'}
        body = json.dumps({
            'size'    : top_n                                                        ,
            'query'   : {'term': {'content_processed': False}}                       ,
            'sort'    : [{'delivery_at': {'order': 'desc'}}]                         ,
            '_source' : SOURCE_FIELDS                                                ,
        }).encode('utf-8')
        url = base_url.rstrip('/') + f'/_elastic/{INVENTORY_INDEX_PATTERN}/_search'

        try:
            response = self.http_client.request('POST', url, headers=headers, data=body)
        except Exception as exc:
            return [], 0, f'search error: {str(exc)[:200]}'
        status = int(response.status_code)
        if status == 404:                                                           # No inventory indices at all — empty queue is the right answer
            return [], status, ''
        if status >= 300:
            return [], status, f'HTTP {status}: {(response.text or "")[:300]}'

        try:
            payload = response.json() or {}
        except Exception:
            return [], status, 'response was not JSON'

        docs = []
        for hit in payload.get('hits', {}).get('hits', []) or []:
            source = hit.get('_source', {}) or {}
            docs.append({'bucket'      : str(source.get('bucket'      , '')),
                         'key'         : str(source.get('key'         , '')),
                         'etag'        : str(source.get('etag'        , '')),
                         'size_bytes'  : int(source.get('size_bytes'  , 0) or 0),
                         'delivery_at' : str(source.get('delivery_at' , ''))})
        return docs, status, ''

    @type_safe
    def list_processed_etags(self, base_url : str ,
                                    username : str ,
                                    password : str ,
                                    size_cap : int = 10000
                              ) -> set:                                              # Returns the set of inventory etags whose content_processed=true. One ES call. Single source of truth for "we touched this file" — covers 0-event files (which never appear in sg-cf-events-* but DO get manifest.content_processed=true via Events__Loader).
        # Used by Events__Loader's --skip-processed.  Cheap: terms agg with
        # size_cap=10000 (covers >25 days at sg-send's typical cadence
        # ~375 files/day).  Beyond that the filter degrades gracefully — we'd
        # re-fetch a few files unnecessarily, which is correct just not optimal.
        auth_token = base64.b64encode(f'{username}:{password}'.encode()).decode()
        headers    = {'Content-Type' : 'application/json'  ,
                      'Authorization': f'Basic {auth_token}'}
        body = json.dumps({
            'size'    : 0                                                            ,
            'query'   : {'term': {'content_processed': True}}                        ,
            'aggs'    : {'distinct_etags': {'terms': {'field': 'etag.keyword',
                                                       'size' : int(size_cap)        }}},
        }).encode('utf-8')
        url = base_url.rstrip('/') + f'/_elastic/{INVENTORY_INDEX_PATTERN}/_search'

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
