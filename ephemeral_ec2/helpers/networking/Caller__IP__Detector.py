# ═══════════════════════════════════════════════════════════════════════════════
# Ephemeral EC2 — Caller__IP__Detector
# Fetches the caller's public IPv4. Tries all probe URLs in parallel so the
# worst-case wait is one timeout (4 s) rather than N × timeout (was 24 s).
# Returns '' on failure — callers should surface a clear error to the user.
# ═══════════════════════════════════════════════════════════════════════════════

import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

from osbot_utils.type_safe.Type_Safe import Type_Safe


PROBE_URLS = [
    'https://checkip.amazonaws.com',
    'https://api.ipify.org',
    'https://ifconfig.me/ip',
]
TIMEOUT_PER_URL = 4


class Caller__IP__Detector(Type_Safe):

    def detect(self) -> str:
        def _fetch(url: str) -> str:
            try:
                with urllib.request.urlopen(url, timeout=TIMEOUT_PER_URL) as r:
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
