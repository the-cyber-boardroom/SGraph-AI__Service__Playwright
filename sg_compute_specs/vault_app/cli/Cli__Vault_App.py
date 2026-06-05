# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — vault-app: Cli__Vault_App
# Builder-driven CLI. The standard verbs (list/info/create/connect/exec/delete)
# plus the `ami` sub-typer (list/bake/wait/delete) come from Spec__CLI__Builder.
# Vault-app opts out of the default `wait` and `health` commands and replaces
# them with `check` and a diagnose-based `wait` — see the Setup-CLI Pattern
# guide (library/guides/v0.2.31__setup_cli_pattern.md).
#
# Spec-specific extras:
#   - check   : sequential boot checklist + external HTTP probe (was: diag + health)
#   - wait    : live boot-stage progress, polls until all checks pass
#   - logs    : stream boot / cloud-init / journal / container logs from the host
#   - extend  : push the auto-terminate timer out by N hours
#
# Create-time flags worth knowing:
#   (default)          just-vault — 1 container (sg-send-vault)
#   --with-playwright  4-container stack (+ host-plane + sg-playwright + agent-mitmproxy)
#   --podman           use Podman instead of Docker as the container engine
#   --ami <id>         boot from a baked AMI — skips engine install + image pull
# ═══════════════════════════════════════════════════════════════════════════════

import json
import os
import threading
from typing import Optional

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
    mode = '[green]with-playwright[/] (4 containers)' if with_playwright else '[dim]just-vault[/] (1 container)'
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
    mitmweb_url    = str(getattr(info, 'mitmweb_url',    '') or '')

    if host_plane_url:
        t.add_row('host-plane',        f'[cyan]{host_plane_url}[/]  [dim](container admin: /containers/list, /host/shell/page, …)[/]')
        t.add_row('host-plane-cookie', f'[cyan]{host_plane_url}/auth/set-cookie-form[/]')
    if mitmweb_url:
        t.add_row('mitmweb',           f'[cyan]{mitmweb_url}[/]  [dim](mitmproxy admin UI)[/]')
        t.add_row('mitmweb-cookie',    f'[cyan]http://localhost:19081/auth/set-cookie-form[/]')

    open_cmds = []
    if host_plane_url: open_cmds.append('[cyan]sp vault-app open host-plane[/]')
    if mitmweb_url:    open_cmds.append('[cyan]sp vault-app open mitmweb[/]')
    if open_cmds:
        t.add_row('open', '  ·  '.join(open_cmds))
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
                with_tls_check=True, tls_mode='letsencrypt-ip', acme_prod=True,
                tls_hostname='', with_aws_dns=False, interceptor_script='',
                name_prefix=''):
    request.with_playwright  = bool(with_playwright)
    request.name_prefix      = (name_prefix or '').strip()
    request.container_engine = 'podman' if podman else 'docker'
    request.use_spot         = bool(use_spot)
    request.with_tls_check   = bool(with_tls_check)
    request.with_aws_dns     = bool(with_aws_dns)
    # Auto-bump: --tls-hostname (or --with-aws-dns, which will derive one) implies
    # letsencrypt-hostname mode when mode is left at the default IP-cert. Explicit
    # --tls-mode wins (lets a caller combine --tls-mode self-signed --tls-hostname X).
    resolved_mode = tls_mode or 'self-signed'
    wants_hostname_cert = bool(tls_hostname) or bool(with_aws_dns)
    if wants_hostname_cert and resolved_mode == 'letsencrypt-ip':
        resolved_mode = 'letsencrypt-hostname'
    request.tls_mode         = resolved_mode
    request.acme_prod        = bool(acme_prod)
    request.tls_hostname     = (tls_hostname or '').strip()
    if storage_mode:
        request.storage_mode    = storage_mode
    if seed_vault_keys:
        request.seed_vault_keys = seed_vault_keys
    if access_token:
        request.access_token    = access_token
    if disk_size:
        request.disk_size_gb    = int(disk_size)
    # --interceptor-script: read the local file now (operator's machine) and ship
    # its source inline. Only meaningful with --with-playwright (it's the only
    # shape that runs agent-mitmproxy); ignored otherwise.
    if interceptor_script:
        import pathlib
        from sg_compute_specs.vault_app.enums.Enum__Vault_App__Interceptor__Kind          import Enum__Vault_App__Interceptor__Kind
        from sg_compute_specs.vault_app.primitives.Safe_Str__Vault_App__Interceptor__Source import Safe_Str__Vault_App__Interceptor__Source
        path = pathlib.Path(interceptor_script).expanduser()
        if not path.is_file():
            raise typer.BadParameter(f'interceptor script not found: {interceptor_script}')
        request.interceptor.kind          = Enum__Vault_App__Interceptor__Kind.INLINE
        request.interceptor.inline_source = Safe_Str__Vault_App__Interceptor__Source(path.read_text(encoding='utf-8'))


# ── --with-aws-dns: post-launch parallel Route 53 work ───────────────────────
# Kicked off after Vault_App__Service.create_stack returns, BEFORE _wait_healthy
# blocks on EC2 boot. The thread polls for the public IP (allocated ~5-10s after
# run_instance), then runs Vault_App__Auto_DNS to upsert the A record + wait for
# INSYNC + run authoritative check. By the time --wait reaches the cert-init
# stage, DNS has typically already converged, so cert-init's DNS-wait returns on
# its first poll. _wait_healthy + .join(timeout=180) ensure we don't return
# from create until both EC2 boot AND DNS are confirmed.

