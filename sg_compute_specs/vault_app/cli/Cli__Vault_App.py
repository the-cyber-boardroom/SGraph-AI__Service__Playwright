# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — vault-app: Cli__Vault_App
# Builder-driven CLI. The 8 standard verbs (list/info/create/wait/health/
# connect/exec/delete) plus the `ami` sub-typer (list/bake/wait/delete) come
# from Spec__CLI__Builder. Spec-specific extras:
#   - logs    : stream boot / cloud-init / journal logs from the host
#   - extend  : push the auto-terminate timer out by N hours
#
# Create-time flags worth knowing:
#   (default)          just-vault — 2 containers (host-plane + sg-send-vault)
#   --with-playwright  4-container stack (+ sg-playwright + agent-mitmproxy)
#   --podman           use Podman instead of Docker as the container engine
#   --ami <id>         boot from a baked AMI — skips engine install + image pull
# ═══════════════════════════════════════════════════════════════════════════════

import typer
from rich.console import Console
from rich.panel   import Panel
from rich.table   import Table

from sg_compute.cli.base.Schema__Spec__CLI__Spec         import Schema__Spec__CLI__Spec
from sg_compute.cli.base.Spec__CLI__Builder              import Spec__CLI__Builder
from sg_compute.cli.base.Spec__CLI__Defaults             import DEFAULT_REGION
from sg_compute.cli.base.Spec__CLI__Errors               import spec_cli_errors
from sg_compute.cli.base.Spec__CLI__Renderers__Base      import humanize_time_left, humanize_uptime
from sg_compute_specs.vault_app.schemas.Schema__Vault_App__Create__Request import Schema__Vault_App__Create__Request
from sg_compute_specs.vault_app.service.Vault_App__Service                 import Vault_App__Service


def _render_vault_app_info(info, console: Console) -> None:
    stack_name  = str(getattr(info, 'stack_name',  ''))
    instance_id = str(getattr(info, 'instance_id', ''))
    state_raw   = (info.state.value
                   if hasattr(info, 'state') and hasattr(info.state, 'value')
                   else str(getattr(info, 'state', '')))
    console.print()
    console.print(Panel(f'[bold]{stack_name}[/]  [dim]{instance_id}[/]  {state_raw}', expand=False))
    console.print()
    t = Table(box=None, show_header=False, padding=(0, 2))
    t.add_column(style='bold', min_width=18, no_wrap=True)
    t.add_column()

    vault_url      = str(getattr(info, 'vault_url',      '') or '')
    playwright_url = str(getattr(info, 'playwright_url', '') or '')
    if vault_url:
        t.add_row('vault-url', f'[bold cyan]{vault_url}[/]')
    if playwright_url:
        t.add_row('playwright-url', f'[bold cyan]{playwright_url}[/]  [dim](same X-API-Key)[/]')

    with_playwright = getattr(info, 'with_playwright', False)
    mode = '[green]with-playwright[/] (4 containers)' if with_playwright else '[dim]just-vault[/] (2 containers)'
    t.add_row('mode', mode)
    engine = str(getattr(info, 'container_engine', '') or '') or 'docker'
    t.add_row('container-engine', engine)

    for key, label in (('region',           'region'        ),
                       ('instance_type',    'instance-type' ),
                       ('ami_id',           'ami-id'        ),
                       ('public_ip',        'public-ip'     ),
                       ('security_group_id','security-group')):
        val = str(getattr(info, key, '') or '')
        if val:
            t.add_row(label, val)

    uptime = getattr(info, 'uptime_seconds', 0)
    if uptime:
        t.add_row('uptime', humanize_uptime(uptime))

    pricing = getattr(info, 'spot', None)
    if pricing is not None:
        t.add_row('pricing', '[cyan]spot[/]' if pricing else '[dim]on-demand[/]')

    token = str(getattr(info, 'access_token', '') or '')
    if token:
        t.add_row('access-token', f'[bold]{token}[/]  [dim](X-API-Key + x-sgraph-access-token)[/]')

    if vault_url:
        t.add_row('set-cookie-form', f'[cyan]{vault_url}/auth/set-cookie-form[/]')
    if playwright_url:
        t.add_row('playwright-cookie', f'[cyan]{playwright_url}/auth/set-cookie-form[/]')

    host_plane_url = str(getattr(info, 'host_plane_url', '') or '')
    ssm_forward    = str(getattr(info, 'ssm_forward',    '') or '')
    if host_plane_url:
        t.add_row('host-plane', f'[cyan]{host_plane_url}[/]  [dim](mitmweb at /web/ — set the cookie first)[/]')
    if ssm_forward:
        t.add_row('ssm-forward', f'[dim]{ssm_forward}[/]')
    if vault_url:
        bookmarklet_token = token or 'YOUR_TOKEN'
        t.add_row('browser-auth',
                  f'[dim]javascript: document.cookie = '
                  f'"x-sgraph-access-token={bookmarklet_token}; path=/"; location.reload();[/]')

    terminate_at = str(getattr(info, 'terminate_at', '') or '')
    if terminate_at:
        remaining = int(getattr(info, 'time_remaining_sec', 0) or 0)
        t.add_row('terminate-at', terminate_at)
        t.add_row('time-left',    humanize_time_left(terminate_at, remaining))

    console.print(t)
    console.print()


