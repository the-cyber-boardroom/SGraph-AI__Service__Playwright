# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Firefox__HTTP__Probe
# Read-only HTTP probes against a live Firefox stack.
#
# Two probes:
#   firefox_ready(public_ip)  — GET https://<ip>:5800/ (self-signed cert)
#                               Any HTTP response means the container is up
#                               and serving (even 401 / 302 counts as alive).
#   mitmweb_ready(public_ip)  — GET http://<ip>:8081/
#                               mitmweb root returns 200 when ready.
#
# Both return False on any connection error / timeout.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe

from sgraph_ai_service_playwright__cli.firefox.service.Firefox__HTTP__Base          import Firefox__HTTP__Base

VIEWER_PORT  = 5800
MITMWEB_PORT = 8081


class Firefox__HTTP__Probe(Type_Safe):
    http : Firefox__HTTP__Base                                                      # Composed; tests override http.request

    def firefox_ready(self, public_ip: str) -> bool:                               # True iff port 5800 returns any HTTP response
        try:
            resp = self.http.request('GET', f'https://{public_ip}:{VIEWER_PORT}/')
            return resp.status_code > 0
        except Exception:
            return False

    def mitmweb_ready(self, public_ip: str) -> bool:                               # True iff mitmweb returns any HTTP response on port 8081
        try:
            resp = self.http.request('GET', f'http://{public_ip}:{MITMWEB_PORT}/')
            return resp.status_code > 0
        except Exception:
            return False
