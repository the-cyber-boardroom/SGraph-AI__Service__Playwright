# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — Content Proxy: CLI renderers
# Rich info/create blocks — the "everything you need once it's up" surface.
# Pure rendering: takes a schema, prints; no service / AWS / HTTP calls.
# ═══════════════════════════════════════════════════════════════════════════════

from rich.console import Console
from rich.panel   import Panel
from rich.table   import Table

from sg_compute_specs.content_proxy.enums.Enum__Content_Proxy__Edge import Enum__Content_Proxy__Edge
from sg_compute_specs.content_proxy.enums.Enum__Content_Proxy__Tls  import Enum__Content_Proxy__Tls


def _urls(info):                                                                    # (proxy_endpoint, vault_url, scheme_note)
    ip       = str(getattr(info, 'public_ip', '') or '')
    tls      = getattr(info, 'tls',  Enum__Content_Proxy__Tls.NONE)
    edge     = getattr(info, 'edge', Enum__Content_Proxy__Edge.NONE)
    hostname = str(getattr(info, 'hostname', '') or '')
    if not ip:
        return '', '', ''
    proxy = f'http://{ip}:8080'                                                     # Mode 1 — configure the browser proxy here
    if edge == Enum__Content_Proxy__Edge.CADDY:                                     # the Caddy edge always terminates TLS on :443
        if hostname:
            return proxy, f'https://{hostname}', 'TLS via Caddy edge (trusted, auto-ACME)'
        return proxy, f'https://{ip}', 'TLS via Caddy edge (internal CA — curl -k)'
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
    terminate_at = str(getattr(info, 'terminate_at', '') or '')                      # deadman deadline (boot-script shutdown -h) → time-left
    if terminate_at:
        from sg_compute.cli.base.Spec__CLI__Renderers__Base import humanize_time_left
        remaining = int(getattr(info, 'time_remaining_sec', 0) or 0)
        t.add_row('time-left',   f'{humanize_time_left(terminate_at, remaining)}  [dim]({terminate_at} — auto-terminate)[/]')
    t.add_row('mode',       getattr(info, 'mode', None).value if hasattr(getattr(info, 'mode', None), 'value') else '—')
    t.add_row('tls',        getattr(info, 'tls',  None).value if hasattr(getattr(info, 'tls',  None), 'value') else '—')
    edge_val = getattr(info, 'edge', None)
    if hasattr(edge_val, 'value') and edge_val.value != 'none':
        t.add_row('edge',   edge_val.value)
    hostname = str(getattr(info, 'hostname', '') or '')
    if hostname:
        t.add_row('hostname', f'[bold cyan]{hostname}[/]  [dim](Route 53 → public IP; Caddy auto-ACME)[/]')
    token = str(getattr(info, 'access_token', '') or '')
    if proxy:
        t.add_row('proxy (Mode 1)', f'[bold cyan]{proxy}[/]  [dim]configure your browser proxy here — use your proxyauth creds[/]')
        t.add_row('vault / UX',     f'[bold cyan]{vault_url}/[/]  [dim]{scheme_note}[/]')
        t.add_row('sg-playwright',  f'[cyan]{vault_url}/pw/[/]  [dim](same-origin via the vault /pw proxy)[/]')
    browser_count  = int(getattr(info, 'browser_count', 0) or 0)
    browser_engine = str(getattr(info, 'browser_engine', '') or 'chromium')
    if browser_count > 0 and vault_url:                                              # interactive sg-playwright-vnc fleet — one noVNC browser per user
        urls = '\n'.join(f'                       [cyan]{vault_url}/browser/{i}/[/]'
                         for i in range(1, browser_count + 1))
        t.add_row('browsers', f'[dim]{browser_count} interactive {browser_engine} browser(s) (noVNC via sg-playwright-vnc):[/]\n{urls}')
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
    pa_user      = str(getattr(response, 'proxyauth_user',  '') or '')
    pa_pass      = str(getattr(response, 'proxyauth_pass',  '') or '')
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
        rows = [
            title,
            f'  access token  [bold yellow]{access_token}[/]  [dim](vault key + /pw key + set-cookie)[/]',
            f'  mitm key      {fastapi_key}  [dim](interceptor ↔ mitm-service)[/]',
        ]
        if pa_pass:                                                                  # Mode 1 (browser → ext proxy :8080) basic-auth
            rows.append(f'  proxy auth    [bold yellow]{pa_user}:{pa_pass}[/]  [dim](mitmproxy-ext :8080 — Mode 1 browser)[/]')
        console.print(Panel('\n'.join(rows), border_style='yellow', expand=False))
    if vault_url:
        console.print()
        console.print(f'  vault / UX  : [bold cyan]{vault_url}/[/]')
        console.print(f'  set-cookie  : [cyan]{vault_url}/auth/set-cookie-form[/]  [dim]— paste the access token to auth the browser (vault + /pw)[/]')
        browser_count = int(getattr(info, 'browser_count', 0) or 0)
        for i in range(1, browser_count + 1):                                        # interactive sg-playwright-vnc fleet URLs
            console.print(f'  browser {i}   : [cyan]{vault_url}/browser/{i}/[/]  [dim](interactive noVNC browser)[/]')
    console.print()
    console.print('  [dim]run [cyan]sg content-proxy info[/] for the full URL/token block.[/]')
    console.print()