def _render_vault_app_create(response, console: Console) -> None:
    info        = getattr(response, 'stack_info', None) or response
    stack_name  = str(getattr(info, 'stack_name',  ''))
    instance_id = str(getattr(info, 'instance_id', ''))
    vault_url   = str(getattr(info, 'vault_url', '') or '')
    token       = str(getattr(response, 'access_token', '') or '')
    elapsed     = getattr(response, 'elapsed_ms', 0)

    console.print()
    console.print(Panel(f'[bold green]Launching[/]  ·  {stack_name}', border_style='green', expand=False))
    console.print()
    console.print(f'  instance-id : [dim]{instance_id}[/]')
    console.print(f'  submitted in: {elapsed / 1000:.1f}s')
    console.print()

    # The access token is the one shared secret — it gates the vault HTTP API
    # (X-API-Key header / cookie) AND is the SG/Send access token. Shown once
    # here; recover later via `connect` → sudo cat /opt/vault-app/.env.
    if token:
        console.print(Panel(
            f'[bold yellow]{token}[/]\n\n'
            f'[dim]Save this now — shown once, not recoverable from the API.[/]\n'
            f'[dim]It is both the vault API key and the SG/Send access token.[/]\n'
            f'[dim]Recover later:  sp vault-app connect  →  sudo cat /opt/vault-app/.env[/]',
            title='[bold]access token[/]', border_style='yellow', expand=False))
        console.print()

    if vault_url:
        console.print(f'  vault-url   : [bold cyan]{vault_url}[/]')
        console.print(f'  set-cookie  : [cyan]{vault_url}/auth/set-cookie-form[/]'
                      f'  [dim]— paste the token here in a browser[/]')
    else:
        console.print('  [dim]public IP assigned shortly — run [cyan]sp vault-app info[/] for the URL,[/]')
        console.print('  [dim]or [cyan]sp vault-app create --wait[/] to block until healthy.[/]')
    console.print()


def _set_extras(request, with_playwright=False, podman=False, use_spot=True,
                storage_mode='disk', seed_vault_keys='', access_token='', disk_size=0,
                with_tls_check=True, tls_mode='letsencrypt-ip', acme_prod=True):
    request.with_playwright  = bool(with_playwright)
    request.container_engine = 'podman' if podman else 'docker'
    request.use_spot         = bool(use_spot)
    request.with_tls_check   = bool(with_tls_check)
    request.tls_mode         = tls_mode or 'self-signed'
    request.acme_prod        = bool(acme_prod)
    if storage_mode:
        request.storage_mode    = storage_mode
    if seed_vault_keys:
        request.seed_vault_keys = seed_vault_keys
    if access_token:
        request.access_token    = access_token
    if disk_size:
        request.disk_size_gb    = int(disk_size)


_cli_spec = Schema__Spec__CLI__Spec(
    spec_id               = 'vault-app'                              ,
    display_name          = 'Vault App'                              ,
    default_instance_type = 't3.medium'                              ,
    create_request_cls    = Schema__Vault_App__Create__Request        ,
    service_factory       = lambda: Vault_App__Service().setup()     ,
    health_path           = '/info/health'                           ,
    health_port           = 8080                                     ,
    health_scheme         = 'http'                                   ,
    extra_create_field_setters = _set_extras                         ,
    render_info_fn             = _render_vault_app_info              ,
    render_create_fn           = _render_vault_app_create            ,
)


