# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — vault-publish setup: Cli__Setup
# Typer app for `sg vault-publish setup` sub-commands.
#
#   sg vault-publish setup check    — check all areas (ec2+iam+lambda+cf+cf-function+acm+dns)
#   sg vault-publish setup create   — create all resources in dependency order
#   sg vault-publish setup update   — update/redeploy all resources
#   sg vault-publish setup delete   — delete all resources (reverse order)
#
#   sg vault-publish setup ec2          check/status                        (read-only)
#   sg vault-publish setup iam          check/status/create/update/delete
#   sg vault-publish setup lambda       check/status/create/update
#   sg vault-publish setup cf           check/status/create
#   sg vault-publish setup cf-function  check/status/create/update/delete   (viewer-Host shim)
#   sg vault-publish setup acm          check/status/request
#   sg vault-publish setup dns          check/status/create/delete
#
# Every command:
#   1. Prints the auto-assume notice if iam-admin was detected.
#   2. Runs a credential pre-flight (STS GetCallerIdentity) and exits cleanly
#      on failure — no tracebacks.
#   3. Wraps the service call in a broad except so ClientError and RuntimeError
#      are rendered as readable messages, not Python tracebacks.
# ═══════════════════════════════════════════════════════════════════════════════

import json
from typing import List

import typer
from botocore.exceptions import ClientError
from rich.console        import Console
from rich.live           import Live
from rich.table          import Table

from sg_compute_specs.vault_publish.setup.schemas.Enum__Setup__State            import Enum__Setup__State
from sg_compute_specs.vault_publish.setup.service.Setup__IAM                    import Setup__IAM
from sg_compute_specs.vault_publish.setup.service.Setup__Lambda                 import Setup__Lambda
from sg_compute_specs.vault_publish.setup.service.Setup__CF                     import Setup__CF
from sg_compute_specs.vault_publish.setup.service.Setup__CF__Function           import Setup__CF__Function
from sg_compute_specs.vault_publish.setup.service.Setup__ACM                    import Setup__ACM
from sg_compute_specs.vault_publish.setup.service.Setup__DNS                    import Setup__DNS
from sg_compute_specs.vault_publish.setup.service.Setup__EC2                    import Setup__EC2
from sg_compute_specs.vault_publish.setup.service.Setup__Admin__IAM             import Setup__Admin__IAM
from sg_compute_specs.vault_publish.setup.service.Setup__Admin__Lambda          import Setup__Admin__Lambda
from sg_compute_specs.vault_publish.setup.service.Setup__Admin__CF              import Setup__Admin__CF
from sg_compute_specs.vault_publish.setup.service.Setup__Admin__DNS             import Setup__Admin__DNS
from sg_compute_specs.vault_publish.schemas.Schema__Vault_Publish__Bootstrap__Request import DEFAULT_CERT_ARN, DEFAULT_ZONE

app              = typer.Typer(name='setup',        help='Setup and drift-check for vault-publish AWS resources.', no_args_is_help=True)
ec2_app          = typer.Typer(name='ec2',          help='EC2 prerequisites (IAM instance profile + base AMI).',   no_args_is_help=True)
iam_app          = typer.Typer(name='iam',          help='IAM execution role management.',                         no_args_is_help=True)
lambda_app       = typer.Typer(name='lambda',       help='Lambda waker function management.',                      no_args_is_help=True)
cf_app           = typer.Typer(name='cf',           help='CloudFront wildcard distribution management.',           no_args_is_help=True)
cf_function_app  = typer.Typer(name='cf-function',  help='CloudFront Function — viewer Host → X-Forwarded-Host.',  no_args_is_help=True)
acm_app          = typer.Typer(name='acm',          help='ACM wildcard certificate management.',                   no_args_is_help=True)
dns_app          = typer.Typer(name='dns',          help='Route 53 wildcard DNS record management.',               no_args_is_help=True)
admin_iam_app    = typer.Typer(name='admin-iam',    help='Admin Lambda IAM execution role.',                       no_args_is_help=True)
admin_lambda_app = typer.Typer(name='admin-lambda', help='Admin Lambda (vp-admin) function management.',           no_args_is_help=True)
admin_cf_app     = typer.Typer(name='admin-cf',     help='Admin CloudFront distribution + single-host ACM cert.',  no_args_is_help=True)
admin_dns_app    = typer.Typer(name='admin-dns',    help='Route 53 record for vp-admin.<zone>.',                   no_args_is_help=True)

app.add_typer(ec2_app,          name='ec2')
app.add_typer(iam_app,          name='iam')
app.add_typer(lambda_app,       name='lambda')
app.add_typer(cf_app,           name='cf')
app.add_typer(cf_function_app,  name='cf-function')
app.add_typer(acm_app,          name='acm')
app.add_typer(dns_app,          name='dns')
app.add_typer(admin_iam_app,    name='admin-iam')
app.add_typer(admin_lambda_app, name='admin-lambda')
app.add_typer(admin_cf_app,     name='admin-cf')
app.add_typer(admin_dns_app,    name='admin-dns')


# ── service constructors ─────────────────────────────────────────────────────

def _iam()          -> Setup__IAM:           return Setup__IAM()
def _lambda()       -> Setup__Lambda:        return Setup__Lambda()
def _cf()           -> Setup__CF:            return Setup__CF()
def _cf_function()  -> Setup__CF__Function:  return Setup__CF__Function()
def _acm()          -> Setup__ACM:           return Setup__ACM()
def _dns()          -> Setup__DNS:           return Setup__DNS()
def _ec2()          -> Setup__EC2:           return Setup__EC2()
def _admin_iam()    -> Setup__Admin__IAM:    return Setup__Admin__IAM()
def _admin_lambda() -> Setup__Admin__Lambda: return Setup__Admin__Lambda()
def _admin_cf()     -> Setup__Admin__CF:     return Setup__Admin__CF()
def _admin_dns()    -> Setup__Admin__DNS:    return Setup__Admin__DNS()


# ── shared pre-flight helpers ─────────────────────────────────────────────────

def _print_role_notice(c: Console, svc: Setup__IAM) -> None:
    notice = svc.assumed_role_notice()
    if notice:
        c.print(f'  [dim]ℹ  {notice}[/]')


def _preflight(c: Console, svc: Setup__IAM) -> bool:
    info = svc.credentials_ok()
    if info['ok']:
        c.print(f"  [dim]✓  identity: {info['arn']}[/]")
        return True
    c.print(f'\n  [red]✗  credential check failed[/]')
    c.print(f"  [red]   {info['error']}[/]")
    err  = info['error']
    role = svc._resolved_role or 'your-role'
    if 'InvalidClientTokenId' in err or 'ExpiredToken' in err or 'ExpiredTokenException' in err:
        c.print(f'\n  [dim]   Hint: credentials for {role!r} are stale or missing a session token.[/]')
        c.print(f'  [dim]   Run:  eval $(sg credentials switch {role})[/]')
    elif 'NoCredentialProviders' in err or 'Unable to locate credentials' in err:
        c.print(f'\n  [dim]   Hint: no AWS credentials found.[/]')
        c.print(f'  [dim]   Run:  eval $(sg credentials switch {role})[/]')
    return False


def _print_aws_error(c: Console, exc: ClientError) -> None:
    code = exc.response.get('Error', {}).get('Code', 'Unknown')
    msg  = exc.response.get('Error', {}).get('Message', str(exc))
    c.print(f'  [red]✗  AWS error ({code}): {msg}[/]')


# ═══════════════════════════════════════════════════════════════════════════════
# Global commands — operate on all areas at once
# ═══════════════════════════════════════════════════════════════════════════════

@app.command(name='check', help='Check all areas: ec2 + iam + lambda + cf + cf-function + acm + dns.')
def setup_check(
    zone    : str = typer.Option(DEFAULT_ZONE,     '--zone',     help='DNS apex zone'),
    cert_arn: str = typer.Option(DEFAULT_CERT_ARN, '--cert-arn', help='ACM certificate ARN'),
):
    c   = Console(highlight=False)
    iam = _iam()
    _print_role_notice(c, iam)
    if not _preflight(c, iam):
        raise typer.Exit(1)
    c.print()

    # Each entry: (area_label, check_fn, format_detail_fn)
    checks = [
        ('ec2',         lambda: _ec2().check(),
                        lambda r: f'profile={r.profile_name} ami={r.ami_id or "(none)"}'),
        ('iam',         lambda: iam.check(),
                        lambda r: r.role_arn or r.role_name),
        ('lambda',      lambda: _lambda().check(),
                        lambda r: r.function_url or r.function_name),
        ('cf',          lambda: _cf().check(zone),
                        lambda r: r.domain_name or f'*.{zone}'),
        ('cf-function', lambda: _cf_function().check(zone),
                        lambda r: (f'attached → {r.distribution_id}'
                                    if r.attached else r.function_name)),
        ('acm',         lambda: _acm().check(zone),
                        lambda r: r.cert_arn or f'*.{zone}'),
        ('dns',         lambda: _dns().check(zone),
                        lambda r: r.record_value or f'*.{zone}'),
    ]

    # results[i] = (area_label, state_or_None, detail) — None state == pending
    results = [(area, None, '') for area, _, _ in checks]

    def _build_table() -> Table:
        t = Table(box=None, show_header=True, padding=(0, 2))
        t.add_column('Area',   style='bold')
        t.add_column('State',  style='')
        t.add_column('Detail', style='dim')
        for area, state, detail in results:
            if state is None:
                t.add_row(area, '[dim]⏳ checking…[/]', '')
            else:
                t.add_row(area, _STATE_ICON.get(state, str(state)), detail)
        return t

    overall_ok = True
    with Live(_build_table(), console=c, refresh_per_second=8, transient=False) as live:
        for i, (area, check_fn, format_detail) in enumerate(checks):
            try:
                rep    = check_fn()
                state  = rep.state
                detail = format_detail(rep)
            except Exception as exc:
                state  = Enum__Setup__State.ERROR
                detail = str(exc)
            results[i] = (area, state, detail)
            live.update(_build_table())
            if state != Enum__Setup__State.OK:
                overall_ok = False

    c.print()
    if not overall_ok:
        raise typer.Exit(1)


