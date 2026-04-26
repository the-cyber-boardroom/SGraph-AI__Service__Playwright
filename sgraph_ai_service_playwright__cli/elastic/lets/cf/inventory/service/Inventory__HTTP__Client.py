# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Inventory__HTTP__Client
# Sibling HTTP boundary for the LETS inventory pipeline. Carved out of (rather
# than extending) Elastic__HTTP__Client because:
#   1. The brief promises Elastic__HTTP__Client stays unmodified (the
#      existing 165 elastic tests must stay green).
#   2. Our bulk-post needs etag-as-_id support; the existing bulk_post is
#      typed to List__Schema__Log__Document and doesn't pass an _id.
# Methods:
#   1. bulk_post_with_id(base_url, username, password, index, docs, id_field)
#      Bulk-posts any Type_Safe collection, using the named field of each doc
#      as the Elastic _id so re-loads dedupe at index time.
# verify=False mirrors Elastic__HTTP__Client (self-signed nginx cert).
# Tests subclass and override the public method (no mocks).
# ═══════════════════════════════════════════════════════════════════════════════

import base64
import json
import warnings
from typing                                                                         import Any, Tuple

import requests
from urllib3.exceptions                                                             import InsecureRequestWarning

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe
from osbot_utils.type_safe.type_safe_core.collections.Type_Safe__List               import Type_Safe__List


DEFAULT_TIMEOUT = 30


class Inventory__HTTP__Client(Type_Safe):
    timeout : int  = DEFAULT_TIMEOUT
    verify  : bool = False                                                          # Self-signed nginx cert — mirrors Elastic__HTTP__Client

    def request(self, method: str, url: str, *,                                     # Single seam for test overrides
                      headers: dict = None,
                      data   : bytes = None
                ) -> requests.Response:
        with warnings.catch_warnings():
            warnings.simplefilter('ignore', InsecureRequestWarning)
            return requests.request(method = method            ,
                                    url    = url               ,
                                    headers= headers or {}     ,
                                    data   = data              ,
                                    timeout= self.timeout      ,
                                    verify = self.verify       )

    def bulk_post_with_id(self, base_url : str              ,
                                username : str              ,
                                password : str              ,
                                index    : str              ,
                                docs     : Type_Safe__List   ,                       # Any Type_Safe collection (List__Schema__S3__Object__Record etc.)
                                id_field : str              = 'etag'                # Field on each doc whose value becomes _id; etag default for the inventory case
                          ) -> Tuple[int, int, int, int, str]:                       # (created, updated, failed, http_status, error_message)
        if len(docs) == 0:
            return 0, 0, 0, 0, ''

        auth_token = base64.b64encode(f'{username}:{password}'.encode()).decode()
        url        = base_url.rstrip('/') + '/_elastic/_bulk'
        headers    = {'Content-Type' : 'application/x-ndjson'  ,
                      'Authorization': f'Basic {auth_token}'   }

        body_lines = []
        for doc in docs:
            doc_dict = doc.json()
            doc_id   = str(doc_dict.get(id_field, '') or '')                        # Empty id_field → ES generates an id; lose dedup but keep robustness
            action   = {'index': {'_index': index, '_id': doc_id}} if doc_id else {'index': {'_index': index}}
            body_lines.append(json.dumps(action))
            body_lines.append(json.dumps(doc_dict))
        body = ('\n'.join(body_lines) + '\n').encode('utf-8')

        response = self.request('POST', url, headers=headers, data=body)
        status   = int(response.status_code)
        if status >= 300:                                                           # Whole batch rejected
            return 0, 0, len(docs), status, f'HTTP {status}: {(response.text or "")[:500]}'

        payload = response.json() or {}
        created = 0
        updated = 0
        failed  = 0
        err_msg = ''
        for item in payload.get('items', []):
            action = next(iter(item.values()), {})                                  # Extract the action dict whatever the verb (index/create/update)
            item_status = int(action.get('status', 0))
            result      = str(action.get('result', '') or '')
            if item_status >= 300:
                failed += 1
                if not err_msg:
                    reason = action.get('error', {}).get('reason', '')
                    err_msg = f'per-item HTTP {item_status}: {reason}'[:500]
            elif result == 'created':
                created += 1
            elif result == 'updated':
                updated += 1
            else:                                                                   # noop / unexpected — count as updated so totals add up
                updated += 1
        return created, updated, failed, status, err_msg

    def delete_indices_by_pattern(self, base_url : str ,
                                         username : str ,
                                         password : str ,
                                         pattern  : str
                                    ) -> Tuple[int, int, str]:                       # (indices_dropped, http_status, error_message)
        # Two-step: list matching indices first (so we can return a count),
        # then DELETE the pattern.  ES's DELETE /_elastic/{pattern} succeeds
        # even when the pattern matches zero indices, but doesn't tell us
        # the count — and the count is what makes wipe's idempotency
        # contract observable.
        if not pattern:
            return 0, 0, 'no pattern'

        auth_token = base64.b64encode(f'{username}:{password}'.encode()).decode()
        headers    = {'Authorization': f'Basic {auth_token}'}
        list_url   = base_url.rstrip('/') + f'/_elastic/_cat/indices/{pattern}?format=json&h=index&expand_wildcards=open'

        try:
            list_resp = self.request('GET', list_url, headers=headers)
        except Exception as exc:
            return 0, 0, f'list error: {str(exc)[:200]}'
        list_status = int(list_resp.status_code)
        if list_status == 404:                                                       # _cat/indices returns 404 when the pattern matches nothing in some ES configs
            return 0, list_status, ''
        if list_status >= 300:
            return 0, list_status, f'list HTTP {list_status}: {(list_resp.text or "")[:300]}'

        try:
            entries = list_resp.json() or []
        except Exception:
            entries = []
        count = len(entries)
        if count == 0:
            return 0, list_status, ''                                                # Nothing to delete

        # DELETE pattern — ES handles the wildcard server-side
        delete_url    = base_url.rstrip('/') + f'/_elastic/{pattern}'
        delete_resp   = self.request('DELETE', delete_url, headers=headers)
        delete_status = int(delete_resp.status_code)
        if delete_status >= 300:
            return 0, delete_status, f'delete HTTP {delete_status}: {(delete_resp.text or "")[:300]}'
        return count, delete_status, ''
