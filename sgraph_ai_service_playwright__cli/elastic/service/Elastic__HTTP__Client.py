# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Elastic__HTTP__Client
# Talks to a running ephemeral Elastic+Kibana instance over HTTPS on port 443.
# Two operations:
#   1. kibana_ready()  — GET /api/status, returns True on HTTP 200
#   2. bulk_post(...)  — POST /_elastic/_bulk, NDJSON body, Basic auth
#
# The `/_elastic/` prefix is the nginx rewrite that strips the prefix and
# forwards to elasticsearch:9200 inside the docker network (see
# Elastic__User__Data__Builder). Using it means we don't need a separate SG
# ingress rule for ES port 9200 — everything rides 443.
#
# verify=False is intentional and non-negotiable for this slice: the cert is
# self-signed at boot (per the brief's "we will implement a better solution
# later"). Once a DNS/Let's-Encrypt design lands, flip verify=True.
#
# Tests subclass and override `request()` so assertions work without a real
# endpoint. No mocks, no patches.
# ═══════════════════════════════════════════════════════════════════════════════

import json
import warnings
from typing                                                                         import Tuple

import requests
from urllib3.exceptions                                                             import InsecureRequestWarning

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe
from osbot_utils.type_safe.type_safe_core.decorators.type_safe                      import type_safe

from sgraph_ai_service_playwright__cli.elastic.collections.List__Schema__Log__Document   import List__Schema__Log__Document
from sgraph_ai_service_playwright__cli.elastic.enums.Enum__Kibana__Probe__Status    import Enum__Kibana__Probe__Status


DEFAULT_TIMEOUT = 30


class Elastic__HTTP__Client(Type_Safe):
    timeout : int  = DEFAULT_TIMEOUT
    verify  : bool = False                                                          # Self-signed cert — see module header

    def request(self, method: str, url: str, *,                                     # Single seam for test overrides
                      headers: dict = None,
                      data   : bytes = None
                ) -> requests.Response:
        with warnings.catch_warnings():                                             # verify=False is intentional (self-signed cert) — silence urllib3's noise for our requests only, without touching global warning filters
            warnings.simplefilter('ignore', InsecureRequestWarning)
            return requests.request(method = method            ,
                                    url    = url               ,
                                    headers= headers or {}     ,
                                    data   = data              ,
                                    timeout= self.timeout      ,
                                    verify = self.verify       )

    @type_safe
    def kibana_ready(self, base_url: str) -> bool:                                  # Back-compat bool wrapper around kibana_probe()
        return self.kibana_probe(base_url) == Enum__Kibana__Probe__Status.READY

    @type_safe
    def kibana_probe(self, base_url: str) -> Enum__Kibana__Probe__Status:
        url = base_url.rstrip('/') + '/api/status'
        try:
            response = self.request('GET', url)
        except Exception:
            return Enum__Kibana__Probe__Status.UNREACHABLE                          # Connection refused / DNS fail / timeout — nothing answering yet
        code = int(response.status_code)
        if code == 200:
            return Enum__Kibana__Probe__Status.READY
        if 500 <= code < 600:
            return Enum__Kibana__Probe__Status.UPSTREAM_DOWN                        # nginx 502/503/504 — nginx is up, Kibana container isn't (yet)
        if 300 <= code < 500:
            return Enum__Kibana__Probe__Status.BOOTING                              # Rare: Kibana answered but not 200
        return Enum__Kibana__Probe__Status.UNKNOWN

    @type_safe
    def bulk_post(self, base_url : str                          ,
                        username : str                          ,
                        password : str                          ,
                        index    : str                          ,
                        docs     : List__Schema__Log__Document
                   ) -> Tuple[int, int]:                                            # (posted, failed)
        if len(docs) == 0:
            return 0, 0

        import base64
        auth_raw   = f'{username}:{password}'.encode()
        auth_token = base64.b64encode(auth_raw).decode()
        url        = base_url.rstrip('/') + '/_elastic/_bulk'
        headers    = {'Content-Type' : 'application/x-ndjson'     ,
                      'Authorization': f'Basic {auth_token}'      }

        body_lines = []
        for doc in docs:
            body_lines.append(json.dumps({'index': {'_index': index}}))
            body_lines.append(doc.json())                                           # Type_Safe schemas serialise via .json()
        body = ('\n'.join(body_lines) + '\n').encode('utf-8')

        response = self.request('POST', url, headers=headers, data=body)
        if response.status_code >= 300:
            return 0, len(docs)

        payload = response.json() or {}
        failed  = 0
        if payload.get('errors'):
            for item in payload.get('items', []):
                action = next(iter(item.values()), {})
                if int(action.get('status', 0)) >= 300:
                    failed += 1
        posted = len(docs) - failed
        return posted, failed
