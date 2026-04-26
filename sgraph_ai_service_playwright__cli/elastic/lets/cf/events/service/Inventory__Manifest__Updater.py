# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Inventory__Manifest__Updater
# Flips an inventory doc's content_processed flag from false to true and
# stamps the events-pass run id.  Issued once per file processed by
# Events__Loader.  Uses _update_by_query filtered on the file's etag —
# guarantees we update the right doc regardless of which daily index it
# lives in.
#
# Painless script:
#   ctx._source.content_processed       = true
#   ctx._source.content_extract_run_id  = params.run_id
#
# The wiper (Phase 5) flips them all back to false via a similar
# _update_by_query, so wipe-and-reload returns to a clean state.
# ═══════════════════════════════════════════════════════════════════════════════

import base64
import json
from typing                                                                         import Tuple

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe
from osbot_utils.type_safe.type_safe_core.decorators.type_safe                      import type_safe

from sgraph_ai_service_playwright__cli.elastic.lets.cf.inventory.service.Inventory__HTTP__Client import Inventory__HTTP__Client


INVENTORY_INDEX_PATTERN = 'sg-cf-inventory-*'

PAINLESS_MARK_PROCESSED = ('ctx._source.content_processed = true; '
                            'ctx._source.content_extract_run_id = params.run_id;')


class Inventory__Manifest__Updater(Type_Safe):
    http_client : Inventory__HTTP__Client

    @type_safe
    def mark_processed(self, base_url : str ,
                              username : str ,
                              password : str ,
                              etag     : str ,
                              run_id   : str
                        ) -> Tuple[int, int, str]:                                  # (docs_updated, http_status, error_message)
        if not etag:
            return 0, 0, 'no etag'

        auth_token = base64.b64encode(f'{username}:{password}'.encode()).decode()
        headers    = {'Content-Type' : 'application/json'  ,
                      'Authorization': f'Basic {auth_token}'}
        body = json.dumps({
            'query'  : {'term': {'etag': etag}}                                      ,
            'script' : {'lang'   : 'painless'                                       ,
                        'source' : PAINLESS_MARK_PROCESSED                          ,
                        'params' : {'run_id': str(run_id)}                          },
        }).encode('utf-8')
        url = base_url.rstrip('/') + f'/_elastic/{INVENTORY_INDEX_PATTERN}/_update_by_query?refresh=true&conflicts=proceed'

        try:
            response = self.http_client.request('POST', url, headers=headers, data=body)
        except Exception as exc:
            return 0, 0, f'update error: {str(exc)[:200]}'
        status = int(response.status_code)
        if status == 404:                                                           # Pattern matches no indices — nothing to update
            return 0, status, ''
        if status >= 300:
            return 0, status, f'HTTP {status}: {(response.text or "")[:300]}'

        try:
            payload = response.json() or {}
        except Exception:
            return 0, status, 'response was not JSON'
        return int(payload.get('updated', 0) or 0), status, ''

    @type_safe
    def reset_all_processed(self, base_url : str ,
                                   username : str ,
                                   password : str
                              ) -> Tuple[int, int, str]:                            # (docs_reset, http_status, error_message)
        # The wiper (Phase 5) calls this — flips every content_processed=true
        # back to false so that `events load --from-inventory` finds the full
        # queue again after a wipe.
        auth_token = base64.b64encode(f'{username}:{password}'.encode()).decode()
        headers    = {'Content-Type' : 'application/json'  ,
                      'Authorization': f'Basic {auth_token}'}
        body = json.dumps({
            'query'  : {'term': {'content_processed': True}}                         ,
            'script' : {'lang'   : 'painless'                                       ,
                        'source' : 'ctx._source.content_processed = false; ctx._source.content_extract_run_id = "";'},
        }).encode('utf-8')
        url = base_url.rstrip('/') + f'/_elastic/{INVENTORY_INDEX_PATTERN}/_update_by_query?refresh=true&conflicts=proceed'

        try:
            response = self.http_client.request('POST', url, headers=headers, data=body)
        except Exception as exc:
            return 0, 0, f'reset error: {str(exc)[:200]}'
        status = int(response.status_code)
        if status == 404:
            return 0, status, ''
        if status >= 300:
            return 0, status, f'HTTP {status}: {(response.text or "")[:300]}'
        try:
            payload = response.json() or {}
        except Exception:
            return 0, status, 'response was not JSON'
        return int(payload.get('updated', 0) or 0), status, ''
