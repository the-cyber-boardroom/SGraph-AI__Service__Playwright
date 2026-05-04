# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Firefox__HTTP__Base
# Base HTTP request seam for sp firefox. Wraps requests with verify=False
# (the Firefox noVNC container uses a self-signed cert on port 5800).
# ═══════════════════════════════════════════════════════════════════════════════

import warnings

import requests
from urllib3.exceptions                                                             import InsecureRequestWarning

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe


DEFAULT_TIMEOUT = 10


class Firefox__HTTP__Base(Type_Safe):
    timeout : int  = DEFAULT_TIMEOUT
    verify  : bool = False                                                          # self-signed cert on port 5800

    def request(self, method: str, url: str) -> requests.Response:                 # Single seam — tests override
        with warnings.catch_warnings():
            warnings.simplefilter('ignore', InsecureRequestWarning)
            return requests.request(method  = method        ,
                                    url     = url           ,
                                    timeout = self.timeout  ,
                                    verify  = self.verify   )
