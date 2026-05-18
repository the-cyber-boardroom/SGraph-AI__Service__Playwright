# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — vault-publish: Cli__Vault_Publish
# Typer app for `sg vp` / `sg vault-publish` commands.
#   register  : publish a vault-app stack under a slug + FQDN
#   unpublish : remove slug, stack, and DNS record
#   status    : show EC2 state + FQDN for a slug
#   list      : list all registered slugs (vault keys redacted)
#   wake      : do what the Lambda does — resolve slug, start EC2 if stopped,
#               wait until running + healthy
#   dns       : DNS diagnostics for a slug (Route 53 record + dig-equivalent)
#   eval      : end-to-end smoke test (every layer: tags / EC2 / DNS / CF / waker)
#   setup     : manage shared AWS resources (ec2 / iam / lambda / cf / cf-function / acm / dns)
#   waker     : inspect and debug the waker Lambda
# ═══════════════════════════════════════════════════════════════════════════════

import sys
import time
from typing import Optional

import typer
from rich.console import Console
from rich.table   import Table

from sg_compute.cli.base.Spec__CLI__Defaults                              import DEFAULT_REGION
from sg_compute_specs.vault_publish.schemas.Safe_Str__Slug                import Safe_Str__Slug
from sg_compute_specs.vault_publish.schemas.Safe_Str__Vault__Key          import Safe_Str__Vault__Key
from sg_compute_specs.vault_publish.schemas.Schema__Vault_Publish__Register__Request import Schema__Vault_Publish__Register__Request
from sg_compute_specs.vault_publish.service.Vault_Publish__Service        import Vault_Publish__Service

app = typer.Typer(name='vault-publish', help='Vault Publish — subdomain-routing for vault-app stacks.', no_args_is_help=True)

from sg_compute_specs.vault_publish.setup.cli.Cli__Setup import app as setup_app
from sg_compute_specs.vault_publish.waker.cli.Cli__Waker import app as waker_app
app.add_typer(setup_app, name='setup')
app.add_typer(waker_app, name='waker')


def _svc() -> Vault_Publish__Service:
    return Vault_Publish__Service().setup()


@app.command(name='register', help='Publish a vault-app stack at <slug>.aws.sg-labs.app.')
def register(slug     : str = typer.Argument(..., help='DNS slug (e.g. sara-cv)'),
             vault_key: str = typer.Option(..., '--vault-key', '-k', help='Vault key identifier'),
             region   : str = typer.Option(DEFAULT_REGION, '--region', '-r')):
    c   = Console(highlight=False)
    req = Schema__Vault_Publish__Register__Request(
        slug      = Safe_Str__Slug(slug),
        vault_key = Safe_Str__Vault__Key(vault_key),
        region    = region)
    c.print(f'\n  [yellow]→[/]  Registering [bold]{slug}[/]…')
    resp = _svc().register(req)
    if not str(getattr(resp, 'fqdn', '')):
        c.print(f'  [red]✗  {resp.message}[/]')
        raise typer.Exit(1)
    c.print(f'  [green]✓[/]  Registered [bold]{slug}[/]')
    c.print(f'      FQDN      : {resp.fqdn}')
    c.print(f'      Stack     : {resp.stack_name}')
    c.print(f'      elapsed   : {resp.elapsed_ms}ms')
    c.print()


@app.command(name='unpublish', help='Remove a slug, its stack, and its DNS record.')
def unpublish(slug  : str  = typer.Argument(..., help='Slug to unpublish'),
              region: str  = typer.Option(DEFAULT_REGION, '--region', '-r'),
              yes   : bool = typer.Option(False, '--yes', '-y', help='Skip confirmation')):
    c = Console(highlight=False)
    if not yes:
        typer.confirm(f"\n  Delete slug '{slug}' and its vault-app stack?", default=True, abort=True)
    c.print(f'\n  [yellow]→[/]  Unpublishing [bold]{slug}[/]…')
    resp = _svc().unpublish(slug)
    if not getattr(resp, 'deleted', False):
        c.print(f'  [red]✗  {resp.message}[/]')
        raise typer.Exit(1)
    c.print(f'  [green]✓[/]  Unpublished [bold]{slug}[/]  (stack: {resp.stack_name})')
    c.print()