def _vault_app_post_launch(svc, region, request, response, kwargs, console):
    if not bool(getattr(request, 'with_aws_dns', False)):
        return None
    fqdn = str(getattr(request, 'tls_hostname', '') or '').strip()
    if not fqdn:                                                                   # belt-and-braces: service should have derived this, but skip cleanly if it didn't
        return None
    info        = getattr(response, 'stack_info', None) or response
    stack_name  = str(getattr(info, 'stack_name', '') or '')
    captured    = {}                                                                # populated by the worker; read on join

    def _worker():
        import time as _time
        from sg_compute_specs.vault_app.service.Vault_App__Auto_DNS import Vault_App__Auto_DNS
        # Poll get_stack_info for the public IP — usually allocated within 10s; 60s ceiling.
        public_ip = ''
        deadline  = _time.time() + 60
        while _time.time() < deadline:
            fresh = svc.get_stack_info(region, stack_name)
            ip    = str(getattr(fresh, 'public_ip', '') or '') if fresh is not None else ''
            if ip:
                public_ip = ip
                break
            _time.sleep(2)
        if not public_ip:
            console.print(f'  [yellow]⚠[/]  auto-dns: gave up waiting for public IP after 60s — skipping Route 53 work')
            captured['result'] = None
            return
        console.print(f'  [dim]auto-dns:[/] starting  {fqdn} → {public_ip}')
        def _progress(stage, detail):
            console.print(f'  [dim]auto-dns:[/] {stage}  [dim]{detail}[/]')
        result = Vault_App__Auto_DNS().run(fqdn=fqdn, public_ip=public_ip, on_progress=_progress)
        captured['result'] = result
        if result.error:
            console.print(f'  [red]✗[/]  auto-dns failed: {result.error}')
        else:
            console.print(f'  [green]✓[/]  auto-dns: {fqdn} → {public_ip}  (INSYNC + authoritative, {result.elapsed_ms}ms)')

    thread = threading.Thread(target=_worker, daemon=True, name='vault-app-auto-dns')
    thread.start()
    return thread                                                                  # has .join(timeout=...) — Spec__CLI__Builder joins after _wait_healthy


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
    post_launch_fn             = _vault_app_post_launch              ,
)


app = Spec__CLI__Builder(
    cli_spec              = _cli_spec,
    skip_default_commands = ['wait', 'health', 'delete'],             # replaced by `check`, diagnose-based `wait`, and `delete` w/ --all below
    extra_create_options  = [
        # ── stack shape ──────────────────────────────────────────────────
        ('with_playwright', bool, False,
         'Add the host-plane + sg-playwright + agent-mitmproxy set (4-container stack). '
         'Default: just-vault (1 container: sg-send-vault).'),
        ('podman'         , bool, False,
         'Use Podman instead of Docker as the container engine.'),
        ('use_spot'       , bool, True,
         'Spot instance (~70% cheaper). Pass --no-use-spot for on-demand.'),
        ('disk_size'      , int , 20,
         'Root volume in GiB — vault data + container image layers.'),
        ('name_prefix'    , str , '',
         "Prefix for the AWS Name tag (e.g. 'acme' → Name=acme-<stack-name>). "
         'Cosmetic only — StackName/StackType (used by list/info/delete) are '
         'unchanged. Default: bare stack name, no prefix.'),
        ('interceptor_script', str, '',
         'Path to a mitmproxy intercept script (Python) loaded by agent-mitmproxy '
         'so every browser request flowing through /pw/* passes through it. '
         '--with-playwright only; see scripts/interceptors/ for examples.'),
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
         "How cert-init obtains the cert: letsencrypt-ip (LE cert for the EC2 public IP, "
         "default — but NOT reachable from sandbox-egress proxies that validate hostnames); "
         "letsencrypt-hostname (LE cert for --tls-hostname, sandbox-reachable); "
         "self-signed (offline; browser will warn)."),
        ('tls_hostname'   , str , '',
         "FQDN to issue the cert for when tls_mode=letsencrypt-hostname (or auto-bumps "
         "tls_mode from letsencrypt-ip → letsencrypt-hostname when set). Point this "
         "hostname's A record at the stack's EC2 IP BEFORE running create — cert-init "
         "does not wait for DNS to propagate."),
        ('acme_prod'      , bool, True,
         "letsencrypt-* modes: use the LE production directory (browser-trusted, default). "
         "Pass --no-acme-prod for LE staging (untrusted, rate-limit-safe — for debugging)."),
        ('with_aws_dns'   , bool, False,
         "Auto-create the Route 53 A record for this stack in parallel with the EC2 boot. "
         "Derives the FQDN as <stack-name>.<SG_AWS__DNS__DEFAULT_ZONE> (default zone: "
         "sg-compute.sgraph.ai). Auto-bumps --tls-mode to letsencrypt-hostname. AWS-only. "
         "Requires this AWS account to own the default zone."),
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
    'mitmproxy' : ('(docker logs --tail {tail} vault-app-agent-mitmproxy-1 2>&1 || '
                   'podman logs --tail {tail} vault-app-agent-mitmproxy-1 2>&1) || true', 60,
                   'agent-mitmproxy container — mitmweb startup line includes the web UI password'),
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
         tail  : int  = typer.Option(30,    '--tail', '-n',   help='Number of log lines to fetch.'),
         follow: bool = typer.Option(False, '--follow', '-f', help='Poll for new lines every few seconds (Ctrl-C to stop).'),
         source: str  = typer.Option('',    '--source', '-s',
                                     help='boot | cloud-init | journal | cert-init | vault. Omit to be prompted.'),
         region: str  = typer.Option(DEFAULT_REGION, '--region', '-r')):
    """Stream logs from the stack host via SSM."""
    import time
    c = Console(highlight=False)

    # If the positional arg is a digit in range, treat it as a source index
    # ('sg va logs 4' → 'cert-init') instead of a stack name. This matches
    # the same numbering the interactive prompt shows.
    if name and name.isdigit():
        keys = list(_LOG_SOURCES)
        idx  = int(name)
        if 1 <= idx <= len(keys):
            if not source:
                source = keys[idx - 1]
            name = None                                                # fall through to auto-resolve below

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


