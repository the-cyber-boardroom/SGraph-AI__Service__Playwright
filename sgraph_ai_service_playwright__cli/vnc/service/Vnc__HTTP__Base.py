# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Vnc__HTTP__Base
# Base HTTP request seam for sp vnc. Wraps `requests` with `verify=False`
# default (the nginx terminator at port 443 uses a self-signed cert at boot)
# + scoped urllib3 InsecureRequestWarning suppression + Basic auth seam
# (operator credentials front both the chromium-VNC UI and mitmweb).
#
# Same shape as the OS / Prom HTTP base — kept as its own file so the
# probes stay small and reviewable.
# ═══════════════════════════════════════════════════════════════════════════════

import warnings

import requests
from requests.auth                                                                  import HTTPBasicAuth
from urllib3.exceptions                                                             import InsecureRequestWarning

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe


DEFAULT_TIMEOUT = 30


class Vnc__HTTP__Base(Type_Safe):
    timeout : int  = DEFAULT_TIMEOUT
    verify  : bool = False                                                          # nginx self-signed cert at boot

    def request(self, method: str, url: str, *,                                     # Single seam — tests override
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
