# ═══════════════════════════════════════════════════════════════════════════════
# Waker — Waker__Handler
# State machine: receives a request context, resolves the slug, and decides
# whether to start the EC2 instance, serve the warming page, or proxy the live
# vault-app. Returns a response dict suitable for FastAPI Response().
#
# State paths:
#   UNKNOWN slug        → 404 HTML
#   STOPPED             → start EC2, return 202 warming page
#   PENDING / STOPPING  → return 202 warming page (already starting/warm)
#   RUNNING             → health-check; if healthy → proxy, else → 200 warming
# ═══════════════════════════════════════════════════════════════════════════════

from typing import Optional, Callable

from osbot_utils.type_safe.Type_Safe import Type_Safe

from sg_compute_specs.vault_publish.waker.Endpoint__Proxy                      import Endpoint__Proxy
from sg_compute_specs.vault_publish.waker.Endpoint__Resolver                   import Endpoint__Resolver
from sg_compute_specs.vault_publish.waker.Endpoint__Resolver__EC2              import Endpoint__Resolver__EC2
from sg_compute_specs.vault_publish.waker.Warming__Page                        import Warming__Page
from sg_compute_specs.vault_publish.waker.schemas.Enum__Instance__State        import Enum__Instance__State
from sg_compute_specs.vault_publish.waker.schemas.Schema__Waker__Request_Context import Schema__Waker__Request_Context

_404_HTML = """\
<!DOCTYPE html><html><head><title>404 Not Found</title></head>
<body><h1>404 — Slug not found</h1><p>No vault registered for this subdomain.</p></body></html>
"""


class Waker__Handler(Type_Safe):

    _resolver_factory : Optional[Callable] = None                                 # Seam — tests inject in-memory resolver
    _proxy_factory    : Optional[Callable] = None                                 # Seam — tests inject in-memory proxy
    _warming_page     : Optional[Warming__Page] = None                            # Seam — tests inject custom page

    def _resolver(self) -> Endpoint__Resolver:
        if self._resolver_factory:
            return self._resolver_factory()
        return Endpoint__Resolver__EC2()

    def _proxy(self) -> Endpoint__Proxy:
        if self._proxy_factory:
            return self._proxy_factory()
        return Endpoint__Proxy()

    def _page(self) -> Warming__Page:
        return self._warming_page or Warming__Page()

    def handle(self, ctx: Schema__Waker__Request_Context) -> dict:
        slug = ctx.slug
        if not slug:
            return self._not_found('no slug in host')
        resolution = self._resolver().resolve(slug)
        state      = resolution.state
        if state == Enum__Instance__State.UNKNOWN:
            return self._not_found(slug)
        if state == Enum__Instance__State.STOPPED:
            if resolution.instance_id:
                self._resolver().start(resolution.instance_id)
            return self._warming(slug, 202)
        if state in (Enum__Instance__State.PENDING, Enum__Instance__State.STOPPING):
            return self._warming(slug, 202)
        if state == Enum__Instance__State.RUNNING and resolution.vault_url:
            if self._health_ok(resolution.vault_url):
                return self._proxy().proxy(
                    vault_url = resolution.vault_url,
                    method    = ctx.method,
                    path      = ctx.path,
                    headers   = {},
                    body      = ctx.body,
                )
            return self._warming(slug, 200)
        return self._warming(slug, 202)

    def _warming(self, slug: str, status: int) -> dict:
        page = self._page()
        return {
            'status_code': status,
            'headers'    : page.headers(),
            'body'       : page.render(slug).encode(),
        }

    def _not_found(self, slug: str) -> dict:
        return {
            'status_code': 404,
            'headers'    : {'Content-Type': 'text/html; charset=utf-8',
                            'Cache-Control': 'no-store'},
            'body'       : _404_HTML.encode(),
        }

    def _health_ok(self, vault_url: str) -> bool:
        import urllib3
        try:
            resp = urllib3.PoolManager(timeout=urllib3.Timeout(connect=1, read=2)).request(
                'GET', vault_url.rstrip('/') + '/ui/#!/login',
                preload_content=True,
            )
            return resp.status < 500
        except Exception:
            return False