# ── check / wait: unified boot checklist + external HTTP probe ───────────────
# Both commands drive the same diagnose generator and render into the same
# rich.Live table. `check` runs once; `wait` re-runs every poll-interval until
# every row is OK or the timeout expires. Replaces the old `health` and `diag`
# commands (see Setup-CLI Pattern guide, library/guides/v0.2.31__setup_cli_pattern.md).

_DIAG_ICONS = {
    'ok'      : '[green]✓[/]',
    'fail'    : '[red]✗[/]',
    'warn'    : '[yellow]⚠[/]',
    'skip'    : '[dim]⊘[/]',
    'checking': '[dim]…[/]',
    'pending' : '[dim]·[/]',
}

_DIAG_STATE_LABEL = {
    'ok'      : '[green]OK[/]',
    'fail'    : '[red]FAIL[/]',
    'warn'    : '[yellow]WARN[/]',
    'skip'    : '[dim]SKIP[/]',
    'checking': '[dim]…[/]',
    'pending' : '[dim]·[/]',
}

# Pre-known check order — matches Vault_App__Service.diagnose() yield order.
# Used so the Live table can show all rows up-front in 'pending' state instead
# of growing top-down as each generator yield arrives.
_CHECK_ORDER = ('ec2-state', 'ssm-reachable', 'boot-failed', 'container-engine',
                'images-pulled', 'containers-up', 'vault-http', 'boot-ok',
                'cert-init',                                                # TLS stacks only — surfaces cert_init.py's stage file
                'external-http')

# per-check log source to suggest when a check fails / warns
_DIAG_HINTS = {
    'ssm-reachable'    : [('boot'      , 'see if boot completed at all')],
    'boot-failed'      : [('boot'      , 'full boot log with the error')],
    'container-engine' : [('boot'      , 'engine install stage'), ('journal', 'systemd unit errors')],
    'images-pulled'    : [('boot'      , 'image pull is the long step')],
    'containers-up'    : [('boot'      , 'compose up output')],
    'vault-http'       : [('vault'     , 'sg-send-vault container output'), ('boot', 'container start markers')],
    'boot-ok'          : [('boot'      , 'watch boot progress')],
    'cert-init'        : [('cert-init' , 'full cert-init container output (DNS wait / ACME challenge)')],
    'external-http'    : [('vault'     , 'sg-send-vault container output')],
}


def _build_check_table(rows, *, header_extra: str = '') -> Table:
    t = Table(box=None, show_header=True, header_style='bold', padding=(0, 2), pad_edge=False)
    t.add_column('Check' , no_wrap=True, min_width=18)
    t.add_column('State' , no_wrap=True, min_width=6 )
    t.add_column('Detail' + (f'  [dim]{header_extra}[/]' if header_extra else ''))
    for name, status, detail in rows:
        icon  = _DIAG_ICONS      .get(status, '[dim]?[/]')
        label = _DIAG_STATE_LABEL.get(status, '[dim]?[/]')
        first_line, *_ = (detail or '').split('\n', 1)
        t.add_row(name, f'{icon} {label}', f'[dim]{first_line}[/]')
    return t


def _probe_external_http(svc, region: str, name: str) -> tuple:
    """Return (status, detail) for an external svc.health() probe."""
    try:
        result   = svc.health(region, name, timeout_sec=0)
        healthy  = bool(getattr(result, 'healthy'   , False))
        url      = str (getattr(result, 'url'       , '') or '')
        code     = int (getattr(result, 'http_code' , 0)) or 0
        latency  = int (getattr(result, 'latency_ms', 0)) or 0
        err      = str (getattr(result, 'error'     , '') or '')
        if healthy:
            return ('ok', f'HTTP {code} in {latency}ms — {url}' if url else f'HTTP {code} in {latency}ms')
        if code:
            return ('warn', f'HTTP {code} in {latency}ms — {url or err}')
        return ('fail', err or 'no response')
    except Exception as exc:
        return ('fail', str(exc)[:160])


def _run_checks(svc, region: str, name: str, *, live, rows: list, header_extra: str = '') -> list:
    """Drive svc.diagnose() + the external probe, updating `rows` (and the
    Live table) in place. Returns the final rows list."""
    by_name = {n: i for i, (n, _, _) in enumerate(rows)}

    def _set(check_name: str, status: str, detail: str):
        if check_name in by_name:
            rows[by_name[check_name]] = (check_name, status, detail)
        else:
            rows.append((check_name, status, detail))
            by_name[check_name] = len(rows) - 1
        live.update(_build_check_table(rows, header_extra=header_extra))

    for check_name, status, detail in svc.diagnose(region, name):
        _set(check_name, status, detail)

    _set('external-http', 'checking', '')
    status, detail = _probe_external_http(svc, region, name)
    _set('external-http', status, detail)
    return rows


def _initial_rows() -> list:
    return [(n, 'pending', '') for n in _CHECK_ORDER]


def _suggestions_for(rows, name: str) -> list:
    """De-duplicated `sg va logs` suggestions for any warn/fail rows."""
    seen, out = set(), []
    for check_name, status, _ in rows:
        if status not in ('fail', 'warn'):
            continue
        for source, reason in _DIAG_HINTS.get(check_name, []):
            if source not in seen:
                seen.add(source)
                out.append((source, reason, check_name))
    return out


def _print_summary(c: Console, rows: list, name: str) -> None:
    c.print()
    failed = [n for n, s, _ in rows if s == 'fail']
    warned = [n for n, s, _ in rows if s == 'warn']
    if not failed and not warned:
        c.print('  [green]✓  all checks passed[/]')
        c.print()
        return
    parts = []
    if failed: parts.append(f'[red]{len(failed)} failed[/]')
    if warned: parts.append(f'[yellow]{len(warned)} warnings[/]')
    c.print(f'  {", ".join(parts)}')
    suggested = _suggestions_for(rows, name)
    if suggested:
        c.print()
        c.print('  [bold]Suggested next steps:[/]')
        for source, reason, origin in suggested:
            c.print(f'    [cyan]sg va logs {name} --source {source:<10}[/]'
                    f'  [dim]# {reason}  ({origin})[/]')
    c.print()


