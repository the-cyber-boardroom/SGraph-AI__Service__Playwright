# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — sg_edge local: Cli__SG_Edge__Local
# Typer app for `sg edge local` — the Phase-1 local deployment (no AWS, no docker).
#
#   setup                 bring the local edge up (zone + wildcard + one proxy)
#   register <slug>       register a slug (A + backend TXT) — replicates Vault Waker
#   unregister <slug>     remove a slug
#   request <slug>        simulate a user request end-to-end → welcome / 404 / dormant
#   list                  list registered slugs
#   status                snapshot (proxy fleet, slugs, counter)
#   check                 rich ASCII diagnostics — what's deployed + any deviations
#   serve                 run the local proxy as a real HTTP server (browser/curl)
#   teardown              destroy the local edge
#   usecases              list scripted end-to-end use-cases
#   usecase <id|all>      run one (or all) use-case(s) one by one
#
# Commands have no logic — they call Local__Edge__Stack / Local__Edge__Usecases and
# render with rich.Console. State lives in $SG_EDGE__LOCAL_STATE_DIR (~/.sg/edge_local).
# ═══════════════════════════════════════════════════════════════════════════════

import json

import typer
from rich.console import Console

app = typer.Typer(name='local', help='SG/Edge local deployment (setup / usage / teardown — no AWS).', no_args_is_help=True)

_stack_factory = None                                                                # tests assign a callable → Local__Edge__Stack


def _stack(parent: str = ''):
    if _stack_factory is not None:
        return _stack_factory(parent)
    from sg_compute_specs.sg_edge.local.Local__Edge__Stack       import Local__Edge__Stack
    from sg_compute_specs.sg_edge.local.sg_edge_local__config     import SG_EDGE__LOCAL_PARENT
    return Local__Edge__Stack(parent=parent or SG_EDGE__LOCAL_PARENT)


# ── lifecycle ─────────────────────────────────────────────────────────────────

@app.command(name='setup', help='Bring the local edge up: DNS zone + wildcard + one proxy in the fleet.')
def setup(parent: str = typer.Option('', '--parent', '-p', help='Local edge zone (default edge.sg-labs.local)')):
    c = Console(highlight=False)
    st = _stack(parent).setup()
    c.print(f'\n  [green]✓[/]  local edge deployed  parent=[cyan]{st.parent}[/]')
    c.print(f'  [dim]   wildcard *.{st.parent} → {", ".join(st.proxy_ips) or "(none)"}  |  '
            f'proxies: {len(st.proxy_ips)}[/]')
    c.print(f'  [dim]   next: sg edge local register <slug>  →  sg edge local request <slug>[/]\n')


@app.command(name='register', help='Register a slug (A + backend TXT) — replicates the Vault Waker.')
def register(slug      : str  = typer.Argument(..., help='Slug to register'),
             parent    : str  = typer.Option('', '--parent', '-p'),
             no_backend: bool = typer.Option(False, '--no-backend', help='Write only the A record (dormant slug — no live backend).')):
    c    = Console(highlight=False)
    view = _stack(parent).register(slug, with_backend=not no_backend)
    backend = f'{view.backend_ip}:{view.backend_port}' if view.has_txt else '(none — dormant)'
    c.print(f'\n  [green]✓[/]  registered [bold]{slug}[/]  ([cyan]{view.fqdn}[/])')
    c.print(f'  [dim]   A={view.has_a}  TXT={view.has_txt}  backend={backend}[/]\n')


@app.command(name='unregister', help='Remove a slug (A + TXT).')
def unregister(slug  : str  = typer.Argument(..., help='Slug to remove'),
               parent: str  = typer.Option('', '--parent', '-p')):
    c       = Console(highlight=False)
    removed = _stack(parent).unregister(slug)
    if removed:
        c.print(f'\n  [green]✓[/]  unregistered [bold]{slug}[/]\n')
    else:
        c.print(f'\n  [yellow]⚠[/]  slug [bold]{slug}[/] was not registered\n')
        raise typer.Exit(1)


@app.command(name='teardown', help='Destroy the local edge (delete the local DNS + stack files).')
def teardown(parent: str  = typer.Option('', '--parent', '-p'),
             yes   : bool = typer.Option(False, '--yes', '-y', help='Skip confirmation')):
    c = Console(highlight=False)
    if not yes:
        typer.confirm('\n  Tear down the local edge (delete local DNS + stack state)?', default=True, abort=True)
    removed = _stack(parent).teardown()
    if removed:
        c.print('\n  [green]✓[/]  local edge torn down\n')
    else:
        c.print('\n  [dim]·  nothing to tear down (no local edge state found)[/]\n')


# ── usage ─────────────────────────────────────────────────────────────────────