app = Spec__CLI__Builder(
    cli_spec             = _cli_spec,
    extra_create_options = [
        # ── stack shape ──────────────────────────────────────────────────
        ('with_playwright', bool, False,
         'Add the sg-playwright + agent-mitmproxy pair (4-container stack). '
         'Default: just-vault (2 containers: host-plane + sg-send-vault).'),
        ('podman'         , bool, False,
         'Use Podman instead of Docker as the container engine.'),
        ('use_spot'       , bool, True,
         'Spot instance (~70% cheaper). Pass --no-use-spot for on-demand.'),
        ('disk_size'      , int , 20,
         'Root volume in GiB — vault data + container image layers.'),
        # ── vault storage ────────────────────────────────────────────────
        ('storage_mode'   , str , 'disk',
         'sg-send-vault storage backend: disk | memory | s3.'),
        ('seed_vault_keys', str , '',
         'Comma-separated sgit keys cloned into the vault on first boot.'),
        # ── TLS (on by default — a real LE cert for the EC2 IP) ──────────
        ('with_tls_check' , bool, True,
         'Serve the vault over HTTPS on :443 via the one-shot cert sidecar. '
         'Default ON; pass --no-with-tls-check for plain HTTP on :8080.'),
        ('tls_mode'       , str , 'letsencrypt-ip',
         "How cert-init obtains the cert: letsencrypt-ip (a real Let's Encrypt cert for "
         "the EC2 public IP, default) or self-signed (offline; browser will warn)."),
        ('acme_prod'      , bool, True,
         "letsencrypt-ip: use the LE production directory (browser-trusted, default). "
         "Pass --no-acme-prod for LE staging (untrusted, rate-limit-safe — for debugging)."),
        # ── secret ───────────────────────────────────────────────────────
        ('access_token'   , str , '',
         'Shared stack secret (vault API key + access token). Auto-generated if blank; '
         'always recoverable from sp vault-app info (tagged on the instance).'),
    ],
).build()


# ── vault-app-specific extras ─────────────────────────────────────────────────

_LOG_SOURCES = {                                                       # name → (shell command template, ssm timeout, one-line description)
    'boot'      : ('tail -n {tail} /var/log/ephemeral-ec2-boot.log'  , 60,
                   'EC2 user-data boot script — [vault-app] stage markers, available within seconds'),
    'cloud-init': ('tail -n {tail} /var/log/cloud-init-output.log'   , 60,
                   'cloud-init full output — slightly behind the boot log'),
    'journal'   : ('journalctl -n {tail} --no-pager'                 , 60,
                   'full systemd journal — always available'),
    'cert-init' : ('(docker logs --tail {tail} vault-app-cert-init-1 2>&1 || '
                   'podman logs --tail {tail} vault-app-cert-init-1 2>&1) || true'  , 60,
                   'one-shot TLS cert sidecar — why it exited (self-signed gen / ACME issuance)'),
    'vault'     : ('(docker logs --tail {tail} vault-app-sg-send-vault-1 2>&1 || '
                   'podman logs --tail {tail} vault-app-sg-send-vault-1 2>&1) || true', 60,
                   'sg-send-vault container — the vault app itself'),
}


def _prompt_for_source(c: Console) -> str:
    c.print()
    c.print('  [bold]Which log source?[/]')
    keys = list(_LOG_SOURCES)
    for i, k in enumerate(keys, 1):
        _, _, desc = _LOG_SOURCES[k]
        c.print(f'    [cyan]{i}[/]  [bold]{k:11}[/] [dim]{desc}[/]')
    c.print()
    ans = typer.prompt('  Pick a number or name', default='boot').strip()
    if ans.isdigit() and 1 <= int(ans) <= len(keys):
        return keys[int(ans) - 1]
    if ans in _LOG_SOURCES:
        return ans
    raise typer.BadParameter(f'unknown source {ans!r}; pick from: {", ".join(_LOG_SOURCES)}')


