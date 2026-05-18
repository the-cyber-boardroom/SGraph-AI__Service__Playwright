# ═══════════════════════════════════════════════════════════════════════════════
# Waker — Waker__Handler
# State machine: receives a request context, resolves the slug, and decides
# whether to start the EC2 instance, serve the warming page, or proxy the live
# vault-app.  Returns a response dict suitable for FastAPI Response().
#
# Debug surface (Layer 1 + 2):
#   Every response carries X-Waker-* headers (state, slug, host, instance-id,
#   ec2-state, action, elapsed-ms, request-id, version).  Every invocation
#   emits exactly one JSON line to stdout — Lambda forwards stdout to
#   CloudWatch Logs.
#
# State paths:
#   UNKNOWN slug        → 404 HTML                       (state=not_found, action=returned-404)
#   STOPPED + iid       → start EC2, return 202 warming  (state=warming,   action=started-ec2)
#   PENDING / STOPPING  → return 202 warming             (state=warming,   action=returned-warming)
#   RUNNING + healthy   → proxy                          (state=proxied,   action=proxied)
#   RUNNING + 5xx       → proxy returned 5xx             (state=error,     action=proxy-error)
#   RUNNING + unhealthy → return 200 warming             (state=warming,   action=returned-warming)
# ═══════════════════════════════════════════════════════════════════════════════

import json
import time
from datetime import datetime, timezone
from typing   import Optional, Callable

from osbot_utils.type_safe.Type_Safe import Type_Safe

from sg_compute_specs.vault_publish.waker.Endpoint__Proxy                        import Endpoint__Proxy
from sg_compute_specs.vault_publish.waker.Endpoint__Resolver                     import Endpoint__Resolver
from sg_compute_specs.vault_publish.waker.Endpoint__Resolver__EC2                import Endpoint__Resolver__EC2
from sg_compute_specs.vault_publish.waker.Warming__Page                          import Warming__Page
from sg_compute_specs.vault_publish.waker.schemas.Enum__Instance__State          import Enum__Instance__State
from sg_compute_specs.vault_publish.waker.schemas.Enum__Waker__Action            import Enum__Waker__Action
from sg_compute_specs.vault_publish.waker.schemas.Enum__Waker__State             import Enum__Waker__State
from sg_compute_specs.vault_publish.waker.schemas.Schema__Endpoint__Resolution   import Schema__Endpoint__Resolution
from sg_compute_specs.vault_publish.waker.schemas.Schema__Waker__Request_Context import Schema__Waker__Request_Context

_404_HTML = """\
<!DOCTYPE html><html><head><title>404 Not Found</title></head>
<body><h1>404 — Slug not found</h1><p>No vault registered for this subdomain.</p></body></html>
"""


