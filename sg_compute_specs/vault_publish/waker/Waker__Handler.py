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

import html
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
        if waker_state == Enum__Waker__State.NOT_FOUND:                              # enrich 404 body once all diagnostic info is known
            result['body'] = _render_not_found_html(
                ctx, resolution, waker_state, waker_action, elapsed_ms, self._version
            ).encode()
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
        # 200 OK with a status page — this surface is informational ("the waker
        # is alive, here's what it observed"), not an error. A real 404 framing
        # for unrouted slugs misled operators into thinking the Lambda was
        # broken. Real fatal errors (e.g. upstream proxy 5xx) still return ≥500.
        return {
            'status_code': 200,
            'headers'    : {'Content-Type': 'text/html; charset=utf-8',
                            'Cache-Control': 'no-store'},
            'body'       : b'',                                                       # real body rendered in handle() once all diagnostics are known
        }

    def _health_ok(self, vault_url: str) -> bool:
        import urllib3
        import warnings
        # vault_url is https://{public-ip}/ (TLS on) or http://{public-ip}:8080
        # (TLS off). The LE cert is bound to the FQDN, so any cert validation
        # against the IP would always fail. urllib3 v2 defaults to CERT_REQUIRED;
        # we disable it explicitly here — trust is provided by the AWS-internal
        # ec2:describe_instances lookup that produced this IP.
        try:
            warnings.filterwarnings('ignore', category=urllib3.exceptions.InsecureRequestWarning)
            pool = urllib3.PoolManager(
                cert_reqs       = 'CERT_NONE',
                assert_hostname = False,
                timeout         = urllib3.Timeout(connect=1, read=2),
            )
            resp = pool.request('GET', vault_url.rstrip('/') + '/ui/#!/login',
                                preload_content=True)
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