@app.command(name='status', help='Show EC2 state and FQDN for a registered slug.')
def status(slug  : str = typer.Argument(..., help='Slug to query'),
           region: str = typer.Option(DEFAULT_REGION, '--region', '-r')):
    c    = Console(highlight=False)
    resp = _svc().status(slug)
    c.print()
    c.print(f'  Slug  : {slug}')
    c.print(f'  State : {resp.state}')
    c.print(f'  FQDN  : {resp.fqdn}')
    if getattr(resp, 'vault_url', ''):
        c.print(f'  URL   : {resp.vault_url}')
    if getattr(resp, 'public_ip', ''):
        c.print(f'  IP    : {resp.public_ip}')
    c.print()


@app.command(name='wake', help='Resolve a slug → start EC2 if stopped → wait for RUNNING + healthy. Mirrors the waker Lambda.')
def wake(slug    : str  = typer.Argument(..., help='Slug to wake'),
         region  : str  = typer.Option(DEFAULT_REGION, '--region', '-r'),
         timeout : int  = typer.Option(120, '--timeout', '-t', help='Max seconds to wait for RUNNING + healthy'),
         no_wait : bool = typer.Option(False, '--no-wait', help='Trigger start_instances but exit immediately'),
         no_probe: bool = typer.Option(False, '--no-probe', help='Skip HTTP health probe after RUNNING')):
    from sg_compute_specs.vault_publish.service.Slug__Registry              import Slug__Registry
    from sg_compute_specs.vault_publish.waker.Endpoint__Resolver__EC2       import Endpoint__Resolver__EC2
    from sg_compute_specs.vault_publish.waker.schemas.Enum__Instance__State import Enum__Instance__State

    c        = Console(highlight=False)
    registry = Slug__Registry(region=region)
    resolver = Endpoint__Resolver__EC2(_registry_factory=lambda: registry)

    c.print(f'\n  [yellow]→[/]  Resolving [bold]{slug}[/]…')
    resolution = resolver.resolve(slug)
    if resolution.state == Enum__Instance__State.UNKNOWN:
        c.print(f'  [red]✗  no EC2 instance tagged sg:slug={slug} in {region}[/]')
        c.print(f'  [dim]   Register first: sg vp register {slug} --vault-key <key>[/]\n')
        raise typer.Exit(1)

    c.print(f'  [dim]  instance: {resolution.instance_id}  state: {resolution.state}  ip: {resolution.public_ip or "(none)"}[/]')

    started_now = False
    if resolution.state == Enum__Instance__State.STOPPED:
        c.print(f'  [yellow]→[/]  Instance STOPPED — calling start_instances…')
        ok = resolver.start(resolution.instance_id)
        if not ok:
            c.print(f'  [red]✗  start_instances failed (check IAM / region)[/]\n')
            raise typer.Exit(1)
        started_now = True
        c.print(f'  [green]✓[/]  start triggered')
        if no_wait:
            c.print(f'\n  [dim]--no-wait: returning before EC2 is ready[/]\n')
            return
    elif resolution.state in (Enum__Instance__State.PENDING, Enum__Instance__State.STOPPING):
        c.print(f'  [yellow]→[/]  Instance {resolution.state} — waiting for stable state…')
    elif resolution.state == Enum__Instance__State.RUNNING:
        c.print(f'  [green]✓[/]  Instance already RUNNING')

    if no_wait:
        c.print()
        return

    # ── Wait for RUNNING ─────────────────────────────────────────────────────
    t0 = time.time()
    last_state = resolution.state
    while True:
        elapsed = time.time() - t0
        if elapsed > timeout:
            c.print(f'  [red]✗  timed out after {timeout}s (last state: {last_state})[/]\n')
            raise typer.Exit(1)
        resolution = resolver.resolve(slug)
        if resolution.state != last_state:
            c.print(f'  [dim]  {int(elapsed)}s: state {last_state} → {resolution.state}[/]')
            last_state = resolution.state
        if resolution.state == Enum__Instance__State.RUNNING and resolution.public_ip:
            break
        time.sleep(2)

    wake_ms = int((time.time() - t0) * 1000)
    c.print(f'  [green]✓[/]  RUNNING at {resolution.public_ip}  ({wake_ms}ms wait)')

    if no_probe:
        c.print()
        return

    # ── HTTP health probe (vault-app default port 8080) ──────────────────────
    c.print(f'  [yellow]→[/]  Probing {resolution.vault_url}/ui/#!/login…')
    try:
        import urllib3
        p0   = time.time()
        resp = urllib3.PoolManager(timeout=urllib3.Timeout(connect=2, read=5)).request(
            'GET', resolution.vault_url.rstrip('/') + '/ui/#!/login', preload_content=True)
        probe_ms = int((time.time() - p0) * 1000)
        if resp.status < 500:
            c.print(f'  [green]✓[/]  HTTP {resp.status} in {probe_ms}ms  → vault-app reachable')
        else:
            c.print(f'  [yellow]⚠[/]  HTTP {resp.status} in {probe_ms}ms  → still warming?')
    except Exception as exc:
        c.print(f'  [yellow]⚠[/]  probe failed: {exc}')
        c.print(f'  [dim]  (TCP listener may not yet be up — vault-app boot takes 30–90s after RUNNING)[/]')
    c.print()