@app.command()
@spec_cli_errors
def check(name  : str = typer.Argument(None, help='Stack name; auto-selected when only one exists.'),
          region: str = typer.Option(DEFAULT_REGION, '--region', '-r')):
    """Run the full stack health checklist and show one row per check.

    \b
    Checks (in order):
      ec2-state         EC2 instance is in running state
      ssm-reachable     SSM exec can reach the instance
      boot-failed       /var/lib/sg-compute-boot-failed is absent
      container-engine  docker (or podman.socket) service is active
      images-pulled     all Docker Hub images for this stack shape are present
      containers-up     compose containers are running
      vault-http        :8080/info/health responds from inside the host
      boot-ok           /var/lib/sg-compute-boot-ok is present
      cert-init         TLS stacks only — current stage from /var/lib/sg-compute/cert-init.stage
                        (start → waiting-for-dns → dns-converged → requesting-cert → cert-issued)
      external-http     /info/health responds from the operator's machine

    \b
    Replaces the old `health` (external probe only) and `diag` (internal
    checklist only) commands — same diagnose generator drives both surfaces.
    """
    from rich.live import Live

    c    = Console(highlight=False)
    svc  = Vault_App__Service().setup()
    name = Spec__CLI__Builder(_cli_spec).resolver.resolve(svc, name, region, 'vault-app')
    c.print()
    c.print(f'  [bold]Checks[/]  ·  [cyan]{name}[/]  [dim]{region}[/]')
    c.print()

    rows = _initial_rows()
    with Live(_build_check_table(rows), console=c, refresh_per_second=8, transient=False) as live:
        _run_checks(svc, region, name, live=live, rows=rows)

    _print_summary(c, rows, name)
    if any(s == 'fail' for _, s, _ in rows):
        raise typer.Exit(1)


@app.command()
@spec_cli_errors
def wait(name   : str = typer.Argument(None, help='Stack name; auto-selected when only one exists.'),
         region : str = typer.Option(DEFAULT_REGION, '--region', '-r'),
         timeout: int = typer.Option(600, '--timeout', '-t',
                                     help='Max seconds to wait before giving up.'),
         poll   : int = typer.Option(15, '--poll', '-p',
                                     help='Seconds between re-runs of the full checklist.')):
    """Re-run the check table on a loop until every row is OK (or timeout).

    \b
    The same diagnose generator that powers `check` runs in a loop, updating
    the Live table in place. Lets the operator watch boot progress through
    each stage (engine install → image pull → container start → vault HTTP)
    instead of waiting on a silent external HTTP probe.
    """
    import time
    from rich.live import Live

    c    = Console(highlight=False)
    svc  = Vault_App__Service().setup()
    name = Spec__CLI__Builder(_cli_spec).resolver.resolve(svc, name, region, 'vault-app')
    c.print()
    c.print(f'  [bold]Waiting[/]  ·  [cyan]{name}[/]  [dim]{region}[/]  '
            f'[dim](timeout={timeout}s, poll={poll}s)[/]')
    c.print()

    rows     = _initial_rows()
    started  = time.monotonic()
    attempt  = 0
    all_ok   = False
    with Live(_build_check_table(rows), console=c, refresh_per_second=8, transient=False) as live:
        while True:
            attempt += 1
            elapsed  = int(time.monotonic() - started)
            header   = f'attempt={attempt}  elapsed={elapsed}s'
            _run_checks(svc, region, name, live=live, rows=rows, header_extra=header)
            all_ok = all(s == 'ok' for _, s, _ in rows)
            if all_ok or time.monotonic() - started >= timeout:
                break
            time.sleep(poll)

    _print_summary(c, rows, name)
    if not all_ok:
        raise typer.Exit(1)


