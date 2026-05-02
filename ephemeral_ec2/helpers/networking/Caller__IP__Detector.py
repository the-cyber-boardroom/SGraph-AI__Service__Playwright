# ═══════════════════════════════════════════════════════════════════════════════
# Ephemeral EC2 — Caller__IP__Detector
# Fetches the caller's public IPv4 from ifconfig.me. Returns '' on failure.
# ═══════════════════════════════════════════════════════════════════════════════

import urllib.request

from osbot_utils.type_safe.Type_Safe import Type_Safe


class Caller__IP__Detector(Type_Safe):

    def detect(self) -> str:
        try:
            with urllib.request.urlopen('https://ifconfig.me/ip', timeout=10) as r:
                return r.read().decode().strip()
        except Exception:
            return ''