@app.command(name='create', help='Create all vault-publish resources in dependency order.')
def setup_create(
    zone    : str  = typer.Option(DEFAULT_ZONE,     '--zone',     help='DNS apex zone'),
    cert_arn: str  = typer.Option(DEFAULT_CERT_ARN, '--cert-arn', help='ACM certificate ARN'),
    role_arn: str  = typer.Option('',               '--role-arn', help='Lambda execution role ARN'),
    yes     : bool = typer.Option(False, '--yes', '-y', help='Skip confirmation'),
):
    c = Console(highlight=False)
    iam = _iam()
    _print_role_notice(c, iam)
    if not _preflight(c, iam):
        raise typer.Exit(1)
    if not yes:
        typer.confirm(
            f"\n  Create all vault-publish resources for zone '{zone}'?",
            default=True, abort=True)

    c.print(f'\n  [dim]Zone: {zone}  CertARN: {cert_arn[:40]}…[/]\n')
    exit_code = 0

    # 1 — IAM
    c.print('  [yellow]→[/]  iam create…')
    try:
        rep = iam.create()
        icon = '[green]✓[/]' if rep.state == Enum__Setup__State.OK else '[yellow]⚠[/]'
        c.print(f'  {icon}  iam  {rep.role_arn or rep.role_name}')
        if rep.state not in (Enum__Setup__State.OK,):
            exit_code = 1
    except (ClientError, RuntimeError, Exception) as exc:
        c.print(f'  [red]✗  iam: {exc}[/]')
        exit_code = 1

    # 2 — Lambda
    c.print('  [yellow]→[/]  lambda create…')
    try:
        lrep = _lambda().create(role_arn=role_arn)
        icon = '[green]✓[/]' if lrep.state == Enum__Setup__State.OK else '[yellow]⚠[/]'
        c.print(f'  {icon}  lambda  {lrep.function_url or lrep.function_name}')
        if lrep.state not in (Enum__Setup__State.OK,):
            exit_code = 1
    except (ClientError, RuntimeError, Exception) as exc:
        c.print(f'  [red]✗  lambda: {exc}[/]')
        exit_code = 1

    # 3 — CF (depends on Lambda URL)
    c.print('  [yellow]→[/]  cf create…')
    try:
        crep = _cf().create(zone=zone, cert_arn=cert_arn)
        icon = '[green]✓[/]' if crep.state == Enum__Setup__State.OK else '[yellow]⚠[/]'
        c.print(f'  {icon}  cf  {crep.domain_name or crep.distribution_id}')
        if crep.state not in (Enum__Setup__State.OK,):
            exit_code = 1
    except (ClientError, RuntimeError, Exception) as exc:
        c.print(f'  [red]✗  cf: {exc}[/]')
        exit_code = 1

    # 4 — CF Function (depends on CF distribution; async ~5min for edge propagation)
    c.print('  [yellow]→[/]  cf-function create…')
    try:
        fnrep = _cf_function().create(zone=zone)
        icon = '[green]✓[/]' if fnrep.state == Enum__Setup__State.OK else '[yellow]⚠ (CF edge propagating)[/]'
        c.print(f'  {icon}  cf-function  {fnrep.function_name}')
    except (ClientError, RuntimeError, Exception) as exc:
        c.print(f'  [red]✗  cf-function: {exc}[/]')
        exit_code = 1

    # 5 — DNS (depends on CF domain)
    c.print('  [yellow]→[/]  dns create…')
    try:
        drep = _dns().create(zone=zone)
        icon = '[green]✓[/]' if drep.state == Enum__Setup__State.OK else '[yellow]⚠[/]'
        c.print(f'  {icon}  dns  {drep.record_value or drep.record_name}')
        if drep.state not in (Enum__Setup__State.OK,):
            exit_code = 1
    except (ClientError, RuntimeError, Exception) as exc:
        c.print(f'  [red]✗  dns: {exc}[/]')
        exit_code = 1

    c.print()
    if exit_code:
        raise typer.Exit(exit_code)


@app.command(name='update', help='Update/redeploy all vault-publish resources.')
def setup_update(
    zone    : str  = typer.Option(DEFAULT_ZONE,     '--zone',     help='DNS apex zone'),
    cert_arn: str  = typer.Option(DEFAULT_CERT_ARN, '--cert-arn', help='ACM certificate ARN'),
    yes     : bool = typer.Option(False, '--yes', '-y', help='Skip confirmation'),
):
    c = Console(highlight=False)
    iam = _iam()
    _print_role_notice(c, iam)
    if not _preflight(c, iam):
        raise typer.Exit(1)
    if not yes:
        typer.confirm('\n  Update all vault-publish resources?', default=True, abort=True)

    exit_code = 0
    c.print()

    c.print('  [yellow]→[/]  iam update…')
    try:
        rep  = iam.update()
        icon = '[green]✓[/]' if rep.state == Enum__Setup__State.OK else '[yellow]⚠[/]'
        c.print(f'  {icon}  iam')
    except (ClientError, RuntimeError, Exception) as exc:
        c.print(f'  [red]✗  iam: {exc}[/]')
        exit_code = 1

    c.print('  [yellow]→[/]  lambda update…')
    try:
        lrep = _lambda().update()
        icon = '[green]✓[/]' if lrep.state == Enum__Setup__State.OK else '[yellow]⚠[/]'
        c.print(f'  {icon}  lambda  {lrep.function_url or lrep.function_name}')
    except (ClientError, RuntimeError, Exception) as exc:
        c.print(f'  [red]✗  lambda: {exc}[/]')
        exit_code = 1

    c.print('  [yellow]→[/]  cf update (ensure)…')
    try:
        crep = _cf().create(zone=zone, cert_arn=cert_arn)
        icon = '[green]✓[/]' if crep.state == Enum__Setup__State.OK else '[yellow]⚠[/]'
        c.print(f'  {icon}  cf  {crep.domain_name or crep.distribution_id}')
    except (ClientError, RuntimeError, Exception) as exc:
        c.print(f'  [red]✗  cf: {exc}[/]')
        exit_code = 1

    c.print('  [yellow]→[/]  cf-function update (ensure)…')
    try:
        fnrep = _cf_function().update(zone=zone)
        icon = '[green]✓[/]' if fnrep.state == Enum__Setup__State.OK else '[yellow]⚠ (CF edge propagating)[/]'
        c.print(f'  {icon}  cf-function  {fnrep.function_name}')
    except (ClientError, RuntimeError, Exception) as exc:
        c.print(f'  [red]✗  cf-function: {exc}[/]')
        exit_code = 1

    c.print('  [yellow]→[/]  dns update (ensure)…')
    try:
        drep = _dns().create(zone=zone)
        icon = '[green]✓[/]' if drep.state == Enum__Setup__State.OK else '[yellow]⚠[/]'
        c.print(f'  {icon}  dns  {drep.record_value or drep.record_name}')
    except (ClientError, RuntimeError, Exception) as exc:
        c.print(f'  [red]✗  dns: {exc}[/]')
        exit_code = 1

    c.print()
    if exit_code:
        raise typer.Exit(exit_code)


@app.command(name='delete', help='Delete all vault-publish resources (reverse dependency order).')
def setup_delete(
    zone: str  = typer.Option(DEFAULT_ZONE, '--zone', help='DNS apex zone'),
    yes : bool = typer.Option(False, '--yes', '-y', help='Skip confirmation'),
):
    c = Console(highlight=False)
    iam = _iam()
    _print_role_notice(c, iam)
    if not _preflight(c, iam):
        raise typer.Exit(1)
    if not yes:
        typer.confirm(
            f"\n  Delete ALL vault-publish resources for zone '{zone}'? This cannot be undone.",
            default=False, abort=True)

    c.print()
    exit_code = 0

    for label, fn in [
        ('dns',         lambda: _dns().delete(zone)),
        ('cf-function', lambda: _cf_function().delete(zone)),
        ('cf',          lambda: _cf().delete(zone)),
        ('lambda',      lambda: _lambda().delete()),
        ('iam',         lambda: iam.delete()),
    ]:
        c.print(f'  [yellow]→[/]  {label} delete…')
        try:
            ok   = fn()
            icon = '[green]✓[/]' if ok else '[yellow]⚠ (already absent or skipped)[/]'
            c.print(f'  {icon}  {label}')
        except (ClientError, RuntimeError, Exception) as exc:
            c.print(f'  [red]✗  {label}: {exc}[/]')
            exit_code = 1

    c.print()
    if exit_code:
        raise typer.Exit(exit_code)


