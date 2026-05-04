# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — OpenSearch__HTTP__Base
# Base HTTP request seam for OpenSearch + Dashboards. Single responsibility:
# wraps `requests` with self-signed-TLS handling, basic auth, and a small
# urllib3-warning suppression so per-request `verify=False` does not pollute
# global warning state. Mirrors the seam pattern in Elastic__HTTP__Client but
# kept as its own file (one class per file per CLAUDE.md rule #21) so probe /
# index / bulk operations live in sibling files of their own.
# ═══════════════════════════════════════════════════════════════════════════════

import warnings

import requests
from requests.auth                                                                  import HTTPBasicAuth
from urllib3.exceptions                                                             import InsecureRequestWarning

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe


DEFAULT_TIMEOUT = 30


class OpenSearch__HTTP__Base(Type_Safe):
    timeout : int  = DEFAULT_TIMEOUT
    verify  : bool = False                                                          # Self-signed cert at boot — flip to True once a DNS/Let's-Encrypt design lands

    def request(self, method: str, url: str, *,                                     # Single seam — tests override to script responses
                      headers: dict = None,
                      data   : bytes = None,
                      username: str = '',
                      password: str = '') -> requests.Response:
        auth = HTTPBasicAuth(username, password) if (username or password) else None
        with warnings.catch_warnings():                                             # Silence urllib3 InsecureRequestWarning for our request only — global state untouched
            warnings.simplefilter('ignore', InsecureRequestWarning)
            return requests.request(method = method            ,
                                    url    = url               ,
                                    headers= headers or {}     ,
                                    data   = data              ,
                                    auth   = auth              ,
                                    timeout= self.timeout      ,
                                    verify = self.verify       )