@app.command(name='cert-renew')
@spec_cli_errors
def cert_renew(name     : str  = typer.Argument(None, help='Stack name; auto-selected when only one exists.'),
               region   : str  = typer.Option(DEFAULT_REGION, '--region', '-r'),
               mode     : str  = typer.Option('', '--mode',
                                               help='Override SG__CERT_INIT__MODE on /opt/vault-app/.env before restart. '
                                                    'One of: letsencrypt-hostname, letsencrypt-ip, self-signed. '
                                                    'Empty = re-use whatever\'s already in .env.'),
               hostname : str  = typer.Option('', '--hostname',
                                               help='Override SG__CERT_INIT__TLS_HOSTNAME on /opt/vault-app/.env '
                                                    '(the FQDN to validate when mode=letsencrypt-hostname).'),
               wait     : bool = typer.Option(True, '--wait/--no-wait',
                                               help='Wait for the cert-init container to finish before returning.'),
               timeout  : int  = typer.Option(120, '--timeout', '-t',
                                               help='Max seconds to wait for cert-init to complete (LE issuance can take 20-90s).')):
    """Re-trigger Let's Encrypt cert issuance on a vault-app stack.

    \b
    Restarts the one-shot `cert-init` Docker/podman container on the EC2 via
    SSM. cert-init re-reads SG__CERT_INIT__* env vars from /opt/vault-app/.env
    and runs ACME HTTP-01 against the current DNS, then writes the cert+key
    to the shared /certs volume. The vault container picks up the new cert
    immediately (it mounts /certs).

    Use this when:
      • DNS was added/changed AFTER `sg va create` (HTTP-01 needs DNS
        pointing at the EC2 IP before issuance).
      • An existing cert expired and the auto-renew window slipped.
      • You ran `sg vp adopt <slug>` and now need the cert.

    Requires StackTLS=true on the instance.
    """
    import time as _t

    c    = Console(highlight=False)
    svc  = Vault_App__Service().setup()
    name = Spec__CLI__Builder(_cli_spec).resolver.resolve(svc, name, region, 'vault-app')
    info = svc.get_stack_info(region, name)
    if info is None:
        c.print(f'  [red]✗  No vault-app stack matched {name!r}[/]')
        raise typer.Exit(1)

    if not bool(getattr(info, 'tls_enabled', False)):
        c.print(f'  [red]✗  Stack {name!r} was not created with TLS enabled (StackTLS!=true)[/]')
        c.print(f'  [dim]   cert-renew has nothing to do. Recreate the stack with --with-tls-check.[/]')
        raise typer.Exit(1)

    engine = str(getattr(info, 'engine', '') or 'docker').lower()
    compose_bin = 'podman-compose' if engine == 'podman' else 'docker compose'

    # If the operator asked us to switch mode or change hostname, patch
    # /opt/vault-app/.env IN PLACE before recreating. The compose template
    # uses ${VAR:-default} substitution which is resolved at parse time
    # (compose up), so `restart` would re-use the old values — only
    # `up -d --force-recreate` re-reads .env and re-substitutes.
    env_patch = ''
    if mode or hostname:
        c.print(f'  [yellow]→[/]  Patching /opt/vault-app/.env  '
                f'mode={mode or "(unchanged)"}  hostname={hostname or "(unchanged)"}')
        kvs = []
        if mode:     kvs.append(('SG__CERT_INIT__MODE'        , mode))
        if hostname: kvs.append(('SG__CERT_INIT__TLS_HOSTNAME', hostname))
        env_patch = (
            'set -e; '
            'ENV=/opt/vault-app/.env; '
            'touch "$ENV"; '
            'update_kv(){ if grep -q "^$1=" "$ENV" 2>/dev/null; then '
            '  sed -i "s|^$1=.*|$1=$2|" "$ENV"; else echo "$1=$2" >> "$ENV"; fi; }; '
            + '; '.join(f'update_kv {k!r} {v!r}' for k, v in kvs)
            + '; echo "[env-patch] updated $ENV:"; '
            + '; '.join(f'grep "^{k}=" "$ENV"' for k, _v in kvs) + '; '
        )

    # `up -d --force-recreate` (NOT restart) is required so compose re-parses
    # the template, re-reads .env, and re-substitutes ${VAR} placeholders.
    # `restart` reuses the existing container's env — would silently re-run
    # cert-init with the OLD mode no matter what we wrote to .env. cert-init
    # is one-shot (exit 0 on success); the vault container's
    # depends_on:cert-init:service_completed_successfully waits for it.
    ssm_cmd = (
        f'{env_patch}'
        f'cd /opt/vault-app && '
        f'{compose_bin} up -d --force-recreate --no-deps cert-init 2>&1 | tail -40; '
        f'echo "---cert-init logs---"; '
        f'({"docker" if engine != "podman" else "podman"} logs vault-app-cert-init-1 '
        f'2>&1 | tail -30 || true)'
    )
    c.print()
    c.print(f'  [bold]sg va cert-renew[/]  stack=[cyan]{name}[/]  region=[cyan]{region}[/]  '
            f'engine=[cyan]{engine}[/]')
    c.print(f'  [dim]via SSM:[/] [cyan]{compose_bin} restart cert-init[/]\n')

    result = svc.exec(region, name, ssm_cmd, timeout_sec=60)
    stdout = str(getattr(result, 'stdout', '') or '').strip()
    stderr = str(getattr(result, 'stderr', '') or '').strip()
    if stdout:
        c.print('  [dim]' + '\n  '.join(stdout.splitlines()[-30:]) + '[/]')
    if stderr:
        c.print(f'  [yellow]stderr:[/] {stderr[:400]}')

    if not wait:
        c.print()
        c.print(f'  [green]✓[/]  cert-init restart triggered (returning without waiting)')
        return

    # Poll the cert-init container state until it shows Exited (0) — success
    c.print(f'\n  [yellow]→[/]  Waiting up to {timeout}s for cert-init to finish…')
    container = 'vault-app-cert-init-1'
    ps_cmd = (f'{"docker" if engine != "podman" else "podman"} '
              f'ps -a --filter name={container} --format "{{{{.Status}}}}"')
    t0 = _t.time()
    last_status = ''
    while True:
        elapsed = _t.time() - t0
        if elapsed > timeout:
            c.print(f'\n  [red]✗  timed out after {timeout}s — cert-init last status: {last_status!r}[/]')
            c.print(f'  [dim]   inspect the container logs with: sg va logs {name} --source cert-init[/]\n')
            raise typer.Exit(1)
        r = svc.exec(region, name, ps_cmd, timeout_sec=30)                          # SSM SendCommand minimum is 30s
        status = str(getattr(r, 'stdout', '') or '').strip().splitlines()
        status = status[0] if status else ''
        if status != last_status:
            c.print(f'  [dim]  {int(elapsed)}s: {status or "(no container yet)"}[/]')
            last_status = status
        # Healthy success markers
        if 'Exited (0)' in status:
            c.print(f'  [green]✓[/]  cert-init succeeded')
            # 1) Show what cert-init actually did — logs are now complete since
            #    the container exited. Without this we have no way to verify
            #    the cert is for the right CN/SAN.
            docker = 'docker' if engine != 'podman' else 'podman'
            logs_r = svc.exec(region, name,
                               f'{docker} logs vault-app-cert-init-1 2>&1 | tail -40',
                               timeout_sec=30)
            logs = str(getattr(logs_r, 'stdout', '') or '').strip()
            if logs:
                c.print('  [dim]cert-init logs:[/]')
                for line in logs.splitlines():
                    c.print(f'  [dim]   {line}[/]')

            # 2) Restart the vault container so it picks up the new cert.
            #    The vault reads /certs/cert.pem at startup — replacing the
            #    file on disk doesn't reload it. `compose restart sg-send-vault`
            #    is enough (no env changes; same container restart suffices)
            #    and --no-deps stops compose from touching cert-init again.
            c.print(f'  [yellow]→[/]  Restarting [bold]sg-send-vault[/] to pick up the new cert…')
            restart_r = svc.exec(region, name,
                                  f'cd /opt/vault-app && {compose_bin} restart '
                                  f'--no-deps sg-send-vault 2>&1 | tail -10',
                                  timeout_sec=60)
            rstdout = str(getattr(restart_r, 'stdout', '') or '').strip()
            if rstdout:
                for line in rstdout.splitlines():
                    c.print(f'  [dim]   {line}[/]')

            # 3) Quick liveness check — vault should be back on :443 in a few seconds.
            _t.sleep(3)
            ps_r = svc.exec(region, name,
                             f'{docker} ps --filter name=vault-app-sg-send-vault-1 '
                             f'--format "{{{{.Status}}}}"',
                             timeout_sec=30)
            vault_status = str(getattr(ps_r, 'stdout', '') or '').strip().splitlines()
            vault_status = vault_status[0] if vault_status else '(missing)'
            if 'Up' in vault_status:
                c.print(f'  [green]✓[/]  sg-send-vault: {vault_status}')
            else:
                c.print(f'  [yellow]⚠[/]  sg-send-vault: {vault_status}  '
                        f'(it may still be coming up — give it ~10s)')

            c.print(f'\n  [green]✓[/]  Done. Try the FQDN now: '
                    f'[cyan]curl -sI https://{hostname or "<fqdn>"}/[/]\n')
            return
        if 'Exited' in status and '(0)' not in status:
            c.print(f'\n  [red]✗  cert-init exited non-zero: {status}[/]')
            c.print(f'  [dim]   Inspect with: sg va logs {name} --source cert-init[/]\n')
            raise typer.Exit(1)
        _t.sleep(3)