@app.command(help='''Stream logs from the vault-app host.

\b
Available sources (pick with --source / -s, or omit to be prompted):
  boot        EC2 user-data boot script — [vault-app] stage markers
  cloud-init  cloud-init full output — slightly behind the boot log
  journal     full systemd journal — always available
  cert-init   one-shot TLS cert sidecar — why it exited (--with-tls-check stacks)
  vault       sg-send-vault container — the vault app itself

\b
Add --follow / -f to poll for new lines every few seconds (Ctrl-C to stop).
''')
@spec_cli_errors
def logs(name  : str  = typer.Argument(None, help='Stack name; auto-selected when only one exists.'),
         tail  : int  = typer.Option(300,   '--tail', '-n',   help='Number of log lines to fetch.'),
         follow: bool = typer.Option(False, '--follow', '-f', help='Poll for new lines every few seconds (Ctrl-C to stop).'),
         source: str  = typer.Option('',    '--source', '-s',
                                     help='boot | cloud-init | journal | cert-init | vault. Omit to be prompted.'),
         region: str  = typer.Option(DEFAULT_REGION, '--region', '-r')):
    """Stream logs from the stack host via SSM."""
    import time
    c = Console(highlight=False)
    if not source:
        source = _prompt_for_source(c)
    if source not in _LOG_SOURCES:
        raise typer.BadParameter(
            f'unknown source {source!r}; pick from: {", ".join(_LOG_SOURCES)}')
    cmd_tpl, timeout, _desc = _LOG_SOURCES[source]
    svc        = Vault_App__Service().setup()
    name       = Spec__CLI__Builder(_cli_spec).resolver.resolve(svc, name, region, 'vault-app')
    others     = '  '.join(k for k in _LOG_SOURCES if k != source)
    fetch_tail = max(tail, 500) if follow else tail
    ssm_cmd    = cmd_tpl.format(tail=fetch_tail)

    c.print(f'  [bold]{source}[/] [dim]──  other sources: {others}[/]')
    c.print(f'  [dim]via SSM:[/] [cyan]{ssm_cmd}[/]')
    if follow:
        c.print('  [dim]following — Ctrl-C to stop[/]')
    c.print()

    def fetch():
        r = svc.exec(region, name, ssm_cmd, timeout_sec=timeout)
        return str(getattr(r, 'stdout', '') or '').splitlines()

    if not follow:
        c.print('\n'.join(fetch()))
        return

    shown_anchor = ''                                            # last line printed — used to find new content each poll
    try:
        while True:
            lines = fetch()
            if not shown_anchor:
                for line in lines:
                    c.print(line)
                shown_anchor = lines[-1] if lines else ''
            else:
                # find the anchor in the new batch (search from the end for speed)
                idx = next((i for i in range(len(lines) - 1, -1, -1)
                            if lines[i] == shown_anchor), None)
                new_lines = lines[idx + 1:] if idx is not None else lines
                for line in new_lines:
                    c.print(line)
                if new_lines:
                    shown_anchor = new_lines[-1]
            time.sleep(4)
    except KeyboardInterrupt:
        c.print('\n  [dim]stopped[/]')


@app.command()
@spec_cli_errors
def extend(name     : str   = typer.Argument(None, help='Stack name; auto-selected when only one exists.'),
           add_hours: float = typer.Option(1.0, '--add-hours', '--ah',
                                           help='Hours to add to the lifetime (default: 1).'),
           region   : str   = typer.Option(DEFAULT_REGION, '--region', '-r')):
    """Cancel the current shutdown timer and arm a fresh one N hours from now.

    \b
    Stops any transient run-*.timer unit on the instance (the shutdown
    countdown), arms a fresh systemd-run timer, and updates the TerminateAt
    EC2 tag so `sg vault-app list` shows the correct time-left.
    """
    from datetime import datetime, timedelta, timezone

    from sg_compute.platforms.ec2.helpers.EC2__Instance__Helper       import EC2__Instance__Helper
    from sg_compute_specs.vault_app.service.Vault_App__Stack__Mapper  import TAG_TERMINATE_AT

    c    = Console(highlight=False)
    svc  = Vault_App__Service().setup()
    name = Spec__CLI__Builder(_cli_spec).resolver.resolve(svc, name, region, 'vault-app')
    info = svc.get_stack_info(region, name)
    if info is None:
        c.print(f'  [red]✗  No vault-app stack matched {name!r}[/]')
        raise typer.Exit(1)

    instance_id      = str(info.instance_id)
    new_terminate_at = datetime.now(timezone.utc) + timedelta(hours=add_hours)
    new_seconds      = int(add_hours * 3600)
    new_iso          = new_terminate_at.strftime('%Y-%m-%dT%H:%M:%SZ')

    ssm_cmd = (
        "for t in $(systemctl list-units --type=timer --all --plain --no-legend"
        " | awk '{print $1}' | grep '^run-');"
        " do systemctl stop \"$t\" 2>/dev/null; done;"
        f" systemd-run --on-active={new_seconds}s /sbin/shutdown -h now"
    )
    c.print(f'\n  [dim]via SSM:[/] [cyan]{ssm_cmd}[/]\n')
    result = svc.exec(region, name, ssm_cmd, timeout_sec=30)
    stdout = str(getattr(result, 'stdout', '') or '').strip()
    if stdout:
        c.print(f'  [dim]{stdout}[/]')

    tag_ok = EC2__Instance__Helper().update_tags(region, instance_id, {TAG_TERMINATE_AT: new_iso})
    c.print()
    if tag_ok:
        c.print(f'  [green]✓[/]  [bold]{name}[/] extended — terminates at [bold]{new_iso}[/] UTC'
                f'  [dim](+{add_hours:.1f}h from now)[/]')
    else:
        c.print(f'  [yellow]⚠[/]  Timer armed on instance but TerminateAt tag update failed')
        c.print(f'  [dim]Intended expiry: {new_iso} UTC[/]')
    c.print()


