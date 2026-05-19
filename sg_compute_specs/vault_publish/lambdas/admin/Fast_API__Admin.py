# ═══════════════════════════════════════════════════════════════════════════════
# Admin — Fast_API__Admin
# Browser-side admin surface for vault-publish. Mounted into the existing
# waker FastAPI app at /__admin__/. Same Lambda, two app surfaces (waker for
# slug routing, admin for control plane).
#
# Routes (all under /__admin__/ when mounted):
#   GET  /              → inventory HTML (lists registered slugs)
#   GET  /login         → login form
#   POST /login         → set API-key cookie, redirect to /
#   GET  /logout        → clear cookie, redirect to /login
#   GET  /slug/<slug>/  → per-slug HTML (7-step eval + status)
#   GET  /api/v1/list   → JSON inventory
#   GET  /api/v1/status?slug=X → JSON status (single slug)
#   GET  /api/v1/eval?slug=X   → JSON eval (7 steps)
#
# Auth: API-key cookie or header (see Admin__Auth). Everything except /login
# requires auth. Cookies scoped to .<zone> so a single sign-in carries across
# all <slug>.<zone> + waker.<zone> tabs.
# ═══════════════════════════════════════════════════════════════════════════════

import os
import socket
import time

from fastapi             import FastAPI, Request, Form
from fastapi.responses   import HTMLResponse, RedirectResponse, JSONResponse, Response

from osbot_utils.type_safe.Type_Safe import Type_Safe

from sg_compute_specs.vault_publish.lambdas.admin.Admin__Auth  import (
    Admin__Auth, configured_key_name, is_configured)
from sg_compute_specs.vault_publish.lambdas.admin.Admin__Pages import (
    render_login, render_inventory, render_slug)


def _zone() -> str:
    return os.environ.get('SG_AWS__DNS__DEFAULT_ZONE', 'aws.sg-labs.app')


class Fast_API__Admin(Type_Safe):

    def app(self) -> FastAPI:
        sub = FastAPI(title='SG/Vault Admin', docs_url=None, redoc_url=None, openapi_url=None)
        self._register_routes(sub)
        return sub

    def _register_routes(self, sub: FastAPI):
        auth = Admin__Auth()

        # ── auth middleware ──────────────────────────────────────────────────
        @sub.middleware('http')
        async def _gate(request: Request, call_next):
            # Allow /login (GET, POST) through without auth. Everything else
            # requires the API-key cookie or header. Fail closed: if the
            # Lambda doesn't have the env vars set, all requests redirect to
            # /login with a flash message.
            path = request.url.path
            if path.endswith('/login') or path.endswith('/login/'):
                return await call_next(request)
            if not is_configured():
                return HTMLResponse(render_login(
                    flash      = 'Admin auth is not configured on this Lambda. Set '
                                 'SG_VAULT_PUBLISH__ADMIN__API_KEY_VALUE on the Lambda env '
                                 'and re-deploy — see `sg vp setup lambda status`.',
                    flash_kind = 'error'), status_code=503)
            if not auth.check(headers=dict(request.headers), cookies=dict(request.cookies)):
                return RedirectResponse(url='/__admin__/login', status_code=302)
            return await call_next(request)

        # ── login / logout ──────────────────────────────────────────────────
        @sub.get('/login', response_class=HTMLResponse)
        async def login_get():
            return HTMLResponse(render_login())

        @sub.post('/login')
        async def login_post(api_key: str = Form(...)):
            from sg_compute_specs.vault_publish.lambdas.admin.Admin__Auth import (
                configured_key_value, _consteq)
            expected = configured_key_value()
            if not expected:
                return HTMLResponse(render_login(
                    flash      = 'Admin auth is not configured on this Lambda.',
                    flash_kind = 'error'), status_code=503)
            if not _consteq(api_key, expected):
                return HTMLResponse(render_login(
                    flash      = 'Invalid API key.',
                    flash_kind = 'error'), status_code=401)
            resp = RedirectResponse(url='/__admin__/', status_code=302)
            # Cookie scoped to .<zone> so a single sign-in carries across all
            # subdomains. SameSite=Lax so cross-subdomain top-level navigation
            # carries it; cross-origin XHR with credentials=include also gets
            # it (CORS allow-origin regex permits same-zone subdomains).
            resp.set_cookie(
                key      = configured_key_name(),
                value    = api_key,
                domain   = '.' + _zone(),
                path     = '/',
                secure   = True,
                httponly = False,                                                     # JS in same-origin admin page may want to inspect for debugging
                samesite = 'lax',
                max_age  = 30 * 24 * 3600,                                            # 30 days
            )
            return resp

        @sub.get('/logout')
        async def logout():
            resp = RedirectResponse(url='/__admin__/login', status_code=302)
            resp.delete_cookie(configured_key_name(), domain='.' + _zone(), path='/')
            return resp

        # ── HTML pages ──────────────────────────────────────────────────────
        @sub.get('/', response_class=HTMLResponse)
        async def inventory_html():
            entries = _list_entries()
            return HTMLResponse(render_inventory(entries, _zone()))

        @sub.get('/slug/{slug}/', response_class=HTMLResponse)
        async def slug_html(slug: str):
            status     = _status(slug)
            eval_steps = _eval(slug)
            return HTMLResponse(render_slug(slug, eval_steps, status))

        # ── JSON API ────────────────────────────────────────────────────────
        @sub.get('/api/v1/list')
        async def api_list():
            return JSONResponse({'entries': _list_entries(), 'zone': _zone()})

        @sub.get('/api/v1/status')
        async def api_status(slug: str = ''):
            if not slug:
                return JSONResponse({'error': 'slug query param required'}, status_code=400)
            return JSONResponse(_status(slug))

        @sub.get('/api/v1/eval')
        async def api_eval(slug: str = ''):
            if not slug:
                return JSONResponse({'error': 'slug query param required'}, status_code=400)
            return JSONResponse({'slug': slug, 'steps': _eval(slug)})


