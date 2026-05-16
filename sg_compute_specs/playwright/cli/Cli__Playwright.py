# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — playwright: Cli__Playwright
# Builder-driven CLI. The 8 standard verbs (list/info/create/wait/health/
# connect/exec/delete) plus the `ami` + `cert` sub-typers come from
# Spec__CLI__Builder. Spec-specific extras:
#   - logs    : stream boot / cloud-init / journal logs from the host
#   - extend  : push the auto-terminate timer out by N hours
#
# Create-time flags worth knowing:
#   (default)            host-plane + sg-playwright              (2 containers)
#   --with-mitmproxy     + agent-mitmproxy                       (3 containers)
#   --intercept-script   path/source baked into agent-mitmproxy  (needs --with-mitmproxy)
#   --ami <id>           boot from a baked AMI — skips engine install + image pull
# ═══════════════════════════════════════════════════════════════════════════════

from pathlib import Path

import typer
from rich.console import Console

from sg_compute.cli.base.Schema__Spec__CLI__Spec import Schema__Spec__CLI__Spec
from sg_compute.cli.base.Spec__CLI__Builder      import Spec__CLI__Builder
from sg_compute.cli.base.Spec__CLI__Defaults     import DEFAULT_REGION
from sg_compute.cli.base.Spec__CLI__Errors       import spec_cli_errors
from sg_compute_specs.playwright.cli.Renderers                              import (render_playwright_create,
                                                                                     render_playwright_info  )
from sg_compute_specs.playwright.schemas.Schema__Playwright__Create__Request import Schema__Playwright__Create__Request
from sg_compute_specs.playwright.service.Playwright__Service                 import Playwright__Service


def _set_extras(request, with_mitmproxy=False, intercept_script='', image_tag='latest',
                disk_size=20, use_spot=True, api_key=''):
    request.with_mitmproxy = bool(with_mitmproxy)
    request.use_spot       = bool(use_spot)
    if intercept_script:                                               # path-or-source: read a local file, else treat as inline source
        p = Path(intercept_script)
        request.intercept_script = p.read_text() if p.is_file() else intercept_script
    if image_tag:
        request.image_tag = image_tag
    if disk_size:
        request.disk_size_gb = int(disk_size)
    if api_key:
        request.api_key = api_key


_cli_spec = Schema__Spec__CLI__Spec(
    spec_id               = 'playwright'                              ,
    display_name          = 'Playwright'                              ,
    default_instance_type = 't3.medium'                               ,
    create_request_cls    = Schema__Playwright__Create__Request        ,
    service_factory       = lambda: Playwright__Service().setup()     ,
    health_path           = '/health/status'                          ,
    health_port           = 8000                                      ,
    health_scheme         = 'http'                                    ,
    extra_create_field_setters = _set_extras                          ,
    render_info_fn             = render_playwright_info               ,
    render_create_fn           = render_playwright_create             ,
)


app = Spec__CLI__Builder(
    cli_spec             = _cli_spec,
    extra_create_options = [
        ('with_mitmproxy'  , bool, False,
         'Add the agent-mitmproxy container — a 3-container stack (host-plane + '
         'sg-playwright + agent-mitmproxy). Default: 2 containers.'),
        ('intercept_script', str , '',
         'Path to a mitmproxy interceptor script (or inline source) — baked into '
         'agent-mitmproxy. Only meaningful with --with-mitmproxy.'),
        ('image_tag'       , str , 'latest',
         'diniscruz/sg-playwright image tag.'),
        ('disk_size'       , int , 20,
         'Root volume in GiB — container image layers.'),
        ('use_spot'        , bool, True,
         'Spot instance (~70% cheaper). Pass --no-use-spot for on-demand.'),
        ('api_key'         , str , '',
         'FAST_API__AUTH__API_KEY__VALUE. Auto-generated and returned once on create if blank.'),
    ],
).build()


# ── playwright-specific extras ────────────────────────────────────────────────

_LOG_SOURCES = {                                                       # name → (shell command template, ssm timeout, one-line description)
    'boot'      : ('tail -n {tail} /var/log/ephemeral-ec2-boot.log'  , 60,
                   'EC2 user-data boot script — [playwright] stage markers, available within seconds'),
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


@app.command(help='''Stream logs from the playwright host.

\b
Available sources (pick with --source / -s, or omit to be prompted):
  boot        EC2 user-data boot script — [playwright] stage markers
  cloud-init  cloud-init full output — slightly behind the boot log
  journal     full systemd journal — always available

\b
Add --follow / -f to poll for new lines every few seconds (Ctrl-C to stop).
''')
@spec_cli_errors
def logs(name  : str  = typer.Argument(None, help='Stack name; auto-selected when only one exists.'),
         tail  : int  = typer.Option(300,   '--tail', '-n',   help='Number of log lines to fetch.'),
         follow: bool = typer.Option(False, '--follow', '-f', help='Poll for new lines every few seconds (Ctrl-C to stop).'),
         source: str  = typer.Option('',    '--source', '-s',
                                     help='boot | cloud-init | journal. Omit to be prompted.'),
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
    svc        = Playwright__Service().setup()
    name       = Spec__CLI__Builder(_cli_spec).resolver.resolve(svc, name, region, 'playwright')
    others     = '  '.join(k for k in _LOG_SOURCES if k != source)
    fetch_tail = max(tail, 500) if follow else tail                                # follow mode needs headroom so the dedupe anchor doesn't fall off the back of a small tail
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

    shown_anchor = ''                                                              # last line printed — used to find new content each poll
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
    EC2 tag so `sg playwright list` shows the correct time-left.
    """
    from datetime import datetime, timedelta, timezone

    from sg_compute.platforms.ec2.helpers.EC2__Instance__Helper        import EC2__Instance__Helper
    from sg_compute_specs.playwright.service.Playwright__Stack__Mapper import TAG_TERMINATE_AT

    c    = Console(highlight=False)
    svc  = Playwright__Service().setup()
    name = Spec__CLI__Builder(_cli_spec).resolver.resolve(svc, name, region, 'playwright')
    info = svc.get_stack_info(region, name)
    if info is None:
        c.print(f'  [red]✗  No playwright stack matched {name!r}[/]')
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