# ═══════════════════════════════════════════════════════════════════════════════
# sg vault-publish setup iam *
# ═══════════════════════════════════════════════════════════════════════════════

@iam_app.command(name='check', help='Check live IAM role vs Waker__Policy__Template.')
def iam_check(output_json: bool = typer.Option(False, '--json', help='Machine-readable JSON output')):
    c   = Console(highlight=False)
    svc = _iam()
    _print_role_notice(c, svc)
    if not _preflight(c, svc):
        raise typer.Exit(1)
    try:
        rep = svc.check()
    except ClientError as exc:
        _print_aws_error(c, exc)
        raise typer.Exit(1)
    except Exception as exc:
        c.print(f'  [red]✗  {exc}[/]')
        raise typer.Exit(1)

    if output_json:
        c.print(json.dumps({
            'state'              : str(rep.state),
            'role_name'          : rep.role_name,
            'role_arn'           : rep.role_arn,
            'role_exists'        : rep.role_exists,
            'policy_name'        : rep.policy_name,
            'policy_matches'     : rep.policy_matches,
            'trust_policy_ok'    : rep.trust_policy_ok,
            'missing_statements' : rep.missing_statements,
            'extra_statements'   : rep.extra_statements,
            'issues'             : [{'severity': i.severity, 'area': i.area, 'message': i.message}
                                     for i in rep.issues],
        }, indent=2))
        if rep.state != Enum__Setup__State.OK:
            raise typer.Exit(1)
        return

    _print_iam_report(c, rep)
    if rep.state != Enum__Setup__State.OK:
        raise typer.Exit(1)


@iam_app.command(name='status', help='Pretty-print live IAM role configuration.')
def iam_status():
    c   = Console(highlight=False)
    svc = _iam()
    _print_role_notice(c, svc)
    if not _preflight(c, svc):
        raise typer.Exit(1)
    try:
        info = svc.status()
    except ClientError as exc:
        _print_aws_error(c, exc)
        raise typer.Exit(1)
    except Exception as exc:
        c.print(f'  [red]✗  {exc}[/]')
        raise typer.Exit(1)
    c.print()
    for k, v in info.items():
        c.print(f'  {k:<22}: {v}')
    c.print()


@iam_app.command(name='create', help='Create waker IAM role + policy. Requires SG_AWS__VAULT_PUBLISH__SETUP__ALLOW_MUTATIONS=1.')
def iam_create():
    c   = Console(highlight=False)
    svc = _iam()
    _print_role_notice(c, svc)
    if not _preflight(c, svc):
        raise typer.Exit(1)
    c.print('\n  [yellow]→[/]  Creating IAM role…')
    try:
        rep = svc.create()
    except (RuntimeError, ClientError, Exception) as exc:
        _handle_exc(c, exc)
        raise typer.Exit(1)
    _print_iam_report(c, rep)
    if rep.state == Enum__Setup__State.OK:
        c.print('  [green]✓[/]  IAM role ready')
    c.print()


@iam_app.command(name='update', help='Sync inline policy with Waker__Policy__Template. Requires SG_AWS__VAULT_PUBLISH__SETUP__ALLOW_MUTATIONS=1.')
def iam_update():
    c   = Console(highlight=False)
    svc = _iam()
    _print_role_notice(c, svc)
    if not _preflight(c, svc):
        raise typer.Exit(1)
    c.print('\n  [yellow]→[/]  Updating IAM inline policy…')
    try:
        rep = svc.update()
    except (RuntimeError, ClientError, Exception) as exc:
        _handle_exc(c, exc)
        raise typer.Exit(1)
    _print_iam_report(c, rep)
    if rep.state == Enum__Setup__State.OK:
        c.print('  [green]✓[/]  Policy updated and matches template')
    c.print()


@iam_app.command(name='delete', help='Delete waker IAM role. Requires SG_AWS__VAULT_PUBLISH__SETUP__ALLOW_DELETES=1.')
def iam_delete(yes: bool = typer.Option(False, '--yes', '-y', help='Skip confirmation')):
    c   = Console(highlight=False)
    svc = _iam()
    _print_role_notice(c, svc)
    if not _preflight(c, svc):
        raise typer.Exit(1)
    if not yes:
        typer.confirm('\n  Delete waker IAM role? This cannot be undone.', default=False, abort=True)
    c.print('\n  [yellow]→[/]  Deleting IAM role…')
    try:
        svc.delete()
    except (RuntimeError, ClientError, Exception) as exc:
        _handle_exc(c, exc)
        raise typer.Exit(1)
    c.print('  [green]✓[/]  IAM role deleted')
    c.print()


# ═══════════════════════════════════════════════════════════════════════════════
# sg vault-publish setup lambda *
# ═══════════════════════════════════════════════════════════════════════════════

@lambda_app.command(name='check', help='Check Lambda waker function vs expected config.')
def lambda_check():
    c   = Console(highlight=False)
    svc = _iam()
    _print_role_notice(c, svc)
    if not _preflight(c, svc):
        raise typer.Exit(1)
    try:
        rep = _lambda().check()
    except (ClientError, Exception) as exc:
        _handle_exc(c, exc)
        raise typer.Exit(1)
    _print_lambda_report(c, rep)
    if rep.state != Enum__Setup__State.OK:
        raise typer.Exit(1)


@lambda_app.command(name='status', help='Pretty-print live Lambda function configuration.')
def lambda_status():
    c   = Console(highlight=False)
    svc = _iam()
    _print_role_notice(c, svc)
    if not _preflight(c, svc):
        raise typer.Exit(1)
    try:
        info = _lambda().status()
    except (ClientError, Exception) as exc:
        _handle_exc(c, exc)
        raise typer.Exit(1)
    c.print()
    for k, v in info.items():
        c.print(f'  {k:<22}: {v}')
    c.print()


@lambda_app.command(name='create', help='Deploy Lambda waker function. Requires SG_AWS__VAULT_PUBLISH__SETUP__ALLOW_MUTATIONS=1.')
def lambda_create(role_arn: str = typer.Option('', '--role-arn', help='Lambda execution role ARN')):
    c   = Console(highlight=False)
    svc = _iam()
    _print_role_notice(c, svc)
    if not _preflight(c, svc):
        raise typer.Exit(1)
    c.print('\n  [yellow]→[/]  Deploying Lambda waker…\n')
    try:
        rep = _run_with_lambda_progress(c, lambda cb: _lambda().create(role_arn=role_arn, progress=cb))
    except (RuntimeError, ClientError, Exception) as exc:
        _handle_exc(c, exc)
        raise typer.Exit(1)
    _print_lambda_report(c, rep)
    if rep.state == Enum__Setup__State.OK:
        c.print('  [green]✓[/]  Lambda waker ready')
    c.print()


@lambda_app.command(name='update', help='Redeploy Lambda waker function. Requires SG_AWS__VAULT_PUBLISH__SETUP__ALLOW_MUTATIONS=1.')
def lambda_update(
    invoke: bool = typer.Option(False, '--invoke', help='After a successful deploy, immediately invoke /__waker__/deploy and print the JSON response so you can confirm the new version is live.'),
):
    c   = Console(highlight=False)
    svc = _iam()
    _print_role_notice(c, svc)
    if not _preflight(c, svc):
        raise typer.Exit(1)
    c.print('\n  [yellow]→[/]  Redeploying Lambda waker…\n')
    try:
        rep = _run_with_lambda_progress(c, lambda cb: _lambda().update(progress=cb))
    except (RuntimeError, ClientError, Exception) as exc:
        _handle_exc(c, exc)
        raise typer.Exit(1)
    _print_lambda_report(c, rep)
    if rep.state == Enum__Setup__State.OK:
        c.print('  [green]✓[/]  Lambda waker updated')
    c.print()
    if invoke and rep.state == Enum__Setup__State.OK:
        _do_lambda_invoke(c, path='/__waker__/deploy', host='', method='GET', full=True)


@lambda_app.command(name='cmd', help='Invoke a Waker debug RPC command (dev-only). Use `cmd help` to list commands. Args as key=value pairs.')
def lambda_cmd(
    name: str = typer.Argument(..., help='Command name (e.g. health, env, find-slug, describe-instance, regions, cache).'),
    args: List[str] = typer.Argument(None, help='Optional key=value args (e.g. slug=aaaaa iid=i-0123).'),
    full: bool = typer.Option(True, '--full/--no-full', help='Print full JSON response (default true).'),
):
    import urllib.parse
    c   = Console(highlight=False)
    svc = _iam()
    _print_role_notice(c, svc)
    if not _preflight(c, svc):
        raise typer.Exit(1)
    qs_pairs = [('name', name)]
    for kv in (args or []):
        if '=' not in kv:
            c.print(f'  [yellow]⚠[/]  ignoring arg {kv!r} — must be key=value')
            continue
        k, v = kv.split('=', 1)
        qs_pairs.append((k, v))
    qs   = urllib.parse.urlencode(qs_pairs)
    path = f'/__waker__/cmd?{qs}'
    # Custom renderer for `cmd help` — show a Rich table instead of raw JSON
    if name == 'help':
        _do_lambda_invoke(c, path=path, host='', method='GET', full=full,
                          body_renderer=_render_cmd_help_table)
    else:
        _do_lambda_invoke(c, path=path, host='', method='GET', full=full)


