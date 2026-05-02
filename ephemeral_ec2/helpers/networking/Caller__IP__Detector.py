# ═══════════════════════════════════════════════════════════════════════════════
# Ephemeral EC2 — Caller__IP__Detector
# Fetches the caller's public IPv4 from ifconfig.me. Returns '' on failure.
# ═══════════════════════════════════════════════════════════════════════════════

import urllib.request

from osbot_utils.type_safe.Type_Safe import Type_Safe


PROBE_URLS = [
    'https://ifconfig.me/ip',
    'https://api.ipify.org',
    'https://checkip.amazonaws.com',
]


class Caller__IP__Detector(Type_Safe):

    def detect(self) -> str:
        for url in PROBE_URLS:
            try:
                with urllib.request.urlopen(url, timeout=8) as r:
                    ip = r.read().decode().strip()
                    if ip:
                        return ip
            except Exception:
                continue
        return ''
