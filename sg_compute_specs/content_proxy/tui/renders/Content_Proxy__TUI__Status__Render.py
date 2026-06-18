# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — Content Proxy: status render (mockup 1)
# PURE — no textual/rich import; returns Rich markup strings. Testable on 3.11.
# Surfaces the 5-service health + the active script + the /mitm-proxy smoke result.
# ═══════════════════════════════════════════════════════════════════════════════


def _dot(ok: bool) -> str:
    return '[green]● up[/]' if ok else '[red]● down[/]'


def status_markup(info, smoke_ok: bool = False) -> str:                            # info = Schema__Content_Proxy__Stack__Info
    lines = ['[bold]Content-Transformation Proxy — Status[/]', '']
    lines += [f'  mitmproxy-ext   8080   basic-auth   {_dot(info.mitmproxy_ext_ok)}   [dim]deliverable (a)[/]',
              f'  mitmproxy-int   8080   none         {_dot(info.mitmproxy_int_ok)}   [dim]deliverable (b)[/]',
              f'  mitm-service    10011  x-api-key    {_dot(info.mitm_service_ok)}',
              f'  sg-playwright   8000   X-API-Key    {_dot(info.playwright_ok)}',
              f'  vault-app       443    token/TLS    {_dot(info.vault_app_ok)}',
              '']
    smoke = '[green]PASS[/]' if smoke_ok else '[yellow]not verified[/]'
    lines += [f'  /mitm-proxy smoke   {smoke}   [dim](injected UI renders → chain works)[/]',
              f'  active script       {str(info.active_script) or "[dim]—[/]"}',
              f'  mode                {info.mode.value}      tls  {info.tls.value}',
              '', '[dim][t] traffic   [x] transform   [r] refresh   [q] quit[/]']
    return '\n'.join(lines)


def status_plain(info, smoke_ok: bool = False) -> str:                              # no-TTY fallback
    def b(ok): return 'up' if ok else 'down'
    return '\n'.join([
        'content-proxy status:',
        f'  mitmproxy-ext  {b(info.mitmproxy_ext_ok)}',
        f'  mitmproxy-int  {b(info.mitmproxy_int_ok)}',
        f'  mitm-service   {b(info.mitm_service_ok)}',
        f'  sg-playwright  {b(info.playwright_ok)}',
        f'  vault-app      {b(info.vault_app_ok)}',
        f'  mitm_proxy_smoke {"pass" if smoke_ok else "unverified"}',
        f'  active_script  {str(info.active_script) or "-"}',
    ])