def _render_cmd_help_table(c: Console, body_json: dict) -> None:
    """Render the `cmd help` response as a Rich table."""
    rows = body_json.get('result', []) if isinstance(body_json, dict) else []
    if not rows:
        c.print('  [yellow]no commands returned[/]')
        return
    tbl = Table(box=None, show_header=True, padding=(0, 2))
    tbl.add_column('Command',     style='bold cyan')
    tbl.add_column('Mutates',     style='', justify='center')
    tbl.add_column('Description', style='dim')
    for row in rows:
        mutates = row.get('mutates', False)
        flag    = '[red]●[/]' if mutates else '[dim]·[/]'
        tbl.add_row(row.get('name', '?'), flag, row.get('description', ''))
    c.print()
    c.print(tbl)
    c.print()
    c.print('  [dim]Mutating commands ([red]●[/dim][dim]) require '
            'WAKER_CMD_MUTATIONS_ENABLED=1 on the Lambda env.[/]')
    c.print()


@lambda_app.command(name='invoke', help='Invoke the deployed waker Lambda with a synthetic event and print the JSON response. Defaults to /__waker__/deploy so you immediately see which version is live.')
def lambda_invoke(
    path  : str = typer.Option('/__waker__/deploy', '--path', '-p', help='Request path on the Lambda'),
    host  : str = typer.Option('',                  '--host', '-H', help='Override the synthetic Host header (defaults to the Lambda URL hostname)'),
    method: str = typer.Option('GET',               '--method', '-m'),
    full  : bool = typer.Option(False, '--full', help='Print the full response body (default: truncate to first 800 chars)'),
):
    c   = Console(highlight=False)
    svc = _iam()
    _print_role_notice(c, svc)
    if not _preflight(c, svc):
        raise typer.Exit(1)
    _do_lambda_invoke(c, path=path, host=host, method=method, full=full)


def _do_lambda_invoke(c: Console, *, path: str, host: str, method: str, full: bool,
                       body_renderer=None) -> None:
    """Shared invoke implementation — used by `lambda invoke`, `lambda cmd`,
    and `lambda update --invoke`. Pre-flight (credential check) is the
    caller's responsibility so this helper stays a thin transport layer.

    body_renderer(c, body_json) — optional callable that takes the parsed
    JSON body and renders it however it likes. When set, replaces the
    default pretty-printed JSON. Falls back to the default if the body
    isn't valid JSON.
    """
    import json, uuid, boto3
    from datetime import datetime, timezone
    from sg_compute_specs.vault_publish.setup.service.Setup__Lambda import WAKER_LAMBDA_NAME

    # Resolve the effective Host header — by default we mimic what AWS itself
    # would send when someone hits the Function URL directly.
    if not host:
        try:
            from sgraph_ai_service_playwright__cli.aws.lambda_.service.Lambda__AWS__Client import Lambda__AWS__Client
            url_info = Lambda__AWS__Client().get_function_url(WAKER_LAMBDA_NAME)
            host = str(url_info.function_url).removeprefix('https://').rstrip('/')
        except Exception:
            host = WAKER_LAMBDA_NAME

    # Split path into rawPath + rawQueryString so the Lambda event mirrors
    # what AWS Function URLs actually send (and so command args land in the
    # right field for /__waker__/cmd query parsing).
    if '?' in path:
        raw_path, raw_qs = path.split('?', 1)
    else:
        raw_path, raw_qs = path, ''

    now   = datetime.now(timezone.utc)
    event = {
        'version'       : '2.0',
        'rawPath'       : raw_path,
        'rawQueryString': raw_qs,
        'headers'       : {'host': host, 'user-agent': 'sg-vp-setup-lambda-invoke/0.1'},
        'requestContext': {
            'http'     : {'method': method, 'path': raw_path, 'sourceIp': '127.0.0.1'},
            'requestId': f'sg-invoke-{uuid.uuid4().hex[:8]}',
            'time'     : now.strftime('%d/%b/%Y:%H:%M:%S +0000'),
        },
        'body'           : None,
        'isBase64Encoded': False,
    }

    c.print(f'\n  [yellow]→[/]  invoke [bold]{WAKER_LAMBDA_NAME}[/]  path={path}  host={host}')
    try:
        from sgraph_ai_service_playwright__cli.aws._shared.Aws__Region__Resolver import Aws__Region__Resolver
        lam     = boto3.client('lambda', region_name=str(Aws__Region__Resolver().resolve()))
        resp    = lam.invoke(
            FunctionName   = WAKER_LAMBDA_NAME,
            InvocationType = 'RequestResponse',
            Payload        = json.dumps(event).encode(),
        )
        payload = json.loads(resp['Payload'].read())
    except (ClientError, Exception) as exc:
        _handle_exc(c, exc)
        raise typer.Exit(1)

    status = payload.get('statusCode', 0)
    hdrs   = payload.get('headers', {})
    body   = payload.get('body', '')

    c.print()
    c.print(f'  status: [bold]{status}[/]')
    c.print('  X-Waker headers:')
    for k, v in sorted(hdrs.items()):
        if k.lower().startswith('x-waker'):
            c.print(f'    [dim]{k}[/]: {v}')

    # If body looks like JSON, pretty-print it (or hand off to body_renderer);
    # otherwise show as text.
    try:
        parsed = json.loads(body)
        if body_renderer:
            body_renderer(c, parsed)
        else:
            pretty = json.dumps(parsed, indent=2)
            if full or len(pretty) <= 800:
                c.print(f'  body (json):\n{pretty}')
            else:
                c.print(f'  body (json, truncated to 800 chars):\n{pretty[:800]}\n  [dim]…(pass --full for the rest)[/]')
    except (ValueError, TypeError):
        if full or len(body) <= 800:
            c.print(f'  body: {body}')
        else:
            c.print(f'  body size: {len(body)} chars  [dim](pass --full to see body)[/]')
    c.print()


# Ordered list of phases the Lambda deployer emits (label, description).
# Some phases (create-function vs the update path) are mutually exclusive;
# unused ones stay 'pending' and are hidden from the final table.
_LAMBDA_DEPLOY_PHASES = [
    ('build-env'        , 'Compose deploy env vars (version, commit, caller, region)'),
    ('build-zip'        , 'Build deployment ZIP (vault_publish + osbot_utils + osbot_aws)'),
    ('detect-function'  , 'Check whether the function already exists'),
    ('wait-prior-update', 'Wait for any in-flight update on the existing function'),
    ('upload-code'      , 'Upload code to AWS Lambda (update_function_code)'),
    ('wait-upload'      , 'Wait for code upload to settle'),
    ('update-config'    , 'Update function configuration (handler/runtime/memory/env)'),
    ('create-function'  , 'Create new function (first-time deploy)'),
    ('refresh'          , 'Re-read function details for the post-deploy report'),
    ('ensure-url'       , 'Ensure the function URL exists'),
    ('check'            , 'Refresh full report (config + URL + env vars)'),
]


def _run_with_lambda_progress(c: Console, do_deploy):
    """Run a deployer call with a live phase-progress table."""
    import time as _t
    state    = {label: {'status': 'pending', 'started_at': None, 'elapsed': 0.0}
                 for label, _desc in _LAMBDA_DEPLOY_PHASES}
    descs    = dict(_LAMBDA_DEPLOY_PHASES)

    def _build_table() -> Table:
        t = Table(box=None, show_header=True, padding=(0, 2))
        t.add_column('Step',    style='bold')
        t.add_column('Status',  style='')
        t.add_column('Elapsed', style='dim', justify='right')
        t.add_column('Description', style='dim')
        for label, desc in _LAMBDA_DEPLOY_PHASES:
            s = state[label]
            if s['status'] == 'pending':
                continue                                                              # hide untouched phases (some paths skip a subset)
            if s['status'] == 'running':
                icon  = '[yellow]⏳ running…[/]'
                elapsed_s = _t.time() - (s['started_at'] or _t.time())
            else:                                                                     # 'done'
                icon  = '[green]✓ done[/]'
                elapsed_s = s['elapsed']
            t.add_row(label, icon, f'{elapsed_s:.1f}s', desc)
        return t

    with Live(_build_table(), console=c, refresh_per_second=4, transient=False) as live:
        def cb(phase: str, status: str) -> None:
            if phase not in state:
                # Unknown phase — surface it so we don't lose visibility
                state[phase] = {'status': 'pending', 'started_at': None, 'elapsed': 0.0}
                _LAMBDA_DEPLOY_PHASES.append((phase, '(deployer phase)'))
            entry = state[phase]
            now   = _t.time()
            if status == 'start':
                entry['status']     = 'running'
                entry['started_at'] = now
            elif status == 'done':
                entry['status']     = 'done'
                if entry['started_at']:
                    entry['elapsed'] = now - entry['started_at']
            live.update(_build_table())
        return do_deploy(cb)