@app.command(name='dns', help='DNS diagnostics for a slug (Route 53 record + public resolver lookup).')
def dns(slug  : str = typer.Argument(..., help='Slug to inspect'),
        zone  : str = typer.Option('', '--zone', '-z', help='DNS apex (defaults to $SG_AWS__DNS__DEFAULT_ZONE)')):
    import os
    from sg_compute_specs.vault_publish.service.Slug__Registry import Slug__Registry

    c             = Console(highlight=False)
    resolved_zone = zone or os.environ.get('SG_AWS__DNS__DEFAULT_ZONE', 'aws.sg-labs.app')
    fqdn          = f'{slug}.{resolved_zone}'
    registry      = Slug__Registry()
    entry         = registry.get(slug)

    c.print()
    c.print(f'  Slug : [bold]{slug}[/]')
    c.print(f'  FQDN : {fqdn}')
    c.print(f'  Zone : {resolved_zone}')
    c.print()

    # ── Registry view (tag-derived) ──────────────────────────────────────────
    if entry:
        c.print(f'  [green]✓[/]  Registry: instance tagged sg:slug={slug}  fqdn={entry.fqdn}')
    else:
        c.print(f'  [yellow]⚠[/]  Registry: no EC2 instance tagged sg:slug={slug}')

    # ── Route 53 lookup ──────────────────────────────────────────────────────
    try:
        from sgraph_ai_service_playwright__cli.aws.dns.service.Route53__AWS__Client      import Route53__AWS__Client
        from sgraph_ai_service_playwright__cli.aws.dns.enums.Enum__Route53__Record_Type   import Enum__Route53__Record_Type
        r53      = Route53__AWS__Client()
        zone_obj = r53.find_hosted_zone_by_name(resolved_zone)
        if not zone_obj:
            c.print(f'  [yellow]⚠[/]  Route 53: hosted zone {resolved_zone!r} not found')
        else:
            # Per-slug record (set by Vault_App__Auto_DNS when register was called with TLS)
            rec_a = r53.get_record(str(zone_obj.zone_id), fqdn, Enum__Route53__Record_Type.A)
            if rec_a:
                vals = ', '.join(list(rec_a.values)) if rec_a.values else (rec_a.alias_target or '(alias)')
                c.print(f'  [green]✓[/]  Route 53 A record : {fqdn} → {vals}  (ttl={rec_a.ttl})')
            else:
                c.print(f'  [dim]ℹ[/]   Route 53 A record : (none — relying on wildcard *.{resolved_zone})')

            # Wildcard at *.{zone} that catches everything for the CF distribution
            wild = f'*.{resolved_zone}'
            for rt in (Enum__Route53__Record_Type.A, Enum__Route53__Record_Type.CNAME):
                rec_w = r53.get_record(str(zone_obj.zone_id), wild, rt)
                if rec_w:
                    vals = ', '.join(list(rec_w.values)) if rec_w.values else (rec_w.alias_target or '(alias)')
                    c.print(f'  [green]✓[/]  Wildcard {rt.value:5}    : {wild} → {vals}')
                    break
            else:
                c.print(f'  [red]✗  Wildcard         : no {wild} record (CF fallback broken)[/]')
    except Exception as exc:
        c.print(f'  [red]✗  Route 53 lookup failed: {exc}[/]')

    # ── Public resolver lookup (cheap sanity check) ──────────────────────────
    import socket
    try:
        ips = sorted({addr[4][0] for addr in socket.getaddrinfo(fqdn, None)})
        c.print(f'  [green]✓[/]  Public DNS resolves to: {", ".join(ips)}')
    except socket.gaierror as exc:
        c.print(f'  [red]✗  Public DNS resolution failed: {exc}[/]')
    c.print()


