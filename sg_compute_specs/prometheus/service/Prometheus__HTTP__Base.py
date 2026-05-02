# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — Prometheus: Prometheus__HTTP__Base
# ═══════════════════════════════════════════════════════════════════════════════

import warnings

import requests
from requests.auth                                                                  import HTTPBasicAuth
from urllib3.exceptions                                                             import InsecureRequestWarning

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe


DEFAULT_TIMEOUT = 30


class Prometheus__HTTP__Base(Type_Safe):
    timeout : int  = DEFAULT_TIMEOUT
    verify  : bool = False

    def request(self, method: str, url: str, *,
                      headers : dict  = None,
                      data    : bytes = None,
                      params  : dict  = None,
                      username: str   = '',
                      password: str   = '') -> requests.Response:
        auth = HTTPBasicAuth(username, password) if (username or password) else None
        with warnings.catch_warnings():
            warnings.simplefilter('ignore', InsecureRequestWarning)
            return requests.request(method = method            ,
                                    url    = url               ,
                                    headers= headers or {}     ,
                                    data   = data              ,
                                    params = params            ,
                                    auth   = auth              ,
                                    timeout= self.timeout      ,
                                    verify = self.verify       )