# ═══════════════════════════════════════════════════════════════════════════════
# sg vault-publish setup cf *
# ═══════════════════════════════════════════════════════════════════════════════

@cf_app.command(name='check', help='Check CloudFront wildcard distribution vs expected state.')
def cf_check(zone: str = typer.Option(DEFAULT_ZONE, '--zone', help='DNS apex zone')):
    c   = Console(highlight=False)
    svc = _iam()
    _print_role_notice(c, svc)
    if not _preflight(c, svc):
        raise typer.Exit(1)
    try:
        rep = _cf().check(zone)
    except (ClientError, Exception) as exc:
        _handle_exc(c, exc)
        raise typer.Exit(1)
    _print_cf_report(c, rep)
    if rep.state != Enum__Setup__State.OK:
        raise typer.Exit(1)


@cf_app.command(name='status', help='Pretty-print live CloudFront distribution.')
def cf_status(zone: str = typer.Option(DEFAULT_ZONE, '--zone', help='DNS apex zone')):
    c   = Console(highlight=False)
    svc = _iam()
    _print_role_notice(c, svc)
    if not _preflight(c, svc):
        raise typer.Exit(1)
    try:
        info = _cf().status(zone)
    except (ClientError, Exception) as exc:
        _handle_exc(c, exc)
        raise typer.Exit(1)
    c.print()
    for k, v in info.items():
        c.print(f'  {k:<22}: {v}')
    c.print()


@cf_app.command(name='create', help='Create CloudFront wildcard distribution. Requires SG_AWS__VAULT_PUBLISH__SETUP__ALLOW_MUTATIONS=1.')
def cf_create(
    zone    : str = typer.Option(DEFAULT_ZONE,     '--zone',     help='DNS apex zone'),
    cert_arn: str = typer.Option(DEFAULT_CERT_ARN, '--cert-arn', help='ACM certificate ARN'),
):
    c   = Console(highlight=False)
    svc = _iam()
    _print_role_notice(c, svc)
    if not _preflight(c, svc):
        raise typer.Exit(1)
    c.print(f'\n  [yellow]→[/]  Creating CloudFront distribution for [bold]*.{zone}[/]…')
    try:
        rep = _cf().create(zone=zone, cert_arn=cert_arn)
    except (RuntimeError, ClientError, Exception) as exc:
        _handle_exc(c, exc)
        raise typer.Exit(1)
    _print_cf_report(c, rep)
    if rep.state == Enum__Setup__State.OK:
        c.print('  [green]✓[/]  CloudFront distribution ready')
    c.print()


# ═══════════════════════════════════════════════════════════════════════════════
# sg vault-publish setup acm *
# ═══════════════════════════════════════════════════════════════════════════════

@acm_app.command(name='check', help='Check ACM wildcard certificate vs expected state.')
def acm_check(zone: str = typer.Option(DEFAULT_ZONE, '--zone', help='DNS apex zone')):
    c   = Console(highlight=False)
    svc = _iam()
    _print_role_notice(c, svc)
    if not _preflight(c, svc):
        raise typer.Exit(1)
    try:
        rep = _acm().check(zone)
    except (ClientError, Exception) as exc:
        _handle_exc(c, exc)
        raise typer.Exit(1)
    _print_acm_report(c, rep)
    if rep.state != Enum__Setup__State.OK:
        raise typer.Exit(1)


@acm_app.command(name='status', help='Pretty-print live ACM certificate.')
def acm_status(zone: str = typer.Option(DEFAULT_ZONE, '--zone', help='DNS apex zone')):
    c   = Console(highlight=False)
    svc = _iam()
    _print_role_notice(c, svc)
    if not _preflight(c, svc):
        raise typer.Exit(1)
    try:
        info = _acm().status(zone)
    except (ClientError, Exception) as exc:
        _handle_exc(c, exc)
        raise typer.Exit(1)
    c.print()
    for k, v in info.items():
        c.print(f'  {k:<22}: {v}')
    c.print()


@acm_app.command(name='request', help='Request ACM wildcard certificate (DNS validation). Requires SG_AWS__VAULT_PUBLISH__SETUP__ALLOW_MUTATIONS=1.')
def acm_request(zone: str = typer.Option(DEFAULT_ZONE, '--zone', help='DNS apex zone')):
    c   = Console(highlight=False)
    svc = _iam()
    _print_role_notice(c, svc)
    if not _preflight(c, svc):
        raise typer.Exit(1)
    c.print(f'\n  [yellow]→[/]  Requesting ACM certificate for [bold]*.{zone}[/]…')
    try:
        rep = _acm().request(zone)
    except (RuntimeError, ClientError, Exception) as exc:
        _handle_exc(c, exc)
        raise typer.Exit(1)
    _print_acm_report(c, rep)
    c.print('  [yellow]⚠[/]  Complete DNS validation in the ACM console, then re-run check.')
    c.print()


# ═══════════════════════════════════════════════════════════════════════════════
# sg vault-publish setup dns *
# ═══════════════════════════════════════════════════════════════════════════════

@dns_app.command(name='check', help='Check Route 53 wildcard DNS record vs expected state.')
def dns_check(zone: str = typer.Option(DEFAULT_ZONE, '--zone', help='DNS apex zone')):
    c   = Console(highlight=False)
    svc = _iam()
    _print_role_notice(c, svc)
    if not _preflight(c, svc):
        raise typer.Exit(1)
    try:
        rep = _dns().check(zone)
    except (ClientError, Exception) as exc:
        _handle_exc(c, exc)
        raise typer.Exit(1)
    _print_dns_report(c, rep)
    if rep.state != Enum__Setup__State.OK:
        raise typer.Exit(1)


@dns_app.command(name='status', help='Pretty-print live Route 53 DNS record.')
def dns_status(zone: str = typer.Option(DEFAULT_ZONE, '--zone', help='DNS apex zone')):
    c   = Console(highlight=False)
    svc = _iam()
    _print_role_notice(c, svc)
    if not _preflight(c, svc):
        raise typer.Exit(1)
    try:
        info = _dns().status(zone)
    except (ClientError, Exception) as exc:
        _handle_exc(c, exc)
        raise typer.Exit(1)
    c.print()
    for k, v in info.items():
        c.print(f'  {k:<22}: {v}')
    c.print()


@dns_app.command(name='create', help='Create/upsert Route 53 wildcard CNAME record. Requires SG_AWS__VAULT_PUBLISH__SETUP__ALLOW_MUTATIONS=1.')
def dns_create(zone: str = typer.Option(DEFAULT_ZONE, '--zone', help='DNS apex zone')):
    c   = Console(highlight=False)
    svc = _iam()
    _print_role_notice(c, svc)
    if not _preflight(c, svc):
        raise typer.Exit(1)
    c.print(f'\n  [yellow]→[/]  Upserting Route 53 CNAME for [bold]*.{zone}[/]…')
    try:
        rep = _dns().create(zone)
    except (RuntimeError, ClientError, Exception) as exc:
        _handle_exc(c, exc)
        raise typer.Exit(1)
    _print_dns_report(c, rep)
    if rep.state == Enum__Setup__State.OK:
        c.print(f'  [green]✓[/]  DNS record ready: *.{zone} → {rep.record_value}')
    c.print()


@dns_app.command(name='delete', help='Delete Route 53 wildcard CNAME record. Requires SG_AWS__VAULT_PUBLISH__SETUP__ALLOW_DELETES=1.')
def dns_delete(
    zone: str  = typer.Option(DEFAULT_ZONE, '--zone', help='DNS apex zone'),
    yes : bool = typer.Option(False, '--yes', '-y', help='Skip confirmation'),
):
    c   = Console(highlight=False)
    svc = _iam()
    _print_role_notice(c, svc)
    if not _preflight(c, svc):
        raise typer.Exit(1)
    if not yes:
        typer.confirm(f'\n  Delete *.{zone} CNAME record?', default=False, abort=True)
    c.print(f'\n  [yellow]→[/]  Deleting Route 53 CNAME for [bold]*.{zone}[/]…')
    try:
        ok = _dns().delete(zone)
    except (RuntimeError, ClientError, Exception) as exc:
        _handle_exc(c, exc)
        raise typer.Exit(1)
    if ok:
        c.print(f'  [green]✓[/]  DNS record deleted')
    else:
        c.print(f'  [yellow]⚠[/]  record not found or already absent')
    c.print()


# ═══════════════════════════════════════════════════════════════════════════════
# Render helpers
# ═══════════════════════════════════════════════════════════════════════════════

_STATE_ICON = {
    Enum__Setup__State.OK      : '[green]✓ OK[/]',
    Enum__Setup__State.MISSING : '[red]✗ MISSING[/]',
    Enum__Setup__State.DRIFT   : '[yellow]⚠ DRIFT[/]',
    Enum__Setup__State.ERROR   : '[red]✗ ERROR[/]',
    Enum__Setup__State.UNKNOWN : '[dim]? UNKNOWN[/]',
}