@app.command(name='request', help='Simulate a user request end-to-end → welcome / 404 / dormant.')
def request(slug       : str  = typer.Argument(..., help='Slug to request'),
            parent     : str  = typer.Option('', '--parent', '-p'),
            show_body  : bool = typer.Option(False, '--body', help='Print the full HTML body'),
            output_json: bool = typer.Option(False, '--json', help='Machine-readable JSON output')):
    c    = Console(highlight=False)
    resp = _stack(parent).request(slug)
    if output_json:
        print(json.dumps(resp.json(), indent=2))
        return
    icon = {'welcome': '[green]✓[/]', 'dormant': '[yellow]●[/]', 'not_recognised': '[red]✗[/]'}.get(str(resp.kind), '·')
    c.print(f'\n  {icon}  [bold]{resp.host}[/]  →  HTTP {resp.status_code}  ([cyan]{resp.kind}[/])')
    c.print(f'  [dim]   {resp.title}[/]')
    if resp.backend:
        c.print(f'  [dim]   backend: {resp.backend}[/]')
    if show_body:
        c.print(f'\n{resp.body}')
    c.print()


@app.command(name='list', help='List registered slugs.')
def list_slugs(parent     : str  = typer.Option('', '--parent', '-p'),
               output_json: bool = typer.Option(False, '--json')):
    c     = Console(highlight=False)
    st    = _stack(parent).status()
    if output_json:
        print(json.dumps([s.json() for s in st.slugs], indent=2))
        return
    c.print(f'\n  Registered slugs for [cyan]{st.parent}[/]  ({len(st.slugs)})')
    for s in st.slugs:
        state = 'welcome' if (s.has_a and s.has_txt) else ('dormant' if s.has_a else 'orphan-backend')
        c.print(f'    {s.slug:<20} A={int(s.has_a)} TXT={int(s.has_txt)}  [dim]{state}[/]')
    if not st.slugs:
        c.print('    (none)')
    c.print()


@app.command(name='status', help='Show the local edge snapshot (proxy fleet, slugs, counter).')
def status(parent     : str  = typer.Option('', '--parent', '-p'),
           output_json: bool = typer.Option(False, '--json')):
    c  = Console(highlight=False)
    st = _stack(parent).status()
    if output_json:
        print(json.dumps(st.json(), indent=2))
        return
    c.print(f'\n  [bold]SG/Edge local[/]  parent=[cyan]{st.parent}[/]  deployed={st.deployed}')
    c.print(f'  [dim]   zone={st.zone_exists}  wildcard={st.wildcard}  '
            f'proxies={len(st.proxy_ips)}  slugs={len(st.slugs)}  zero_streak={st.zero_streak}[/]\n')


# ── rich check (ASCII art) ────────────────────────────────────────────────────

@app.command(name='check', help='Rich ASCII diagnostics — what is deployed/enabled and any deviations.')
def check(parent     : str  = typer.Option('', '--parent', '-p'),
          output_json: bool = typer.Option(False, '--json')):
    c  = Console(highlight=False)
    st = _stack(parent).check()
    if output_json:
        print(json.dumps(st.json(), indent=2))
        if _has_errors(st):
            raise typer.Exit(1)
        return
    _render_check(c, st)
    if _has_errors(st):
        raise typer.Exit(1)


def _has_errors(st) -> bool:
    return any(str(i.severity) == 'error' for i in st.issues)


_SEV_ICON = {'ok': '[green]✓[/]', 'info': '[dim]·[/]', 'warn': '[yellow]⚠[/]', 'error': '[red]✗[/]'}


def _render_check(c: Console, st) -> None:
    W    = 64
    bar  = '─' * W
    def row(text=''):                                                                # left-aligned content row inside the box
        c.print(f'  │ {text}')
    yn   = lambda ok: '[green]✓[/]' if ok else '[red]✗[/]'

    c.print()
    c.print(f'  ┌{bar}┐')
    c.print(f'  │ [bold]SG/Edge — local deployment[/]   ([cyan]{st.parent}[/])')
    c.print(f'  ├{bar}┤')
    if not st.deployed:
        row('[yellow]not deployed[/] — run [cyan]sg edge local setup[/]')
        c.print(f'  └{bar}┘')
        _render_issues(c, st, bar, W)
        c.print()
        return

    row('Browser')
    row('  │  http://<slug>.' + st.parent)
    row('  ▼')
    row(f'{yn(st.wildcard)} Wildcard   *.{st.parent}  (CloudFront equiv)')
    row('  │')
    row('  ▼')
    row(f'{yn(len(st.proxy_ips) > 0)} Proxy fleet  proxies.{st.parent}  ({len(st.proxy_ips)} IP)')
    for ip in st.proxy_ips:
        row(f'      • {ip}')
    row('  │')
    row('  ▼')
    row(f'{yn(True)} Slugs  ({len(st.slugs)} registered)')
    if not st.slugs:
        row('      (none — register one with `sg edge local register <slug>`)')
    for s in st.slugs:
        if s.has_a and s.has_txt:
            row(f'      [green]✓[/] {s.slug:<14} A+TXT  → {s.backend_ip}:{s.backend_port}  [dim](welcome)[/]')
        elif s.has_a:
            row(f'      [yellow]●[/] {s.slug:<14} A only → [dim](dormant — Vault Waker on first hit)[/]')
        else:
            row(f'      [red]✗[/] {s.slug:<14} TXT only → [dim](orphan backend)[/]')
    c.print(f'  └{bar}┘')
    _render_issues(c, st, bar, W)
    c.print()


