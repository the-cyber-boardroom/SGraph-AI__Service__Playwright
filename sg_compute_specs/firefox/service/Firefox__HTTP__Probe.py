# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — Firefox: Firefox__HTTP__Probe
# Read-only HTTP probes against a live Firefox stack.
#   firefox_ready — GET https://<ip>:5800/ (any HTTP response = alive)
#   mitmweb_ready — GET http://<ip>:8081/  (200 = ready)
# ═══════════════════════════════════════════════════════════════════════════════

import urllib.request
import ssl

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe


VIEWER_CONTAINER_PORT = 5800
MITMWEB_PORT          = 8081


class Firefox__HTTP__Probe(Type_Safe):

    def firefox_ready(self, public_ip: str, timeout: int = 5) -> bool:
        try:
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode    = ssl.CERT_NONE
            req = urllib.request.urlopen(
                f'https://{public_ip}:{VIEWER_CONTAINER_PORT}/', timeout=timeout, context=ctx)
            return req.status > 0
        except Exception:
            return False

    def mitmweb_ready(self, public_ip: str, timeout: int = 5) -> bool:
        try:
            req = urllib.request.urlopen(f'http://{public_ip}:{MITMWEB_PORT}/', timeout=timeout)
            return req.status > 0
        except Exception:
            return False