class Waker__Handler(Type_Safe):

    _resolver_factory : Optional[Callable] = None                                 # Seam — tests inject in-memory resolver
    _proxy_factory    : Optional[Callable] = None                                 # Seam — tests inject in-memory proxy
    _warming_page     : Optional[Warming__Page] = None                            # Seam — tests inject custom page
    _version          : str = ''                                                   # Seam — tests override version string

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
        t0          = time.time()
        slug        = ctx.slug
        empty_res   = Schema__Endpoint__Resolution()

        if not slug:
            result       = self._not_found('no slug in host')
            waker_state  = Enum__Waker__State.NOT_FOUND
            waker_action = Enum__Waker__Action.RETURNED_404
            resolution   = empty_res
        else:
            resolver   = self._resolver()
            resolution = resolver.resolve(slug)
            state      = resolution.state

            if state == Enum__Instance__State.UNKNOWN:
                result       = self._not_found(slug)
                waker_state  = Enum__Waker__State.NOT_FOUND
                waker_action = Enum__Waker__Action.RETURNED_404

            elif state == Enum__Instance__State.STOPPED:
                waker_state = Enum__Waker__State.WARMING
                if resolution.instance_id:
                    resolver.start(resolution.instance_id)
                    waker_action = Enum__Waker__Action.STARTED_EC2
                else:
                    waker_action = Enum__Waker__Action.RETURNED_WARMING
                result = self._warming(slug, 202)

            elif state in (Enum__Instance__State.PENDING, Enum__Instance__State.STOPPING):
                result       = self._warming(slug, 202)
                waker_state  = Enum__Waker__State.WARMING
                waker_action = Enum__Waker__Action.RETURNED_WARMING

            elif state == Enum__Instance__State.RUNNING and resolution.vault_url:
                if self._health_ok(resolution.vault_url):
                    result = self._proxy().proxy(
                        vault_url = resolution.vault_url,
                        method    = ctx.method,
                        path      = ctx.path,
                        headers   = {},
                        body      = ctx.body,
                    )
                    if result['status_code'] >= 500:
                        waker_state  = Enum__Waker__State.ERROR
                        waker_action = Enum__Waker__Action.PROXY_ERROR
                    else:
                        waker_state  = Enum__Waker__State.PROXIED
                        waker_action = Enum__Waker__Action.PROXIED
                else:
                    result       = self._warming(slug, 200)
                    waker_state  = Enum__Waker__State.WARMING
                    waker_action = Enum__Waker__Action.RETURNED_WARMING

            else:
                result       = self._warming(slug, 202)
                waker_state  = Enum__Waker__State.WARMING
                waker_action = Enum__Waker__Action.RETURNED_WARMING

        elapsed_ms = int((time.time() - t0) * 1000)
        _inject_waker_headers(result['headers'], ctx, waker_state, waker_action,
                              resolution, elapsed_ms, self._version)
        _emit_waker_log(ctx, result, waker_state, waker_action, resolution, elapsed_ms,
                        self._version)
        return result

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


# ── helpers ───────────────────────────────────────────────────────────────────

def _inject_waker_headers(headers: dict, ctx: Schema__Waker__Request_Context,
                           waker_state: Enum__Waker__State,
                           waker_action: Enum__Waker__Action,
                           resolution: Schema__Endpoint__Resolution,
                           elapsed_ms: int,
                           version: str) -> None:
    headers['X-Waker-State']      = str(waker_state)
    headers['X-Waker-Slug']       = ctx.slug or ''
    headers['X-Waker-Host']       = ctx.host or ''
    headers['X-Waker-Instance-Id']= resolution.instance_id or ''
    headers['X-Waker-Ec2-State']  = str(resolution.state)
    headers['X-Waker-Action']     = str(waker_action)
    headers['X-Waker-Elapsed-Ms'] = str(elapsed_ms)
    if ctx.request_id:
        headers['X-Waker-Request-Id'] = ctx.request_id
    if version:
        headers['X-Waker-Version'] = version


def _emit_waker_log(ctx: Schema__Waker__Request_Context,
                     result: dict,
                     waker_state: Enum__Waker__State,
                     waker_action: Enum__Waker__Action,
                     resolution: Schema__Endpoint__Resolution,
                     elapsed_ms: int,
                     version: str) -> None:
    now    = datetime.now(timezone.utc)
    record = {
        'ts'         : f'{now.strftime("%Y-%m-%dT%H:%M:%S")}.{now.microsecond // 1000:03d}Z',
        'request_id' : ctx.request_id,
        'host'       : ctx.host,
        'slug'       : ctx.slug,
        'method'     : ctx.method,
        'path'       : ctx.path,
        'source_ip'  : ctx.source_ip,
        'state'      : str(waker_state),
        'action'     : str(waker_action),
        'ec2_state'  : str(resolution.state),
        'instance_id': resolution.instance_id,
        'vault_url'  : resolution.vault_url,
        'status'     : result['status_code'],
        'elapsed_ms' : elapsed_ms,
        'version'    : version,
    }
    print(json.dumps(record))