# ══════════════════════════════════════════════════════════════════════════════
# Data-access helpers — thin wrappers around the existing services, returning
# plain dicts (the HTML renderers and JSON encoders both consume dicts).
# ══════════════════════════════════════════════════════════════════════════════

def _list_entries() -> list:
    from sg_compute_specs.vault_publish.service.Slug__Registry        import Slug__Registry
    from sg_compute_specs.vault_publish.lambdas.waker.Endpoint__Resolver__EC2 import Endpoint__Resolver__EC2

    registry = Slug__Registry()
    resolver = Endpoint__Resolver__EC2(_registry_factory=lambda: registry)
    out = []
    for slug in registry.list_all():
        entry = registry.get(slug)
        if entry is None:
            continue
        resolution = resolver.resolve(slug)
        out.append({
            'slug'        : str(entry.slug),
            'fqdn'        : str(entry.fqdn),
            'stack_name'  : str(entry.stack_name),
            'region'      : str(entry.region) or str(resolution.region),
            'instance_id' : str(resolution.instance_id),
            'public_ip'   : str(resolution.public_ip),
            'state'       : str(resolution.state),
        })
    return out


def _status(slug: str) -> dict:
    from sg_compute_specs.vault_publish.service.Slug__Registry        import Slug__Registry
    from sg_compute_specs.vault_publish.lambdas.waker.Endpoint__Resolver__EC2 import Endpoint__Resolver__EC2

    entry      = Slug__Registry().get(slug)
    resolution = Endpoint__Resolver__EC2().resolve(slug)
    return {
        'slug'        : slug,
        'fqdn'        : str(entry.fqdn) if entry else '',
        'stack_name'  : str(entry.stack_name) if entry else '',
        'region'      : str(entry.region) if entry else str(resolution.region),
        'instance_id' : str(resolution.instance_id),
        'public_ip'   : str(resolution.public_ip),
        'vault_url'   : str(resolution.vault_url),
        'state'       : str(resolution.state),
    }