# ── `sp vault-app open <target>` — SSM port-forward to an internal sidecar ───
# A target registry maps a friendly name to (local port, post-forward URL, cookie-
# form URL, description, with-playwright requirement). Adding a new internal
# sidecar = one entry here; no other command changes needed.

_FORWARD_TARGETS = {
    'host-plane': {'port'            : 19009,
                   'url'             : 'http://localhost:19009',
                   'cookie_form'     : 'http://localhost:19009/auth/set-cookie-form',
                   'desc'            : 'host-plane admin API — containers, shell, logs, pods, status',
                   'needs_playwright': False},
    'mitmweb'   : {'port'            : 19081,
                   'url'             : 'http://localhost:19081/web/',
                   'cookie_form'     : 'http://localhost:19081/auth/set-cookie-form',
                   'desc'            : 'mitmproxy admin UI — requires --with-playwright',
                   'needs_playwright': True },
}


def _render_open_targets(c: Console) -> None:
    c.print()
    c.print('  [bold]Available targets[/]  [dim](sp vault-app open <target> [stack-name])[/]')
    t = Table(box=None, show_header=False, padding=(0, 2))
    t.add_column(style='bold cyan', no_wrap=True)
    t.add_column()
    for tname, meta in _FORWARD_TARGETS.items():
        t.add_row(tname, f'[dim]{meta["desc"]}[/]\n[dim]  → {meta["url"]}[/]')
    c.print(t)
    c.print()


@app.command(name='open', help='''Open an internal sidecar via SSM port-forward.

\b
Available targets:
  host-plane  host-plane admin API (containers, shell, logs, pods, status)
  mitmweb     mitmproxy admin UI (--with-playwright only)

\b
Starts an `aws ssm start-session AWS-StartPortForwardingSession` tunnel,
prints the URL + the cookie-form URL, then hands the terminal to the aws
CLI — Ctrl-C closes the tunnel. Run with no target to list options.
''')
@spec_cli_errors
def open_target(target: Optional[str] = typer.Argument(None,
                          help='host-plane | mitmweb — omit to list available targets.'),
                name  : Optional[str] = typer.Argument(None,
                          help='Stack name; auto-selected when only one exists.'),
                region: str = typer.Option(DEFAULT_REGION, '--region', '-r')):
    c = Console(highlight=False)
    if not target:
        _render_open_targets(c)
        return
    target = target.lower()
    if target not in _FORWARD_TARGETS:
        raise typer.BadParameter(
            f'unknown target {target!r}; pick from: {", ".join(_FORWARD_TARGETS)}')
    meta = _FORWARD_TARGETS[target]

    svc  = Vault_App__Service().setup()
    name = Spec__CLI__Builder(_cli_spec).resolver.resolve(svc, name, region, 'vault-app')
    info = svc.get_stack_info(region, name)
    if info is None:
        c.print(f'  [red]✗  No vault-app stack matched {name!r}[/]')
        raise typer.Exit(1)
    if meta['needs_playwright'] and not getattr(info, 'with_playwright', False):
        c.print(f'  [red]✗  Target [bold]{target}[/] requires --with-playwright; '
                f'[bold]{name}[/] is a just-vault stack.[/]')
        raise typer.Exit(1)

    iid  = str(getattr(info, 'instance_id', '') or '')
    port = meta['port']

    c.print()
    c.print(f'  [bold]Opening {target}[/]  [dim]via SSM port-forward[/]')
    t = Table(box=None, show_header=False, padding=(0, 2))
    t.add_column(style='dim', no_wrap=True, min_width=14)
    t.add_column()
    t.add_row('stack',        f'[cyan]{name}[/]  [dim]{iid}[/]  region=[dim]{region}[/]')
    t.add_row('url',          f'[bold cyan]{meta["url"]}[/]')
    t.add_row('cookie-form',  f'[cyan]{meta["cookie_form"]}[/]  [dim](set the access token here once)[/]')
    t.add_row('',             '[dim]→ once you see "Waiting for connections…", open the url above.  Ctrl-C closes the tunnel.[/]')
    c.print(t)
    c.print()

    parameters = json.dumps({'portNumber'      : [str(port)],
                             'localPortNumber' : [str(port)]})
    os.execvp('aws', [
        'aws', 'ssm', 'start-session',
        '--target',        iid,
        '--document-name', 'AWS-StartPortForwardingSession',
        '--parameters',    parameters,
        '--region',        region,
    ])


