# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Vnc__HTTP__Probe
# Read-only probes against a live VNC stack. Single responsibility: probes
# that populate Schema__Vnc__Health + the future `sp vnc flows` command.
#
# Three probes:
#   - caddy_ready(base_url)       — GET /healthz   → bool  (Caddy gate alive)
#   - mitmweb_ready(base_url)     — GET /healthz   → bool  (same gate; mitmweb
#                                    behind the gate so we trust the compose
#                                    healthcheck — see note below)
#   - flows_listing(base_url, ...)— GET /mitmweb/flows w/ creds → list
#
# When Caddy is the front door, every protected path returns 302 → /login
# without a JWT cookie, so /  is no longer a useful liveness probe. /healthz
# is configured in the Caddyfile to return 200 unauthenticated specifically
# for this purpose.
#
# The historical method names `nginx_ready` / `mitmweb_ready` are kept on
# the class for caller compatibility (Vnc__Service.health, tests). They
# now both probe /healthz; the names just describe what's true when each
# returns True ("Caddy front door alive" — yes, "mitmweb is reachable
# through it" — implied by the compose lifecycle).
#
# All probes return False / [] / {} on any failure; caller maps to
# Schema__Vnc__Health '-1' sentinel for flow_count when listing fails.
# ═══════════════════════════════════════════════════════════════════════════════

import json

from typing                                                                         import List

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe

from sgraph_ai_service_playwright__cli.vnc.service.Vnc__HTTP__Base                  import Vnc__HTTP__Base


HEALTHZ_PATH       = '/healthz'                                                     # Unauthenticated 200 endpoint defined in Vnc__Caddy__Template.CADDYFILE_TEMPLATE
MITMWEB_FLOWS_PATH = '/mitmweb/flows'                                               # Behind Caddy auth gate — flows_listing must include a valid JWT cookie (or session cookie); see Vnc__HTTP__Base for the cookie seam (deferred wiring — see v0.1.118 caddy slice followup)


class Vnc__HTTP__Probe(Type_Safe):
    http : Vnc__HTTP__Base                                                          # Composed; tests override http.request

    def nginx_ready(self, base_url: str, username: str = '', password: str = '') -> bool:    # True iff Caddy front door returns 2xx on /healthz
        url = f'{base_url.rstrip("/")}{HEALTHZ_PATH}'
        try:
            resp = self.http.request('GET', url, username=username, password=password)
        except Exception:
            return False
        return 200 <= resp.status_code < 300

    def mitmweb_ready(self, base_url: str, username: str = '', password: str = '') -> bool:  # Same /healthz endpoint — mitmweb is reachable iff Caddy is up and the compose lifecycle started both
        return self.nginx_ready(base_url, username=username, password=password)

    def flows_listing(self, base_url: str, username: str = '', password: str = '') -> List[dict]:  # Parsed flow listing; empty list on any failure (incl. Caddy 302 to /login when no JWT)
        url = f'{base_url.rstrip("/")}{MITMWEB_FLOWS_PATH}'
        try:
            resp = self.http.request('GET', url, username=username, password=password)
        except Exception:
            return []
        if resp.status_code != 200:
            return []
        try:
            body = resp.json()
        except (json.JSONDecodeError, ValueError):
            return []
        return body if isinstance(body, list) else []                               # mitmweb returns a top-level array; defensive
