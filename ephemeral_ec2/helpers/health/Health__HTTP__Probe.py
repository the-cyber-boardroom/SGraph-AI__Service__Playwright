# ═══════════════════════════════════════════════════════════════════════════════
# Ephemeral EC2 — Health__HTTP__Probe
# Single HTTP GET. Returns True on any 2xx/3xx response.
# Uses stdlib urllib so no extra dependencies.
# ═══════════════════════════════════════════════════════════════════════════════

import ssl
import urllib.request

from osbot_utils.type_safe.Type_Safe import Type_Safe


class Health__HTTP__Probe(Type_Safe):

    def check(self, url: str, timeout_sec: int = 10) -> bool:
        try:
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode    = ssl.CERT_NONE
            req = urllib.request.Request(url, headers={'User-Agent': 'ephemeral-ec2-health'})
            with urllib.request.urlopen(req, timeout=timeout_sec, context=ctx) as resp:
                return resp.status < 400
        except Exception:
            return False
