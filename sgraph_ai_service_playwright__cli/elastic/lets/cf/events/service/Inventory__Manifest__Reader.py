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