# ── `sg va delete` — single stack or --all ───────────────────────────────────
# Replaces the builder's default delete to add the --all flag for bulk cleanup
# (useful after benchmarks or when wiping a region).

@app.command(name='delete', help='''Terminate a vault-app stack (or every stack in the region).

\b
  sg va delete <name>     terminate one stack (auto-picks if only one exists)
  sg va delete --all      terminate every vault-app stack in the region

\b
Deletes the EC2 instance + its security group, and removes the per-slug DNS
A record when one exists.  Confirmation prompt unless --yes is set.
''')
@spec_cli_errors
def delete(name  : Optional[str] = typer.Argument(None, help='Stack name; auto-selected when only one exists.  Ignored with --all.'),
           region: str           = typer.Option(DEFAULT_REGION, '--region', '-r'),
           all_  : bool          = typer.Option(False, '--all',          help='Terminate every vault-app stack in the region.'),
           yes   : bool          = typer.Option(False, '--yes', '-y',    help='Skip confirmation prompt.')):
    """Terminate one vault-app stack, or all of them with --all."""
    from sg_compute.cli.base.Spec__CLI__Renderers__Base import render_delete

    c   = Console(highlight=False)
    svc = Vault_App__Service().setup()

    if not all_:
        name = Spec__CLI__Builder(_cli_spec).resolver.resolve(svc, name, region, 'vault-app')
        if not yes:
            typer.confirm(f'Delete vault-app stack {name!r} in {region}?', default=True, abort=True)
        result = svc.delete_stack(region, name)
        render_delete(name, getattr(result, 'deleted', False), Console(highlight=False, width=200))
        fqdn = str(getattr(result, 'fqdn', '') or '')
        if fqdn:
            dns_ok = getattr(result, 'dns_deleted', False)
            c.print(f'  [dim]dns:[/] {fqdn}  {"[green]✓ deleted[/]" if dns_ok else "[yellow]⚠ not deleted (no record or Route53 error)[/]"}')
        if not getattr(result, 'deleted', False):
            raise typer.Exit(1)
        return

    # --all path
    stacks = getattr(svc.list_stacks(region), 'stacks', [])
    if not stacks:
        c.print(f'\n  [dim]No vault-app stacks found in {region}.[/]\n')
        return
    c.print(f'\n  Found [bold]{len(stacks)}[/] stack(s) in [cyan]{region}[/]:')
    for s in stacks:
        fqdn_tag = str(getattr(s, 'tls_hostname', '') or '')
        dns_hint = f'  [dim]{fqdn_tag}[/]' if fqdn_tag else ''
        c.print(f'    • [bold]{getattr(s, "stack_name", "?")}[/]  '
                f'[dim]{getattr(s, "instance_id", "")}  {getattr(s, "state", "")}[/]{dns_hint}')
    c.print()
    if not yes:
        typer.confirm(f'  Delete all {len(stacks)} stack(s) in {region}?', default=False, abort=True)
    failed = []
    for s in stacks:
        sname = str(getattr(s, 'stack_name', '') or '')
        c.print(f'  [yellow]→[/]  Deleting [bold]{sname}[/]…', end=' ')
        try:
            result = svc.delete_stack(region, sname)
            if getattr(result, 'deleted', False):
                fqdn = str(getattr(result, 'fqdn', '') or '')
                dns_note = ''
                if fqdn:
                    dns_ok   = getattr(result, 'dns_deleted', False)
                    dns_note = f'  [dim]dns: {fqdn} {"✓" if dns_ok else "⚠ not deleted"}[/]'
                c.print(f'[green]✓[/]{dns_note}')
            else:
                c.print('[red]✗[/]')
                failed.append(sname)
        except Exception as exc:
            c.print(f'[red]✗  {str(exc)[:80]}[/]')
            failed.append(sname)
    c.print()
    if failed:
        c.print(f'  [red]Failed to delete: {", ".join(failed)}[/]')
        raise typer.Exit(1)
    c.print(f'  [green]✓  All {len(stacks)} stack(s) deleted.[/]\n')


# ── `sp vault-app recreate` — delete + create-same-shape + wait + info ───────
# Preserves with_playwright / container_engine / with_tls_check from the existing
# stack's tags so the operator doesn't have to retype them. Everything else
# (tls_mode, acme_prod, max_hours, disk_size, …) resets to current `create`
# defaults. Always --waits. For different flags, use `delete` + `create` directly.

