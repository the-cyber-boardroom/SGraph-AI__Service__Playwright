# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — Elastic: Elastic__HTTP__Client
# ═══════════════════════════════════════════════════════════════════════════════

import base64
import warnings

import requests
from urllib3.exceptions                                                             import InsecureRequestWarning

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe

from sg_compute_specs.elastic.enums.Enum__Elastic__Probe__Status                    import Enum__Elastic__Probe__Status
from sg_compute_specs.elastic.enums.Enum__Kibana__Probe__Status                     import Enum__Kibana__Probe__Status


DEFAULT_TIMEOUT = 30


class Elastic__HTTP__Client(Type_Safe):
    timeout : int  = DEFAULT_TIMEOUT
    verify  : bool = False

    def request(self, method: str, url: str, *,
                      headers: dict  = None,
                      data   : bytes = None) -> requests.Response:
        with warnings.catch_warnings():
            warnings.simplefilter('ignore', InsecureRequestWarning)
            return requests.request(method  = method        ,
                                    url     = url           ,
                                    headers = headers or {} ,
                                    data    = data          ,
                                    timeout = self.timeout  ,
                                    verify  = self.verify   )

    def elastic_probe(self, base_url: str, username: str = '', password: str = '') -> Enum__Elastic__Probe__Status:
        url     = base_url.rstrip('/') + '/_elastic/_cluster/health'
        headers = {}
        if username and password:
            auth_token = base64.b64encode(f'{username}:{password}'.encode()).decode()
            headers['Authorization'] = f'Basic {auth_token}'
        try:
            response = self.request('GET', url, headers=headers)
        except Exception:
            return Enum__Elastic__Probe__Status.UNREACHABLE
        code = int(response.status_code)
        if code in (401, 403):
            return Enum__Elastic__Probe__Status.AUTH_REQUIRED
        if 500 <= code < 600:
            return Enum__Elastic__Probe__Status.UNREACHABLE
        if code != 200:
            return Enum__Elastic__Probe__Status.UNKNOWN
        try:
            payload = response.json() or {}
        except Exception:
            return Enum__Elastic__Probe__Status.UNKNOWN
        status = str(payload.get('status', '')).lower()
        if status == 'green':
            return Enum__Elastic__Probe__Status.GREEN
        if status == 'yellow':
            return Enum__Elastic__Probe__Status.YELLOW
        if status == 'red':
            return Enum__Elastic__Probe__Status.RED
        return Enum__Elastic__Probe__Status.UNKNOWN

    def kibana_probe(self, base_url: str) -> Enum__Kibana__Probe__Status:
        url = base_url.rstrip('/') + '/api/status'
        try:
            response = self.request('GET', url)
        except Exception:
            return Enum__Kibana__Probe__Status.UNREACHABLE
        code = int(response.status_code)
        if code == 200:
            return Enum__Kibana__Probe__Status.READY
        if 500 <= code < 600:
            return Enum__Kibana__Probe__Status.UPSTREAM_DOWN
        if 300 <= code < 500:
            return Enum__Kibana__Probe__Status.BOOTING
        return Enum__Kibana__Probe__Status.UNKNOWN
