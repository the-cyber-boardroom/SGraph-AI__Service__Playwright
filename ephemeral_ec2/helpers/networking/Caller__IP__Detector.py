# ═══════════════════════════════════════════════════════════════════════════════
# Ephemeral EC2 — Caller__IP__Detector
# Fetches the caller's public IPv4. Tries all probe URLs in parallel so the
# worst-case wait is one timeout (4 s) rather than N × timeout.
# HTTP is tried first — no TLS cert issues across Python venvs.
# HTTPS probes use a no-verify SSL context (data is non-sensitive: public IP).
# Returns '' on failure — callers must surface a clear error to the user.
# ═══════════════════════════════════════════════════════════════════════════════

import ssl
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

from osbot_utils.type_safe.Type_Safe import Type_Safe


PROBE_URLS = [
    'http://checkip.amazonaws.com',   # plain HTTP first — avoids venv TLS cert issues
    'http://api.ipify.org',
    'https://checkip.amazonaws.com',  # HTTPS fallbacks with no-verify context
    'https://api.ipify.org',
    'https://ifconfig.me/ip',
]
TIMEOUT_PER_URL = 4
_NO_VERIFY_CTX  = ssl.create_default_context()
_NO_VERIFY_CTX.check_hostname = False
_NO_VERIFY_CTX.verify_mode    = ssl.CERT_NONE


class Caller__IP__Detector(Type_Safe):

    def detect(self) -> str:
        def _fetch(url: str) -> str:
            try:
                kw = {'timeout': TIMEOUT_PER_URL}
                if url.startswith('https://'):
                    kw['context'] = _NO_VERIFY_CTX
                with urllib.request.urlopen(url, **kw) as r:
                    ip = r.read().decode().strip()
                    return ip if ip else ''
            except Exception:
                return ''

        with ThreadPoolExecutor(max_workers=len(PROBE_URLS)) as pool:
            futures = {pool.submit(_fetch, url): url for url in PROBE_URLS}
            for future in as_completed(futures):
                ip = future.result()
                if ip:
                    return ip
        return ''