@app.command(name='recreate', help='''Delete a stack and launch a fresh one with the same shape.

\b
Preserves from the existing stack's tags:
  • --with-playwright  (2-vs-4 container shape)
  • container engine   (docker | podman)
  • --with-tls-check   (HTTPS on :443 vs plain HTTP on :8080)

\b
Everything else resets to current `create` defaults (LE production cert,
spot, max-hours, disk size, …). For different flags, use:
  sp vault-app delete && sp vault-app create --<flags>

Always --waits and prints `info` on success.
''')
@spec_cli_errors
def recreate(name  : Optional[str] = typer.Argument(None, help='Stack name; auto-selected when only one exists.'),
             region: str           = typer.Option(DEFAULT_REGION, '--region', '-r'),
             yes   : bool          = typer.Option(False, '--yes', '-y', help='Skip the delete confirmation prompt.')):
    c       = Console(highlight=False, width=200)
    builder = Spec__CLI__Builder(_cli_spec)
    svc     = Vault_App__Service().setup()
    name    = builder.resolver.resolve(svc, name, region, 'vault-app')
    info    = svc.get_stack_info(region, name)
    if info is None:
        c.print(f'  [red]✗  No vault-app stack matched {name!r}[/]')
        raise typer.Exit(1)

    with_playwright = bool(getattr(info, 'with_playwright', False))
    engine          = str(getattr(info, 'container_engine', '') or 'docker')
    with_tls_check  = bool(getattr(info, 'tls_enabled',      False))

    shape_lbl  = '[green]with-playwright[/] (4 containers)' if with_playwright else '[dim]just-vault[/] (1 container)'
    tls_lbl    = '[green]TLS on[/]' if with_tls_check else '[dim]plain HTTP[/]'

    c.print()
    c.print(Panel(
        f'[bold]Recreate[/]  ·  {name}\n'
        f'[dim]preserving:[/]  shape={shape_lbl}  ·  engine=[cyan]{engine}[/]  ·  tls={tls_lbl}\n'
        f'[dim]resetting:[/]   tls-mode, acme-prod, max-hours, disk-size, storage-mode → current defaults',
        expand=False))

    if not yes:
        typer.confirm(f'\n  Delete {name!r} and launch a fresh stack?', default=True, abort=True)

    c.print(f'\n  [yellow]→[/]  Deleting [bold]{name}[/]…')
    delete_result = svc.delete_stack(region, name)
    if not getattr(delete_result, 'deleted', False):
        c.print(f'  [red]✗  Delete failed for {name!r}[/]')
        raise typer.Exit(1)
    c.print(f'  [green]✓[/]  Deleted.')

    # Build the fresh request — schema defaults for everything except the three preserved fields.
    req = Schema__Vault_App__Create__Request()
    req.region           = region
    req.with_playwright  = with_playwright
    req.container_engine = 'podman' if engine == 'podman' else 'docker'
    req.with_tls_check   = with_tls_check

    c.print(f'\n  [yellow]→[/]  Launching fresh stack…\n')
    resp = svc.create_stack(req)
    _render_vault_app_create(resp, c)

    new_info = getattr(resp, 'stack_info', None) or resp
    new_name = str(getattr(new_info, 'stack_name', '') or '')
    builder._wait_healthy(svc, region, new_name)

    fresh = svc.get_stack_info(region, new_name)
    if fresh is not None:
        _render_vault_app_info(fresh, c)


@app.command(name='stop', help='''Stop a running vault-app stack.

\b
Stops the EC2 instance (preserving EBS volumes) and deletes the per-slug
DNS A record so requests are not routed to a stopped node.
Use `sg vault-app start` to restart and re-create the DNS record.
''')
@spec_cli_errors
def stop_stack(name  : Optional[str] = typer.Argument(None, help='Stack name; auto-selected when only one exists.'),
               region: str           = typer.Option(DEFAULT_REGION, '--region', '-r'),
               wait  : bool          = typer.Option(False, '--wait', '-w', help='Wait until the instance reports stopped state.')):
    c    = Console(highlight=False)
    svc  = Vault_App__Service().setup()
    name = Spec__CLI__Builder(_cli_spec).resolver.resolve(svc, name, region, 'vault-app')
    c.print(f'\n  [yellow]→[/]  Stopping [bold]{name}[/]…')
    result = svc.stop_stack(region, name)
    if not getattr(result, 'stopped', False):
        msg = str(getattr(result, 'message', 'stop failed'))
        c.print(f'  [red]✗  {msg}[/]')
        raise typer.Exit(1)
    dns_note = '  DNS A record deleted.' if getattr(result, 'dns_deleted', False) else ''
    if wait:
        from sg_compute.platforms.ec2.helpers.EC2__Instance__Helper import EC2__Instance__Helper
        info = svc.get_stack_info(region, name)
        iid  = str(getattr(info, 'instance_id', '') or '')
        if iid:
            c.print('  [dim]Waiting for stopped state…[/]')
            EC2__Instance__Helper().wait_for_stopped(region, iid)
    c.print(f'  [green]✓[/]  [bold]{name}[/] stopped.{dns_note}')
    c.print()


@app.command(name='start', help='''Start a stopped vault-app stack.

\b
Starts the EC2 instance and, if the stack has a registered FQDN,
re-creates the DNS A record pointing at the new public IP.
''')
@spec_cli_errors
def start_stack(name  : Optional[str] = typer.Argument(None, help='Stack name; auto-selected when only one exists.'),
                region: str           = typer.Option(DEFAULT_REGION, '--region', '-r'),
                wait  : bool          = typer.Option(False, '--wait', '-w', help='Wait for running state and re-upsert DNS.')):
    c    = Console(highlight=False)
    svc  = Vault_App__Service().setup()
    name = Spec__CLI__Builder(_cli_spec).resolver.resolve(svc, name, region, 'vault-app')
    c.print(f'\n  [yellow]→[/]  Starting [bold]{name}[/]…')
    result = svc.start_stack(region, name, wait_running=wait)
    if not getattr(result, 'started', False):
        msg = str(getattr(result, 'message', 'start failed'))
        c.print(f'  [red]✗  {msg}[/]')
        raise typer.Exit(1)
    parts = [f'  [green]✓[/]  [bold]{name}[/] started.']
    if getattr(result, 'public_ip', ''):
        parts.append(f'  IP: {result.public_ip}')
    if getattr(result, 'dns_upserted', False):
        parts.append(f'  DNS A → {result.public_ip}  ({result.fqdn})')
    c.print('\n'.join(parts))
    c.print()


# ── fargate sub-app ───────────────────────────────────────────────────────────

from sg_compute_specs.vault_app.fargate.cli.Cli__Vault_App__Fargate import app as fargate_app  # noqa: E402
app.add_typer(fargate_app, name='fargate')