@app.command(name='eval', help='End-to-end smoke test: every layer between registration and viewer-served HTML.')
def eval_(slug    : str  = typer.Argument(..., help='Slug to evaluate'),
          region  : str  = typer.Option(DEFAULT_REGION, '--region', '-r'),
          zone    : str  = typer.Option('', '--zone', '-z', help='DNS apex (defaults to $SG_AWS__DNS__DEFAULT_ZONE)'),
          no_wake : bool = typer.Option(False, '--no-wake', help='Skip start-if-stopped step (probe in-place state only)')):
    import os, socket, time as _t
    from sg_compute_specs.vault_publish.service.Slug__Registry              import Slug__Registry
    from sg_compute_specs.vault_publish.waker.Endpoint__Resolver__EC2       import Endpoint__Resolver__EC2
    from sg_compute_specs.vault_publish.waker.schemas.Enum__Instance__State import Enum__Instance__State

    c             = Console(highlight=False)
    resolved_zone = zone or os.environ.get('SG_AWS__DNS__DEFAULT_ZONE', 'aws.sg-labs.app')
    fqdn          = f'{slug}.{resolved_zone}'
    registry      = Slug__Registry(region=region)
    resolver      = Endpoint__Resolver__EC2(_registry_factory=lambda: registry)
    failures      = 0

    c.print(f'\n  [bold]Evaluating[/] [cyan]{fqdn}[/]\n')

    # 1 — Slug registered (tag lookup)
    entry = registry.get(slug)
    if entry:
        _step(c, 1, 'slug registered', True, f'instance tagged sg:slug={slug}')
    else:
        _step(c, 1, 'slug registered', False, f'no EC2 tagged sg:slug={slug} in {region}')
        failures += 1
        c.print()
        raise typer.Exit(failures)

    # 2 — EC2 present + state
    resolution = resolver.resolve(slug)
    ok = resolution.state != Enum__Instance__State.UNKNOWN
    _step(c, 2, 'ec2 instance present', ok,
          f'{resolution.instance_id} state={resolution.state} ip={resolution.public_ip or "(none)"}')
    failures += 0 if ok else 1

    # 2b — Optional wake
    if not no_wake and resolution.state == Enum__Instance__State.STOPPED:
        c.print('     [dim]→ STOPPED — calling start_instances and waiting up to 120s…[/]')
        resolver.start(resolution.instance_id)
        deadline = _t.time() + 120
        while _t.time() < deadline:
            resolution = resolver.resolve(slug)
            if resolution.state == Enum__Instance__State.RUNNING and resolution.public_ip:
                break
            _t.sleep(2)

    running = (resolution.state == Enum__Instance__State.RUNNING and bool(resolution.public_ip))

    # 3 — Direct IP HTTP probe
    if running and resolution.vault_url:
        ok, detail = _http_probe(resolution.vault_url.rstrip('/') + '/ui/#!/login')
        _step(c, 3, 'direct IP reachable', ok, f'{resolution.vault_url} → {detail}')
        failures += 0 if ok else 1
    else:
        _step(c, 3, 'direct IP reachable', False, 'skipped — instance not RUNNING with public IP')
        failures += 1

    # 4 — Per-slug Route 53 A record (set by Vault_App__Auto_DNS on register)
    r53_per_slug_ok = False
    try:
        from sgraph_ai_service_playwright__cli.aws.dns.service.Route53__AWS__Client    import Route53__AWS__Client
        from sgraph_ai_service_playwright__cli.aws.dns.enums.Enum__Route53__Record_Type import Enum__Route53__Record_Type
        r53      = Route53__AWS__Client()
        zone_obj = r53.find_hosted_zone_by_name(resolved_zone)
        if zone_obj:
            rec = r53.get_record(str(zone_obj.zone_id), fqdn, Enum__Route53__Record_Type.A)
            if rec:
                vals = ', '.join(list(rec.values)) if rec.values else (rec.alias_target or '(alias)')
                _step(c, 4, 'per-slug DNS record', True, f'A {fqdn} → {vals}')
                r53_per_slug_ok = True
            else:
                _step(c, 4, 'per-slug DNS record', False,
                      f'no A record for {fqdn} — register may not have run with TLS, or DNS was deleted')
                failures += 1
        else:
            _step(c, 4, 'per-slug DNS record', False, f'hosted zone {resolved_zone!r} not found')
            failures += 1
    except Exception as exc:
        _step(c, 4, 'per-slug DNS record', False, f'Route 53 lookup failed: {exc}')
        failures += 1

    # 5 — Public DNS resolution
    try:
        ips = sorted({addr[4][0] for addr in socket.getaddrinfo(fqdn, None)})
        _step(c, 5, 'public DNS resolves', True, f'{fqdn} → {", ".join(ips[:4])}')
    except socket.gaierror as exc:
        _step(c, 5, 'public DNS resolves', False, str(exc))
        failures += 1

    # 6 — HTTPS through CloudFront → waker → vault-app
    https_url = f'https://{fqdn}/'
    ok, detail, waker_headers = _https_probe(https_url)
    _step(c, 6, 'HTTPS via CloudFront', ok, f'{https_url} → {detail}')
    failures += 0 if ok else 1

    # 7 — Waker X-Waker-* response headers
    if waker_headers:
        state_h  = waker_headers.get('X-Waker-State', '')
        action_h = waker_headers.get('X-Waker-Action', '')
        host_h   = waker_headers.get('X-Waker-Host', '')
        host_ok  = (host_h == fqdn) if host_h else False
        ok       = bool(state_h) and host_ok
        _step(c, 7, 'waker headers correct', ok,
              f'state={state_h} action={action_h} host={host_h or "(empty)"}'
              + ('' if host_ok else '  [yellow]← host mismatch (CloudFront Function missing?)[/]'))
        failures += 0 if ok else 1
    else:
        _step(c, 7, 'waker headers correct', False, 'no X-Waker-* headers received')
        failures += 1

    c.print()
    if failures:
        c.print(f'  [red]✗  {failures} step(s) failed[/]\n')
        raise typer.Exit(1)
    c.print(f'  [green]✓  all {7} steps passed[/]\n')