def _add_area_row(tbl: Table, area: str, state: Enum__Setup__State, detail: str = '') -> None:
    tbl.add_row(area, _STATE_ICON.get(state, str(state)), detail)


def _print_iam_report(c: Console, rep) -> None:
    c.print()
    icon = _STATE_ICON.get(rep.state, str(rep.state))
    c.print(f'  IAM role: [bold]{rep.role_name}[/]  {icon}')
    if rep.role_arn:
        c.print(f'  ARN     : {rep.role_arn}')
    if rep.missing_statements:
        c.print(f'  [red]Missing : {rep.missing_statements}[/]')
    if rep.extra_statements:
        c.print(f'  [yellow]Extra   : {rep.extra_statements}[/]')
    for issue in rep.issues:
        sev_colour = {'error': 'red', 'warn': 'yellow', 'info': 'dim'}.get(issue.severity, 'white')
        c.print(f'  [{sev_colour}]{issue.severity.upper()}: {issue.message}[/]')


def _print_lambda_report(c: Console, rep) -> None:
    c.print()
    icon = _STATE_ICON.get(rep.state, str(rep.state))
    c.print(f'  Lambda: [bold]{rep.function_name}[/]  {icon}')
    if rep.function_arn:
        c.print(f'  ARN          : {rep.function_arn}')
    if rep.function_url:
        c.print(f'  Function URL : {rep.function_url}')
    if rep.handler:
        c.print(f'  Handler      : {rep.handler}')
    if rep.runtime or rep.memory_size or rep.timeout:
        c.print(f'  Runtime      : {rep.runtime}  '
                f'memory={rep.memory_size}MB  timeout={rep.timeout}s')
    if rep.code_size or rep.zip_size:
        line = f'  Code size    : {_human_bytes(rep.code_size)} on AWS'
        if rep.zip_size:
            line += f'  (uploaded this round: {_human_bytes(rep.zip_size)})'
        c.print(line)
    if rep.last_modified:
        c.print(f'  Last modified: {rep.last_modified}')
    if rep.deploy_env:
        c.print('  [dim]Deploy env vars (live):[/]')
        for line in rep.deploy_env.splitlines():
            c.print(f'    [dim]{line}[/]')
    for issue in rep.issues:
        sev_colour = {'error': 'red', 'warn': 'yellow', 'info': 'dim'}.get(issue.severity, 'white')
        c.print(f'  [{sev_colour}]{issue.severity.upper()}: {issue.message}[/]')


def _human_bytes(n: int) -> str:
    n = int(n or 0)
    if n < 1024:
        return f'{n}B'
    if n < 1024 * 1024:
        return f'{n / 1024:.1f}KB'
    return f'{n / (1024 * 1024):.2f}MB'


def _print_cf_report(c: Console, rep) -> None:
    c.print()
    icon = _STATE_ICON.get(rep.state, str(rep.state))
    c.print(f'  CloudFront: [bold]*.{rep.zone}[/]  {icon}')
    if rep.distribution_id:
        c.print(f'  Distribution: {rep.distribution_id}')
    if rep.domain_name:
        c.print(f'  Domain      : {rep.domain_name}')
    for issue in rep.issues:
        sev_colour = {'error': 'red', 'warn': 'yellow', 'info': 'dim'}.get(issue.severity, 'white')
        c.print(f'  [{sev_colour}]{issue.severity.upper()}: {issue.message}[/]')


def _print_acm_report(c: Console, rep) -> None:
    c.print()
    icon = _STATE_ICON.get(rep.state, str(rep.state))
    c.print(f'  ACM: [bold]*.{rep.zone}[/]  {icon}')
    if rep.cert_arn:
        c.print(f'  ARN   : {rep.cert_arn}')
    if rep.cert_status:
        c.print(f'  Status: {rep.cert_status}')
    for issue in rep.issues:
        sev_colour = {'error': 'red', 'warn': 'yellow', 'info': 'dim'}.get(issue.severity, 'white')
        c.print(f'  [{sev_colour}]{issue.severity.upper()}: {issue.message}[/]')


def _print_dns_report(c: Console, rep) -> None:
    c.print()
    icon = _STATE_ICON.get(rep.state, str(rep.state))
    c.print(f'  DNS: [bold]{rep.record_name}[/]  {icon}')
    if rep.record_value:
        c.print(f'  CNAME → {rep.record_value}')
    for issue in rep.issues:
        sev_colour = {'error': 'red', 'warn': 'yellow', 'info': 'dim'}.get(issue.severity, 'white')
        c.print(f'  [{sev_colour}]{issue.severity.upper()}: {issue.message}[/]')


def _handle_exc(c: Console, exc: Exception) -> None:
    if isinstance(exc, ClientError):
        _print_aws_error(c, exc)
    else:
        c.print(f'  [red]✗  {exc}[/]')


# ═══════════════════════════════════════════════════════════════════════════════
# sg vault-publish setup ec2 *
# ═══════════════════════════════════════════════════════════════════════════════

@ec2_app.command(name='check', help='Check EC2 prerequisites (IAM instance profile + base AMI).')
def ec2_check():
    c   = Console(highlight=False)
    svc = _iam()
    _print_role_notice(c, svc)
    if not _preflight(c, svc):
        raise typer.Exit(1)
    try:
        rep = _ec2().check()
    except (ClientError, Exception) as exc:
        _handle_exc(c, exc)
        raise typer.Exit(1)
    _print_ec2_report(c, rep)
    if rep.state != Enum__Setup__State.OK:
        raise typer.Exit(1)


@ec2_app.command(name='status', help='Pretty-print live EC2 prerequisite state.')
def ec2_status():
    c   = Console(highlight=False)
    svc = _iam()
    _print_role_notice(c, svc)
    if not _preflight(c, svc):
        raise typer.Exit(1)
    try:
        info = _ec2().status()
    except (ClientError, Exception) as exc:
        _handle_exc(c, exc)
        raise typer.Exit(1)
    c.print()
    for k, v in info.items():
        c.print(f'  {k:<22}: {v}')
    c.print()


# ═══════════════════════════════════════════════════════════════════════════════
# sg vault-publish setup cf-function *
# ═══════════════════════════════════════════════════════════════════════════════

@cf_function_app.command(name='check', help='Check the viewer-Host CF Function: deployed, published, attached.')
def cf_function_check(zone: str = typer.Option(DEFAULT_ZONE, '--zone', help='DNS apex zone')):
    c   = Console(highlight=False)
    svc = _iam()
    _print_role_notice(c, svc)
    if not _preflight(c, svc):
        raise typer.Exit(1)
    try:
        rep = _cf_function().check(zone)
    except (ClientError, Exception) as exc:
        _handle_exc(c, exc)
        raise typer.Exit(1)
    _print_cf_function_report(c, rep)
    if rep.state != Enum__Setup__State.OK:
        raise typer.Exit(1)


@cf_function_app.command(name='status', help='Pretty-print live CF Function config + attachment.')
def cf_function_status(zone: str = typer.Option(DEFAULT_ZONE, '--zone', help='DNS apex zone')):
    c   = Console(highlight=False)
    svc = _iam()
    _print_role_notice(c, svc)
    if not _preflight(c, svc):
        raise typer.Exit(1)
    try:
        info = _cf_function().status(zone)
    except (ClientError, Exception) as exc:
        _handle_exc(c, exc)
        raise typer.Exit(1)
    c.print()
    for k, v in info.items():
        c.print(f'  {k:<22}: {v}')
    c.print()


@cf_function_app.command(name='create', help='Create + publish + attach the CF Function. Requires SG_AWS__VAULT_PUBLISH__SETUP__ALLOW_MUTATIONS=1.')
def cf_function_create(zone: str = typer.Option(DEFAULT_ZONE, '--zone', help='DNS apex zone')):
    c   = Console(highlight=False)
    svc = _iam()
    _print_role_notice(c, svc)
    if not _preflight(c, svc):
        raise typer.Exit(1)
    c.print(f'\n  [yellow]→[/]  Deploying CF Function for [bold]*.{zone}[/]…')
    c.print('  [dim](CloudFront edge propagation takes ~5min; this command returns immediately.)[/]')
    try:
        rep = _cf_function().create(zone)
    except (RuntimeError, ClientError, Exception) as exc:
        _handle_exc(c, exc)
        raise typer.Exit(1)
    _print_cf_function_report(c, rep)
    c.print('  [dim]Run `sg vp setup cf-function check` after a few minutes to confirm attachment.[/]')
    c.print()


@cf_function_app.command(name='update', help='Re-publish CF Function code + ensure attachment. Requires SG_AWS__VAULT_PUBLISH__SETUP__ALLOW_MUTATIONS=1.')
def cf_function_update(zone: str = typer.Option(DEFAULT_ZONE, '--zone', help='DNS apex zone')):
    c   = Console(highlight=False)
    svc = _iam()
    _print_role_notice(c, svc)
    if not _preflight(c, svc):
        raise typer.Exit(1)
    c.print(f'\n  [yellow]→[/]  Updating CF Function for [bold]*.{zone}[/]…')
    try:
        rep = _cf_function().update(zone)
    except (RuntimeError, ClientError, Exception) as exc:
        _handle_exc(c, exc)
        raise typer.Exit(1)
    _print_cf_function_report(c, rep)
    c.print()


