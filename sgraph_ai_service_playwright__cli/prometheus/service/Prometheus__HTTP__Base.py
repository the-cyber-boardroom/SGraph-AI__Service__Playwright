# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Prometheus__HTTP__Base
# Base HTTP request seam for Prometheus. Mirrors OpenSearch__HTTP__Base
# (verify=False default + scoped urllib3 warning suppression + Basic auth seam)
# even though sp prom serves plain HTTP on port 9090 today (P1: no auth, no
# TLS) — the seam parity keeps probe / query / targets in sibling files of
# their own and lets a future nginx-wrapped deployment slot in cleanly.
# ═══════════════════════════════════════════════════════════════════════════════

import warnings

import requests
from requests.auth                                                                  import HTTPBasicAuth
from urllib3.exceptions                                                             import InsecureRequestWarning

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe


DEFAULT_TIMEOUT = 30


class Prometheus__HTTP__Base(Type_Safe):
    timeout : int  = DEFAULT_TIMEOUT
    verify  : bool = False                                                          # Plain HTTP today; flip to True once a nginx-wrapped design lands

    def request(self, method: str, url: str, *,                                     # Single seam — tests override to script responses
                      headers: dict = None,
                      data   : bytes = None,
                      params : dict = None,
                      username: str = '',
                      password: str = '') -> requests.Response:
        auth = HTTPBasicAuth(username, password) if (username or password) else None
        with warnings.catch_warnings():                                             # Silence urllib3 InsecureRequestWarning for our request only
            warnings.simplefilter('ignore', InsecureRequestWarning)
            return requests.request(method = method            ,
                                    url    = url               ,
                                    headers= headers or {}     ,
                                    data   = data              ,
                                    params = params            ,
                                    auth   = auth              ,
                                    timeout= self.timeout      ,
                                    verify = self.verify       )
