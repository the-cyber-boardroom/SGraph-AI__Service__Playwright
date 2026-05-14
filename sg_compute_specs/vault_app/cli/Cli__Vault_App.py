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

from sg_compute.cli.base.Schema__Spec__CLI__Spec import Schema__Spec__CLI__Spec
from sg_compute.cli.base.Spec__CLI__Builder      import Spec__CLI__Builder
from sg_compute.cli.base.Spec__CLI__Defaults     import DEFAULT_REGION
from sg_compute.cli.base.Spec__CLI__Errors       import spec_cli_errors
from sg_compute_specs.vault_app.schemas.Schema__Vault_App__Create__Request import Schema__Vault_App__Create__Request
from sg_compute_specs.vault_app.service.Vault_App__Service                 import Vault_App__Service


def _set_extras(request, with_playwright=False, podman=False, use_spot=True,
                storage_mode='disk', seed_vault_keys='', access_token='', disk_size=0):
    request.with_playwright  = bool(with_playwright)
    request.container_engine = 'podman' if podman else 'docker'
    request.use_spot         = bool(use_spot)
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
)


app = Spec__CLI__Builder(
    cli_spec             = _cli_spec,
    extra_create_options = [
        ('with_playwright', bool, False,
         'Add the sg-playwright + agent-mitmproxy pair (4-container stack). '
         'Default: just-vault (2 containers: host-plane + sg-send-vault).'),
        ('podman'         , bool, False,
         'Use Podman instead of Docker as the container engine.'),
        ('use_spot'       , bool, True,
         'Spot instance (~70% cheaper). Pass --no-use-spot for on-demand.'),
        ('storage_mode'   , str , 'disk',
         'sg-send-vault storage backend: disk | memory | s3.'),
        ('seed_vault_keys', str , '',
         'Comma-separated sgit keys cloned into the vault on first boot.'),
        ('disk_size'      , int , 20,
         'Root volume in GiB — vault data + container image layers.'),
        # ── advanced: hidden from --help; still accepted ──
        ('access_token'   , str , '',
         'Shared stack secret. Auto-generated and returned once on create if blank.', True),
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
''')
@spec_cli_errors
def logs(name  : str  = typer.Argument(None, help='Stack name; auto-selected when only one exists.'),
         tail  : int  = typer.Option(300,   '--tail', '-n',   help='Number of log lines to fetch.'),
         source: str  = typer.Option('',    '--source', '-s',
                                     help='boot | cloud-init | journal. Omit to be prompted.'),
         region: str  = typer.Option(DEFAULT_REGION, '--region', '-r')):
    """Stream logs from the stack host via SSM."""
    c = Console(highlight=False)
    if not source:
        source = _prompt_for_source(c)
    if source not in _LOG_SOURCES:
        raise typer.BadParameter(
            f'unknown source {source!r}; pick from: {", ".join(_LOG_SOURCES)}')
    cmd_tpl, timeout, _desc = _LOG_SOURCES[source]
    svc     = Vault_App__Service().setup()
    name    = Spec__CLI__Builder(_cli_spec).resolver.resolve(svc, name, region, 'vault-app')
    ssm_cmd = cmd_tpl.format(tail=tail)
    others  = '  '.join(k for k in _LOG_SOURCES if k != source)
    c.print(f'  [bold]{source}[/] [dim]──  other sources: {others}[/]')
    c.print(f'  [dim]via SSM:[/] [cyan]{ssm_cmd}[/]')
    c.print()
    result = svc.exec(region, name, ssm_cmd, timeout_sec=timeout)
    c.print(str(getattr(result, 'stdout', '') or ''))


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