def _step(c: Console, n: int, label: str, ok: bool, detail: str = '') -> None:
    icon = '[green]✓[/]' if ok else '[red]✗[/]'
    c.print(f'  {n}. {icon}  {label:<24} {detail}')


def _http_probe(url: str) -> tuple:
    try:
        import urllib3
        t0   = time.time()
        resp = urllib3.PoolManager(timeout=urllib3.Timeout(connect=2, read=5)).request(
            'GET', url, preload_content=True)
        ms   = int((time.time() - t0) * 1000)
        return (resp.status < 500, f'HTTP {resp.status} in {ms}ms')
    except Exception as exc:
        return (False, f'request failed: {exc}')


def _https_probe(url: str) -> tuple:
    try:
        import urllib3
        t0   = time.time()
        resp = urllib3.PoolManager(timeout=urllib3.Timeout(connect=5, read=15)).request(
            'GET', url, preload_content=True, retries=False)
        ms   = int((time.time() - t0) * 1000)
        # Filter just X-Waker-* headers
        waker_headers = {k: v for k, v in resp.headers.items() if k.lower().startswith('x-waker-')}
        ok = resp.status < 500
        return (ok, f'HTTP {resp.status} in {ms}ms', waker_headers)
    except Exception as exc:
        return (False, f'request failed: {exc}', {})


@app.command(name='list', help='List all registered slugs (vault keys redacted).')
def list_slugs():
    c    = Console(highlight=False)
    resp = _svc().list_slugs()
    if not resp.total:
        c.print('\n  (no slugs registered)\n')
        return
    tbl = Table(box=None, show_header=True, padding=(0, 2))
    tbl.add_column('Slug',       style='bold')
    tbl.add_column('FQDN',       style='cyan')
    tbl.add_column('Stack',      style='dim')
    tbl.add_column('Region',     style='dim')
    tbl.add_column('Created',    style='dim')
    for entry in resp.entries:
        tbl.add_row(str(entry.slug), str(entry.fqdn), str(entry.stack_name),
                    str(entry.region), str(entry.created_at))
    c.print()
    c.print(tbl)
    c.print(f'\n  Total: {resp.total}\n')