def _render_issues(c: Console, st, bar: str, W: int) -> None:
    if not st.issues:
        return
    c.print(f'  ┌{bar}┐')
    c.print(f'  │ [bold]Checks[/]')
    c.print(f'  ├{bar}┤')
    for i in st.issues:
        icon = _SEV_ICON.get(str(i.severity), '·')
        c.print(f'  │ {icon} [dim]{i.area}[/]  {i.message}')
    c.print(f'  └{bar}┘')


# ── real HTTP server ──────────────────────────────────────────────────────────

@app.command(name='serve', help='Run the local proxy as a real HTTP server (route by Host header).')
def serve(parent: str = typer.Option('', '--parent', '-p'),
          port  : int = typer.Option(0, '--port', help='Listen port (default from config: 8410)')):
    c = Console(highlight=False)
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
    from sg_compute_specs.sg_edge.local.sg_edge_local__config import LOCAL_SERVE_PORT

    stack       = _stack(parent)
    listen_port = port or LOCAL_SERVE_PORT

    class _Handler(BaseHTTPRequestHandler):
        def do_GET(self):                                                            # noqa: N802 — http.server contract
            host = self.headers.get('Host', '') or f'unknown.{stack.parent}'
            resp = stack.handle(host)
            self.send_response(resp.status_code)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(resp.body.encode('utf-8'))

        def log_message(self, *a):                                                   # quiet — we print our own line
            try:
                host = self.headers.get('Host', '')
            except Exception:
                host = ''
            c.print(f'  [dim]→ {self.command} {self.path}  Host={host}[/]')

    c.print(f'\n  [green]●[/]  serving local edge for [cyan]{stack.parent}[/] on [bold]http://127.0.0.1:{listen_port}[/]')
    c.print(f'  [dim]   curl -H "Host: alice.{stack.parent}" http://127.0.0.1:{listen_port}/[/]')
    c.print(f'  [dim]   (browser: map *.{stack.parent} → 127.0.0.1 via /etc/hosts or dnsmasq)[/]')
    c.print(f'  [dim]   Ctrl-C to stop[/]\n')
    httpd = ThreadingHTTPServer(('127.0.0.1', listen_port), _Handler)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        c.print('\n  [dim]· stopped[/]\n')
    finally:
        httpd.server_close()


# ── use-cases ──────────────────────────────────────────────────────────────────

@app.command(name='usecases', help='List the scripted end-to-end use-cases.')
def usecases():
    from sg_compute_specs.sg_edge.local.usecases.Local__Edge__Usecases import Local__Edge__Usecases
    c = Console(highlight=False)
    c.print('\n  [bold]SG/Edge local use-cases[/]')
    for uc_id, name, desc in Local__Edge__Usecases().list():
        c.print(f'    [cyan]{uc_id}[/]  [bold]{name}[/]')
        c.print(f'        [dim]{desc}[/]')
    c.print('\n  [dim]   run one: sg edge local usecase UC-02   |   run all: sg edge local usecase all[/]\n')


@app.command(name='usecase', help='Run one use-case by id (e.g. UC-02), or "all" to run every one.')
def usecase(uc_id      : str  = typer.Argument(..., metavar='ID', help='Use-case id (UC-01 … UC-06) or "all"'),
            output_json: bool = typer.Option(False, '--json', help='Machine-readable JSON output')):
    from sg_compute_specs.sg_edge.local.usecases.Local__Edge__Usecases import Local__Edge__Usecases
    c   = Console(highlight=False)
    svc = Local__Edge__Usecases()
    try:
        results = svc.run_all() if uc_id.strip().lower() == 'all' else [svc.run(uc_id)]
    except ValueError as exc:
        c.print(f'\n  [red]✗  {exc}[/]\n')
        raise typer.Exit(1)

    if output_json:
        print(json.dumps([r.json() for r in results], indent=2))
        if not all(r.passed for r in results):
            raise typer.Exit(1)
        return

    c.print()
    for r in results:
        head = '[green]PASS[/]' if r.passed else '[red]FAIL[/]'
        c.print(f'  {head}  [cyan]{r.id}[/]  [bold]{r.name}[/]')
        for s in r.steps:
            mark = '[green]✓[/]' if s.ok else '[red]✗[/]'
            c.print(f'      {mark}  {s.label}  [dim]{s.detail}[/]')
    passed = sum(1 for r in results if r.passed)
    c.print(f'\n  {passed}/{len(results)} use-case(s) passed\n')
    if passed != len(results):
        raise typer.Exit(1)