def _render_not_found_html(ctx: Schema__Waker__Request_Context,
                            resolution: Schema__Endpoint__Resolution,
                            waker_state: Enum__Waker__State,
                            waker_action: Enum__Waker__Action,
                            elapsed_ms: int,
                            version: str) -> str:
    # Vault Waker status page — mirrors the structured log so operators can
    # debug without tailing CloudWatch. Served as 200 OK because the page is
    # informational ("here's what the waker saw"), not an error response.
    # All user-controlled values are HTML-escaped.
    def esc(v) -> str:
        return html.escape(str(v)) if v else '<span class="muted">(none)</span>'

    if not ctx.slug:
        has_viewer_signal = bool(ctx.vault_viewer_host or ctx.forwarded_host)
        if ctx.origin_host and not has_viewer_signal and '.lambda-url.' in ctx.origin_host:
            heading = 'No slug to route'
            reason  = ('Request arrived at the Lambda Function URL directly (or via '
                       'CloudFront without the viewer-Host shim). The waker only routes '
                       'requests whose viewer host matches <code>&lt;slug&gt;.&lt;zone&gt;</code>. '
                       'For CloudFront-fronted requests, ensure '
                       '<code>vault-publish-viewer-host</code> is published and attached — '
                       'run <code>sg vp setup cf-function check</code>.')
        else:
            heading = 'No slug to route'
            reason  = ('The host does not match <code>&lt;slug&gt;.&lt;zone&gt;</code>. '
                       'This is the bare waker landing — there is no specific slug to '
                       'wake. See the diagnostic sections below for the full request.')
    else:
        heading = f'Slug not registered: {html.escape(ctx.slug)}'
        reason  = (f'No vault is registered for slug <code>{html.escape(ctx.slug)}</code>. '
                   f'Register one with <code>sg vp register {html.escape(ctx.slug)} '
                   '--vault-key &lt;key&gt;</code>.')

    now    = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    rows_request = [
        ('Host (viewer)'      , esc(ctx.host)),
        ('Host (origin)'      , esc(ctx.origin_host)),
        ('X-Vault-Viewer-Host', esc(ctx.vault_viewer_host)),
        ('X-Forwarded-Host'   , esc(ctx.forwarded_host)),
        ('Slug'               , esc(ctx.slug)),
        ('Path'               , esc(ctx.path)),
        ('Method'             , esc(ctx.method)),
        ('Source IP'          , esc(ctx.source_ip)),
        ('Request ID'         , esc(ctx.request_id)),
    ]
    rows_waker = [
        ('Waker state'     , esc(waker_state)),
        ('Waker action'    , esc(waker_action)),
        ('EC2 state'       , esc(resolution.state)),
        ('Instance ID'     , esc(resolution.instance_id)),
        ('Vault URL'       , esc(resolution.vault_url)),
        ('Region'          , esc(resolution.region)),
        ('Regions scanned' , esc(resolution.regions_scanned)),
        ('Elapsed'         , f'{elapsed_ms} ms'),
        ('Waker version'   , esc(version)),
        ('Timestamp'       , esc(now)),
    ]

    def render_rows(rows):
        return ''.join(f'<tr><th>{k}</th><td>{v}</td></tr>' for k, v in rows)

    scope_section = ''
    if ctx.asgi_scope:
        scope_section = (
            '<h2>Lambda event meta <span class="muted">'
            '(raw path, source IP, requestContext.*)</span></h2>'
            f'<pre>{html.escape(ctx.asgi_scope)}</pre>'
        )

    deploy_section = ''
    if ctx.deploy_info:
        deploy_section = (
            '<h2>Lambda deployment metadata <span class="muted">'
            '(env vars baked in at deploy time by Setup__Lambda)</span></h2>'
            f'<pre>{html.escape(ctx.deploy_info)}</pre>'
        )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Vault Waker — {heading}</title>
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
         max-width: 820px; margin: 2rem auto; padding: 0 1.5rem; color: #222; }}
  h1   {{ color: #333; font-size: 1.8rem; margin-bottom: 0.5rem; }}
  h1 .badge {{ background: #e8f5e9; color: #2e7d32; font-size: 0.7rem;
               padding: 2px 8px; border-radius: 10px; vertical-align: middle;
               margin-left: 0.5rem; font-weight: normal; }}
  h2   {{ font-size: 1.1rem; margin-top: 1.8rem; color: #555;
         border-bottom: 1px solid #eee; padding-bottom: 0.3rem; }}
  p.reason {{ background: #fff8e1; border-left: 4px solid #ffb300;
              padding: 0.7rem 1rem; border-radius: 3px; }}
  table {{ width: 100%; border-collapse: collapse; margin-top: 0.5rem;
           font-size: 0.92rem; }}
  th, td {{ padding: 0.45rem 0.8rem; border-bottom: 1px solid #eee;
            text-align: left; vertical-align: top; }}
  th {{ background: #f7f7f7; font-weight: 600; width: 160px; color: #333; }}
  code {{ background: #f0f0f0; padding: 1px 5px; border-radius: 3px;
          font-family: SFMono-Regular, Menlo, monospace; font-size: 0.88rem; }}
  pre {{ background: #f7f7f7; padding: 0.8rem 1rem; border-radius: 4px;
         font-family: SFMono-Regular, Menlo, monospace; font-size: 0.82rem;
         overflow-x: auto; border: 1px solid #eee; }}
  .muted {{ color: #999; font-style: italic; }}
  footer {{ margin-top: 2rem; font-size: 0.8rem; color: #888; }}
</style>
</head>
<body>
<h1>Vault Waker <span class="badge">200 OK</span></h1>
<p style="color:#555;margin-top:-0.3rem;">{heading}</p>
<p class="reason">{reason}</p>

<h2>Request</h2>
<table>{render_rows(rows_request)}</table>

<h2>Waker diagnostics</h2>
<table>{render_rows(rows_waker)}</table>
{deploy_section}
{scope_section}
<footer>
  Served by the vault-publish waker Lambda. Same diagnostics are emitted as JSON to CloudWatch
  and as <code>X-Waker-*</code> response headers.
</footer>
</body>
</html>
"""


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