def _eval(slug: str) -> list:
    # Mirrors sg vp eval's 7 steps. Each step: {n, label, ok, detail}.
    from sg_compute_specs.vault_publish.service.Slug__Registry        import Slug__Registry
    from sg_compute_specs.vault_publish.lambdas.waker.Endpoint__Resolver__EC2 import Endpoint__Resolver__EC2
    from sg_compute_specs.vault_publish.lambdas.waker.schemas.Enum__Instance__State import Enum__Instance__State
    from sg_compute_specs.vault_publish.lambdas.waker.Waker__Handler          import health_probe

    steps    = []
    fqdn     = f'{slug}.{_zone()}'
    registry = Slug__Registry()

    # 1 — slug registered
    entry = registry.get(slug)
    steps.append({'n': 1, 'label': 'slug registered',
                  'ok'   : entry is not None,
                  'detail': f'tag:sg:slug={slug}' if entry else f'no EC2 tagged sg:slug={slug}'})
    if entry is None:
        return steps

    # 2 — EC2 present
    resolution = Endpoint__Resolver__EC2().resolve(slug)
    iid_state  = (resolution.state != Enum__Instance__State.UNKNOWN)
    steps.append({'n': 2, 'label': 'ec2 instance present',
                  'ok'    : iid_state,
                  'detail': f'{resolution.instance_id} state={resolution.state} ip={resolution.public_ip or "(none)"}'})

    running = (resolution.state == Enum__Instance__State.RUNNING and bool(resolution.public_ip))

    # 3 — direct IP reachable
    if running and resolution.vault_url:
        ok = health_probe(resolution.vault_url, connect_timeout=2, read_timeout=4)
        steps.append({'n': 3, 'label': 'direct IP reachable',
                      'ok' : ok,
                      'detail': f'{resolution.vault_url}/ui/ → {"healthy" if ok else "failed health probe"}'})
    else:
        steps.append({'n': 3, 'label': 'direct IP reachable',
                      'ok': False,
                      'detail': 'skipped — instance not RUNNING with public IP'})

    # 4 — per-slug DNS record (Route 53)
    instance_tls = _instance_has_tls_tag(resolution.instance_id, resolution.region)
    if not instance_tls:
        steps.append({'n': 4, 'label': 'per-slug DNS record',
                      'ok'    : True,
                      'detail': 'skipped — StackTLS=false (record would override CF wildcard)'})
    else:
        try:
            from sgraph_ai_service_playwright__cli.aws.dns.service.Route53__AWS__Client    import Route53__AWS__Client
            from sgraph_ai_service_playwright__cli.aws.dns.enums.Enum__Route53__Record_Type import Enum__Route53__Record_Type
            r53 = Route53__AWS__Client()
            zone_obj = r53.find_hosted_zone_by_name(_zone())
            if zone_obj:
                rec = r53.get_record(str(zone_obj.zone_id), fqdn, Enum__Route53__Record_Type.A)
                if rec:
                    vals = ', '.join(list(rec.values)) if rec.values else (rec.alias_target or '(alias)')
                    steps.append({'n': 4, 'label': 'per-slug DNS record',
                                  'ok' : True, 'detail': f'A {fqdn} → {vals}'})
                else:
                    steps.append({'n': 4, 'label': 'per-slug DNS record',
                                  'ok' : False, 'detail': f'no A record for {fqdn}'})
            else:
                steps.append({'n': 4, 'label': 'per-slug DNS record',
                              'ok' : False, 'detail': f'hosted zone {_zone()!r} not found'})
        except Exception as e:
            steps.append({'n': 4, 'label': 'per-slug DNS record',
                          'ok' : False, 'detail': f'lookup failed: {type(e).__name__}'})

    # 5 — public DNS resolves
    try:
        ips = sorted({a[4][0] for a in socket.getaddrinfo(fqdn, None)})
        steps.append({'n': 5, 'label': 'public DNS resolves',
                      'ok' : True, 'detail': f'{fqdn} → {", ".join(ips[:4])}'})
    except socket.gaierror as e:
        steps.append({'n': 5, 'label': 'public DNS resolves', 'ok': False, 'detail': str(e)})

    # 6 — HTTPS via CloudFront (probe FQDN with cert validation)
    https_url = f'https://{fqdn}/'
    try:
        import urllib3
        t0 = time.time()
        resp = urllib3.PoolManager(timeout=urllib3.Timeout(connect=3, read=5)).request(
            'GET', https_url, preload_content=False, retries=False)
        ms  = int((time.time() - t0) * 1000)
        steps.append({'n': 6, 'label': 'HTTPS via CloudFront',
                      'ok' : resp.status < 500,
                      'detail': f'{https_url} → HTTP {resp.status} in {ms}ms'})
        # 7 — waker headers (only if we got a response with X-Waker-State)
        state_h = resp.headers.get('X-Waker-State', '') if resp.headers else ''
        host_h  = resp.headers.get('X-Waker-Host',  '') if resp.headers else ''
        if state_h:
            host_ok = (host_h == fqdn)
            steps.append({'n': 7, 'label': 'waker headers correct',
                          'ok' : host_ok,
                          'detail': f'state={state_h} host={host_h or "(empty)"}'})
        else:
            steps.append({'n': 7, 'label': 'waker headers correct',
                          'ok' : True,
                          'detail': 'no X-Waker-State — request went direct to EC2 (DNS converged)'})
    except Exception as e:
        steps.append({'n': 6, 'label': 'HTTPS via CloudFront', 'ok': False, 'detail': str(e)[:120]})
        steps.append({'n': 7, 'label': 'waker headers correct', 'ok': False, 'detail': 'skipped — HTTPS probe failed'})

    return steps


def _instance_has_tls_tag(instance_id: str, region: str) -> bool:
    if not instance_id or not region:
        return False
    try:
        import boto3
        ec2 = boto3.client('ec2', region_name=region)
        resp = ec2.describe_instances(InstanceIds=[instance_id])
        for res in resp.get('Reservations', []):
            for inst in res.get('Instances', []):
                for t in inst.get('Tags', []) or []:
                    if t.get('Key') == 'StackTLS':
                        return str(t.get('Value', '')).lower() in ('true', '1', 'yes')
    except Exception:
        return False
    return False