@cf_function_app.command(name='show', help='Dump the live CF Function source code (LIVE stage) and the expected source side-by-side.')
def cf_function_show():
    from sg_compute_specs.vault_publish.setup.service.Setup__CF__Function       import FUNCTION_NAME, FUNCTION_CODE, _normalise
    from sgraph_ai_service_playwright__cli.aws.cf.service.CloudFront__Function__AWS__Client import CloudFront__Function__AWS__Client

    c   = Console(highlight=False)
    svc = _iam()
    _print_role_notice(c, svc)
    if not _preflight(c, svc):
        raise typer.Exit(1)
    try:
        live_code = CloudFront__Function__AWS__Client().get_code(FUNCTION_NAME, stage='LIVE')
    except (ClientError, Exception) as exc:
        _handle_exc(c, exc)
        raise typer.Exit(1)

    c.print()
    c.print(f'  [bold]Expected[/]  ({len(FUNCTION_CODE)} bytes)')
    c.print(f'  [dim]{"─" * 60}[/]')
    for line in FUNCTION_CODE.splitlines():
        c.print(f'  {line}')

    c.print()
    c.print(f'  [bold]Live[/]      ({len(live_code)} bytes)')
    c.print(f'  [dim]{"─" * 60}[/]')
    if not live_code:
        c.print('  [dim](function not deployed)[/]')
    else:
        for line in live_code.splitlines():
            c.print(f'  {line}')

    c.print()
    match = _normalise(live_code) == _normalise(FUNCTION_CODE)
    c.print(f'  Normalised match: {"[green]yes[/]" if match else "[red]no[/]"}')
    if not match and live_code:
        # Find first differing position after normalisation for a hint
        n_live = _normalise(live_code)
        n_exp  = _normalise(FUNCTION_CODE)
        first_diff = next((i for i, (a, b) in enumerate(zip(n_exp, n_live)) if a != b),
                           min(len(n_exp), len(n_live)))
        c.print(f'  First diff at normalised char {first_diff}:')
        c.print(f'    expected: …{n_exp[max(0, first_diff-15):first_diff+30]!r}')
        c.print(f'    live    : …{n_live[max(0, first_diff-15):first_diff+30]!r}')
    c.print()


@cf_function_app.command(name='delete', help='Detach + delete the CF Function. Requires SG_AWS__VAULT_PUBLISH__SETUP__ALLOW_DELETES=1.')
def cf_function_delete(
    zone: str  = typer.Option(DEFAULT_ZONE, '--zone', help='DNS apex zone'),
    yes : bool = typer.Option(False, '--yes', '-y', help='Skip confirmation'),
):
    c   = Console(highlight=False)
    svc = _iam()
    _print_role_notice(c, svc)
    if not _preflight(c, svc):
        raise typer.Exit(1)
    if not yes:
        typer.confirm('\n  Detach and delete the viewer-Host CF Function?', default=False, abort=True)
    c.print('\n  [yellow]→[/]  Deleting CF Function…')
    try:
        ok = _cf_function().delete(zone)
    except (RuntimeError, ClientError, Exception) as exc:
        _handle_exc(c, exc)
        raise typer.Exit(1)
    if ok:
        c.print('  [green]✓[/]  CF Function deleted')
    else:
        c.print('  [yellow]⚠[/]  Function still present — CF edge may still be propagating; retry in ~5min')
    c.print()


# ── extra render helpers ─────────────────────────────────────────────────────

def _print_ec2_report(c: Console, rep) -> None:
    c.print()
    icon = _STATE_ICON.get(rep.state, str(rep.state))
    c.print(f'  EC2 prereqs  {icon}')
    c.print(f'  Region        : {rep.region}')
    c.print(f'  Profile       : {rep.profile_name}  ({"yes" if rep.profile_exists else "no"})')
    if rep.profile_arn:
        c.print(f'  Profile ARN   : {rep.profile_arn}')
    c.print(f'  AMI           : {rep.ami_id or "(not resolvable)"}')
    for issue in rep.issues:
        sev_colour = {'error': 'red', 'warn': 'yellow', 'info': 'dim'}.get(issue.severity, 'white')
        c.print(f'  [{sev_colour}]{issue.severity.upper()}: {issue.message}[/]')


def _print_cf_function_report(c: Console, rep) -> None:
    c.print()
    icon = _STATE_ICON.get(rep.state, str(rep.state))
    c.print(f'  CF Function: [bold]{rep.function_name}[/]  {icon}')
    if rep.function_arn:
        c.print(f'  ARN          : {rep.function_arn}')
    c.print(f'  Stage        : {rep.function_stage or "(none)"}')
    c.print(f'  Code matches : {"yes" if rep.code_matches else "no"}')
    c.print(f'  Attached     : {"yes" if rep.attached else "no"}'
            + (f'  → {rep.distribution_id}' if rep.distribution_id else ''))
    for issue in rep.issues:
        sev_colour = {'error': 'red', 'warn': 'yellow', 'info': 'dim'}.get(issue.severity, 'white')
        c.print(f'  [{sev_colour}]{issue.severity.upper()}: {issue.message}[/]')


# ═══════════════════════════════════════════════════════════════════════════════
# sg vault-publish setup admin-iam *
# ═══════════════════════════════════════════════════════════════════════════════

@admin_iam_app.command(name='check', help='Check live admin IAM role vs Admin__Policy__Template.')
def admin_iam_check(output_json: bool = typer.Option(False, '--json')):
    c   = Console(highlight=False)
    svc = _admin_iam()
    _print_role_notice(c, svc)
    if not _preflight(c, _iam()):       # share preflight with the waker IAM setup
        raise typer.Exit(1)
    try:
        rep = svc.check()
    except (ClientError, Exception) as exc:
        _handle_exc(c, exc); raise typer.Exit(1)
    if output_json:
        c.print(json.dumps({'state': str(rep.state), 'role_name': rep.role_name,
                            'role_exists': rep.role_exists, 'policy_matches': rep.policy_matches}, indent=2))
        if rep.state != Enum__Setup__State.OK: raise typer.Exit(1)
        return
    _print_iam_report(c, rep)
    if rep.state != Enum__Setup__State.OK: raise typer.Exit(1)


@admin_iam_app.command(name='status', help='Pretty-print live admin IAM role config.')
def admin_iam_status():
    c   = Console(highlight=False)
    svc = _admin_iam()
    _print_role_notice(c, svc)
    if not _preflight(c, _iam()): raise typer.Exit(1)
    info = svc.status()
    c.print()
    for k, v in info.items():
        c.print(f'  {k:<22}: {v}')
    c.print()


@admin_iam_app.command(name='create', help='Create admin IAM role + policy.')
def admin_iam_create():
    c   = Console(highlight=False)
    svc = _admin_iam()
    _print_role_notice(c, svc)
    if not _preflight(c, _iam()): raise typer.Exit(1)
    c.print('\n  [yellow]→[/]  Creating admin IAM role…')
    try:
        rep = svc.create()
    except (RuntimeError, ClientError, Exception) as exc:
        _handle_exc(c, exc); raise typer.Exit(1)
    _print_iam_report(c, rep)
    if rep.state == Enum__Setup__State.OK:
        c.print('  [green]✓[/]  Admin IAM role ready')
    c.print()


@admin_iam_app.command(name='update', help='Sync admin inline policy with Admin__Policy__Template.')
def admin_iam_update():
    c   = Console(highlight=False)
    svc = _admin_iam()
    _print_role_notice(c, svc)
    if not _preflight(c, _iam()): raise typer.Exit(1)
    c.print('\n  [yellow]→[/]  Updating admin IAM inline policy…')
    try:
        rep = svc.update()
    except (RuntimeError, ClientError, Exception) as exc:
        _handle_exc(c, exc); raise typer.Exit(1)
    _print_iam_report(c, rep)
    if rep.state == Enum__Setup__State.OK:
        c.print('  [green]✓[/]  Admin policy updated')
    c.print()


@admin_iam_app.command(name='delete', help='Delete admin IAM role.')
def admin_iam_delete(yes: bool = typer.Option(False, '--yes', '-y')):
    c   = Console(highlight=False)
    svc = _admin_iam()
    _print_role_notice(c, svc)
    if not _preflight(c, _iam()): raise typer.Exit(1)
    if not yes:
        if not typer.confirm('  Delete admin IAM role?'):
            raise typer.Exit(0)
    try:
        rep = svc.delete()
    except (RuntimeError, ClientError, Exception) as exc:
        _handle_exc(c, exc); raise typer.Exit(1)
    _print_iam_report(c, rep)


# ═══════════════════════════════════════════════════════════════════════════════
# sg vault-publish setup admin-lambda *
# ═══════════════════════════════════════════════════════════════════════════════