# ── diag: sequential boot checklist ──────────────────────────────────────────

_DIAG_ICONS = {
    'ok'  : '[green]✓[/]',
    'fail': '[red]✗[/]',
    'warn': '[yellow]⚠[/]',
    'skip': '[dim]⊘[/]',
}

# per-check log source to suggest when a check fails / warns
_DIAG_HINTS = {
    'ssm-reachable'    : [('boot'      , 'see if boot completed at all')],
    'boot-failed'      : [('boot'      , 'full boot log with the error')],
    'container-engine' : [('boot'      , 'engine install stage'), ('journal', 'systemd unit errors')],
    'images-pulled'    : [('boot'      , 'ECR login + image pull is the long step')],
    'containers-up'    : [('boot'      , 'compose up output')],
    'vault-http'       : [('boot'      , 'container start markers')],
    'boot-ok'          : [('boot'      , 'watch boot progress')],
}


@app.command()
@spec_cli_errors
def diag(name  : str = typer.Argument(None, help='Stack name; auto-selected when only one exists.'),
         region: str = typer.Option(DEFAULT_REGION, '--region', '-r')):
    """Run the sequential 8-step boot checklist and show which steps passed/failed.

    \b
    Steps checked in order:
      ec2-state         EC2 instance is in running state
      ssm-reachable     SSM exec can reach the instance
      boot-failed       /var/lib/sg-compute-boot-failed is absent
      container-engine  docker (or podman.socket) service is active
      images-pulled     sg-send-vault + host-plane images present
      containers-up     both compose containers are running
      vault-http        :8080/info/health responds from inside the host
      boot-ok           /var/lib/sg-compute-boot-ok is present
    """
    import sys

    c    = Console(highlight=False)
    svc  = Vault_App__Service().setup()
    name = Spec__CLI__Builder(_cli_spec).resolver.resolve(svc, name, region, 'vault-app')
    c.print()
    c.print(f'  [bold]Diagnostics[/]  ·  [cyan]{name}[/]  [dim]{region}[/]')
    c.print()

    is_tty  = sys.stdout.isatty()
    results = []

    for check_name, status, detail in svc.diagnose(region, name):
        if status == 'checking':
            if is_tty:
                sys.stdout.write(f'  ···  {check_name:<20} checking…\r')
                sys.stdout.flush()
            continue

        if is_tty:
            sys.stdout.write('\r\033[K')
            sys.stdout.flush()

        icon = _DIAG_ICONS.get(status, '[dim]?[/]')
        results.append((check_name, status, detail))

        first_line, *rest = detail.split('\n')
        c.print(f'  {icon}  {check_name:18} [dim]{first_line}[/]')
        for extra in rest:
            if extra.strip():
                c.print(f'       [dim]{extra}[/]')

    c.print()
    failed = [n for n, s, _ in results if s == 'fail']
    warned = [n for n, s, _ in results if s == 'warn']
    if not failed and not warned:
        c.print('  [green]✓  all checks passed[/]')
    else:
        parts = []
        if failed: parts.append(f'[red]{len(failed)} failed[/]')
        if warned: parts.append(f'[yellow]{len(warned)} warnings[/]')
        c.print(f'  {", ".join(parts)}')
        seen_sources   = set()
        suggested_cmds = []
        for check_name, status, _ in results:
            if status not in ('fail', 'warn'):
                continue
            for source, reason in _DIAG_HINTS.get(check_name, []):
                if source not in seen_sources:
                    seen_sources.add(source)
                    suggested_cmds.append((source, reason, check_name))
        if suggested_cmds:
            c.print()
            c.print('  [bold]Suggested next steps:[/]')
            for source, reason, origin in suggested_cmds:
                c.print(f'    [cyan]sp vault-app logs {name} --source {source:<10}[/]'
                        f'  [dim]# {reason}  ({origin})[/]')
    c.print()
