# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — Content Proxy: CLI renderers
# Rich info/create blocks — the "everything you need once it's up" surface.
# Pure rendering: takes a schema, prints; no service / AWS / HTTP calls.
# ═══════════════════════════════════════════════════════════════════════════════

from rich.console import Console
from rich.panel   import Panel
from rich.table   import Table

from sg_compute_specs.content_proxy.enums.Enum__Content_Proxy__Tls import Enum__Content_Proxy__Tls


def _urls(info):                                                                    # (proxy_endpoint, vault_url, scheme_note)
    ip  = str(getattr(info, 'public_ip', '') or '')
    tls = getattr(info, 'tls', Enum__Content_Proxy__Tls.NONE)
    if not ip:
        return '', '', ''
    proxy = f'http://{ip}:8080'                                                     # Mode 1 — configure the browser proxy here
    if tls == Enum__Content_Proxy__Tls.NONE:
        return proxy, f'http://{ip}:443', 'plain HTTP on :443 (TLS none)'           # vault is http behind host 443
    return proxy, f'https://{ip}', 'TLS on :443'


def render_info(info, console: Console) -> None:
    stack_name  = str(getattr(info, 'stack_name',  '') or '')
    instance_id = str(getattr(info, 'instance_id', '') or '')
    state       = getattr(info, 'state', None)
    state_raw   = state.value if hasattr(state, 'value') else str(state or '')
    proxy, vault_url, scheme_note = _urls(info)

    console.print()
    console.print(Panel(f'[bold]{stack_name}[/]  [dim]{instance_id}[/]  {state_raw}', expand=False))
    console.print()

    t = Table(box=None, show_header=False, padding=(0, 2))
    t.add_column(style='bold', min_width=18, no_wrap=True)
    t.add_column()
    t.add_row('public-ip',  str(getattr(info, 'public_ip', '') or '—'))
    t.add_row('region',     str(getattr(info, 'region', '') or '—'))
    t.add_row('mode',       getattr(info, 'mode', None).value if hasattr(getattr(info, 'mode', None), 'value') else '—')
    t.add_row('tls',        getattr(info, 'tls',  None).value if hasattr(getattr(info, 'tls',  None), 'value') else '—')
    token = str(getattr(info, 'access_token', '') or '')
    if proxy:
        t.add_row('proxy (Mode 1)', f'[bold cyan]{proxy}[/]  [dim]configure your browser proxy here — use your proxyauth creds[/]')
        t.add_row('vault / UX',     f'[bold cyan]{vault_url}/[/]  [dim]{scheme_note}[/]')
        t.add_row('sg-playwright',  f'[cyan]{vault_url}/pw/[/]  [dim](same-origin via the vault /pw proxy)[/]')
    if token:
        t.add_row('access-token', f'[bold]{token}[/]  [dim](X-API-Key + x-sgraph-access-token)[/]')
    if vault_url:
        t.add_row('set-cookie',  f'[cyan]{vault_url}/auth/set-cookie-form[/]  [dim]— paste the token here to auth the browser (vault + /pw)[/]')
    t.add_row('proxy CA',   '[dim]import into the browser for Mode 1 → [/][cyan]sg content-proxy local ca[/]')
    t.add_row('verify',     '[cyan]sg content-proxy smoke[/]  [dim](runs the /mitm-proxy chain check on the box via SSM)[/]')
    console.print(t)
    console.print()


def render_create(response, console: Console) -> None:
    info        = getattr(response, 'stack_info', None) or response
    stack_name  = str(getattr(info, 'stack_name',  '') or '')
    instance_id = str(getattr(info, 'instance_id', '') or '')
    elapsed      = int(getattr(response, 'elapsed_ms', 0) or 0)
    fastapi_key  = str(getattr(response, 'fastapi_api_key', '') or '')
    access_token = str(getattr(response, 'access_token',    '') or '')
    _, vault_url, _ = _urls(info)

    console.print()
    console.print(Panel(f'[bold green]Launching[/]  ·  {stack_name}', border_style='green', expand=False))
    console.print()
    console.print(f'  instance-id : [dim]{instance_id}[/]')
    console.print(f'  submitted in: {elapsed / 1000:.1f}s')
    from_env = bool(getattr(response, 'secrets_from_env', False))
    if fastapi_key or access_token:                                                  # surfaced ONCE — not recoverable from the API
        title = ('[bold]stack secrets[/]  [dim](from --env-file)[/]' if from_env
                 else '[bold]generated secrets[/]  [dim](shown once)[/]')
        console.print()
        console.print(Panel('\n'.join([
            title,
            f'  access token  [bold yellow]{access_token}[/]  [dim](vault key + /pw key + set-cookie)[/]',
            f'  mitm key      {fastapi_key}  [dim](interceptor ↔ mitm-service)[/]',
        ]), border_style='yellow', expand=False))
    if vault_url:
        console.print()
        console.print(f'  vault / UX  : [bold cyan]{vault_url}/[/]')
        console.print(f'  set-cookie  : [cyan]{vault_url}/auth/set-cookie-form[/]  [dim]— paste the access token to auth the browser (vault + /pw)[/]')
    console.print()
    console.print('  [dim]run [cyan]sg content-proxy info[/] for the full URL/token block.[/]')
    console.print()