@admin_lambda_app.command(name='check', help='Check live admin Lambda config.')
def admin_lambda_check():
    c   = Console(highlight=False)
    svc = _admin_lambda()
    if not _preflight(c, _iam()): raise typer.Exit(1)
    try:
        rep = svc.check()
    except (ClientError, Exception) as exc:
        _handle_exc(c, exc); raise typer.Exit(1)
    _print_lambda_report(c, rep)
    if rep.state != Enum__Setup__State.OK: raise typer.Exit(1)


@admin_lambda_app.command(name='status', help='Pretty-print live admin Lambda config.')
def admin_lambda_status():
    c   = Console(highlight=False)
    svc = _admin_lambda()
    if not _preflight(c, _iam()): raise typer.Exit(1)
    info = svc.status()
    c.print()
    for k, v in info.items():
        c.print(f'  {k:<26}: {v}')
    c.print()


@admin_lambda_app.command(name='create', help='Deploy the admin Lambda.')
def admin_lambda_create(role_arn: str = typer.Option('', '--role-arn')):
    c   = Console(highlight=False)
    svc = _admin_lambda()
    if not _preflight(c, _iam()): raise typer.Exit(1)
    c.print('\n  [yellow]→[/]  Deploying admin Lambda…')
    try:
        rep = svc.create(role_arn=role_arn)
    except (RuntimeError, ClientError, Exception) as exc:
        _handle_exc(c, exc); raise typer.Exit(1)
    _print_lambda_report(c, rep)


@admin_lambda_app.command(name='update', help='Redeploy the admin Lambda.')
def admin_lambda_update():
    c   = Console(highlight=False)
    svc = _admin_lambda()
    if not _preflight(c, _iam()): raise typer.Exit(1)
    c.print('\n  [yellow]→[/]  Redeploying admin Lambda…')
    try:
        rep = svc.update()
    except (RuntimeError, ClientError, Exception) as exc:
        _handle_exc(c, exc); raise typer.Exit(1)
    _print_lambda_report(c, rep)


@admin_lambda_app.command(name='delete', help='Delete the admin Lambda.')
def admin_lambda_delete(yes: bool = typer.Option(False, '--yes', '-y')):
    c   = Console(highlight=False)
    svc = _admin_lambda()
    if not _preflight(c, _iam()): raise typer.Exit(1)
    if not yes:
        if not typer.confirm('  Delete admin Lambda?'):
            raise typer.Exit(0)
    try:
        ok = svc.delete()
    except (RuntimeError, ClientError, Exception) as exc:
        _handle_exc(c, exc); raise typer.Exit(1)
    c.print(f'  {"[green]✓[/]  admin Lambda deleted" if ok else "[red]✗[/]  delete failed"}')


# ═══════════════════════════════════════════════════════════════════════════════
# sg vault-publish setup admin-cf *  (ACM cert + CF distribution combined)
# ═══════════════════════════════════════════════════════════════════════════════

@admin_cf_app.command(name='check', help='Check admin CF distribution + verify cert is single-host (NOT wildcard).')
def admin_cf_check(zone: str = typer.Option(DEFAULT_ZONE, '--zone')):
    c   = Console(highlight=False)
    svc = _admin_cf()
    if not _preflight(c, _iam()): raise typer.Exit(1)
    try:
        rep = svc.check(zone)
    except (ClientError, Exception) as exc:
        _handle_exc(c, exc); raise typer.Exit(1)
    _print_cf_report(c, rep)
    if rep.state != Enum__Setup__State.OK: raise typer.Exit(1)


@admin_cf_app.command(name='status', help='Pretty-print admin CF distribution config.')
def admin_cf_status(zone: str = typer.Option(DEFAULT_ZONE, '--zone')):
    c   = Console(highlight=False)
    svc = _admin_cf()
    if not _preflight(c, _iam()): raise typer.Exit(1)
    info = svc.status(zone)
    c.print()
    for k, v in info.items():
        c.print(f'  {k:<18}: {v}')
    c.print()


@admin_cf_app.command(name='create', help='Provision admin CF + single-host ACM cert (waits for DNS validation, up to 30 min).')
def admin_cf_create(
    zone               : str = typer.Option(DEFAULT_ZONE, '--zone'),
    cert_wait_timeout  : int = typer.Option(1800, '--cert-wait-timeout',
                                              help='Max seconds to wait for ACM DNS validation (default 30 min).'),
):
    c   = Console(highlight=False)
    svc = _admin_cf()
    if not _preflight(c, _iam()): raise typer.Exit(1)

    def _prog(stage, detail):
        c.print(f'  [dim]   {stage}  {detail}[/]')

    c.print(f'\n  [yellow]→[/]  Provisioning admin CF distribution + ACM cert for vp-admin.{zone}…')
    try:
        rep = svc.create(zone, cert_wait_timeout_sec=cert_wait_timeout, progress=_prog)
    except (RuntimeError, ClientError, Exception) as exc:
        _handle_exc(c, exc); raise typer.Exit(1)
    _print_cf_report(c, rep)


@admin_cf_app.command(name='update', help='Re-ensure admin CF distribution + cert.')
def admin_cf_update(zone: str = typer.Option(DEFAULT_ZONE, '--zone')):
    c   = Console(highlight=False)
    svc = _admin_cf()
    if not _preflight(c, _iam()): raise typer.Exit(1)

    def _prog(stage, detail):
        c.print(f'  [dim]   {stage}  {detail}[/]')

    c.print(f'\n  [yellow]→[/]  Updating admin CF distribution…')
    try:
        rep = svc.update(zone, progress=_prog)
    except (RuntimeError, ClientError, Exception) as exc:
        _handle_exc(c, exc); raise typer.Exit(1)
    _print_cf_report(c, rep)


@admin_cf_app.command(name='delete', help='Delete admin CF distribution.')
def admin_cf_delete(
    zone : str  = typer.Option(DEFAULT_ZONE, '--zone'),
    yes  : bool = typer.Option(False, '--yes', '-y'),
):
    c   = Console(highlight=False)
    svc = _admin_cf()
    if not _preflight(c, _iam()): raise typer.Exit(1)
    if not yes:
        if not typer.confirm(f'  Delete admin CF distribution for vp-admin.{zone}?'):
            raise typer.Exit(0)
    try:
        ok = svc.delete(zone)
    except (RuntimeError, ClientError, Exception) as exc:
        _handle_exc(c, exc); raise typer.Exit(1)
    c.print(f'  {"[green]✓[/]  admin CF deleted" if ok else "[red]✗[/]  delete failed (already gone?)"}')


# ═══════════════════════════════════════════════════════════════════════════════
# sg vault-publish setup admin-dns *
# ═══════════════════════════════════════════════════════════════════════════════

@admin_dns_app.command(name='check', help='Check Route 53 record for vp-admin.<zone>.')
def admin_dns_check(zone: str = typer.Option(DEFAULT_ZONE, '--zone')):
    c   = Console(highlight=False)
    svc = _admin_dns()
    if not _preflight(c, _iam()): raise typer.Exit(1)
    try:
        rep = svc.check(zone)
    except (ClientError, Exception) as exc:
        _handle_exc(c, exc); raise typer.Exit(1)
    _print_dns_report(c, rep)
    if rep.state != Enum__Setup__State.OK: raise typer.Exit(1)


@admin_dns_app.command(name='status', help='Pretty-print admin DNS record.')
def admin_dns_status(zone: str = typer.Option(DEFAULT_ZONE, '--zone')):
    c   = Console(highlight=False)
    svc = _admin_dns()
    if not _preflight(c, _iam()): raise typer.Exit(1)
    info = svc.status(zone)
    c.print()
    for k, v in info.items():
        c.print(f'  {k:<12}: {v}')
    c.print()


@admin_dns_app.command(name='create', help='Create CNAME vp-admin.<zone> → admin CF distribution.')
def admin_dns_create(zone: str = typer.Option(DEFAULT_ZONE, '--zone')):
    c   = Console(highlight=False)
    svc = _admin_dns()
    if not _preflight(c, _iam()): raise typer.Exit(1)
    c.print(f'\n  [yellow]→[/]  Upserting Route 53 record for vp-admin.{zone}…')
    try:
        rep = svc.create(zone)
    except (RuntimeError, ClientError, Exception) as exc:
        _handle_exc(c, exc); raise typer.Exit(1)
    _print_dns_report(c, rep)


@admin_dns_app.command(name='delete', help='Delete admin DNS record.')
def admin_dns_delete(
    zone : str  = typer.Option(DEFAULT_ZONE, '--zone'),
    yes  : bool = typer.Option(False, '--yes', '-y'),
):
    c   = Console(highlight=False)
    svc = _admin_dns()
    if not _preflight(c, _iam()): raise typer.Exit(1)
    if not yes:
        if not typer.confirm(f'  Delete admin DNS record vp-admin.{zone}?'):
            raise typer.Exit(0)
    try:
        ok = svc.delete(zone)
    except (RuntimeError, ClientError, Exception) as exc:
        _handle_exc(c, exc); raise typer.Exit(1)
    c.print(f'  {"[green]✓[/]  admin DNS record deleted" if ok else "[red]✗[/]  delete failed"}')
