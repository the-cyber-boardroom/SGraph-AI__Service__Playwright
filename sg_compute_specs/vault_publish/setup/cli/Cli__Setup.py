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
from sg_compute_specs.vault_publish.schemas.Schema__Vault_Publish__Bootstrap__Request import DEFAULT_CERT_ARN, DEFAULT_ZONE

app             = typer.Typer(name='setup',       help='Setup and drift-check for vault-publish AWS resources.', no_args_is_help=True)
ec2_app         = typer.Typer(name='ec2',         help='EC2 prerequisites (IAM instance profile + base AMI).',   no_args_is_help=True)
iam_app         = typer.Typer(name='iam',         help='IAM execution role management.',                         no_args_is_help=True)
lambda_app      = typer.Typer(name='lambda',      help='Lambda waker function management.',                      no_args_is_help=True)
cf_app          = typer.Typer(name='cf',          help='CloudFront wildcard distribution management.',           no_args_is_help=True)
cf_function_app = typer.Typer(name='cf-function', help='CloudFront Function — viewer Host → X-Forwarded-Host.',  no_args_is_help=True)
acm_app         = typer.Typer(name='acm',         help='ACM wildcard certificate management.',                   no_args_is_help=True)
dns_app         = typer.Typer(name='dns',         help='Route 53 wildcard DNS record management.',               no_args_is_help=True)

app.add_typer(ec2_app,         name='ec2')
app.add_typer(iam_app,         name='iam')
app.add_typer(lambda_app,      name='lambda')
app.add_typer(cf_app,          name='cf')
app.add_typer(cf_function_app, name='cf-function')
app.add_typer(acm_app,         name='acm')
app.add_typer(dns_app,         name='dns')


# ── service constructors ─────────────────────────────────────────────────────

def _iam()         -> Setup__IAM:          return Setup__IAM()
def _lambda()      -> Setup__Lambda:       return Setup__Lambda()
def _cf()          -> Setup__CF:           return Setup__CF()
def _cf_function() -> Setup__CF__Function: return Setup__CF__Function()
def _acm()         -> Setup__ACM:          return Setup__ACM()
def _dns()         -> Setup__DNS:          return Setup__DNS()
def _ec2()         -> Setup__EC2:          return Setup__EC2()


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
    c.print('\n  [yellow]→[/]  Deploying Lambda waker…')
    try:
        rep = _lambda().create(role_arn=role_arn)
    except (RuntimeError, ClientError, Exception) as exc:
        _handle_exc(c, exc)
        raise typer.Exit(1)
    _print_lambda_report(c, rep)
    if rep.state == Enum__Setup__State.OK:
        c.print('  [green]✓[/]  Lambda waker ready')
    c.print()


@lambda_app.command(name='update', help='Redeploy Lambda waker function. Requires SG_AWS__VAULT_PUBLISH__SETUP__ALLOW_MUTATIONS=1.')
def lambda_update():
    c   = Console(highlight=False)
    svc = _iam()
    _print_role_notice(c, svc)
    if not _preflight(c, svc):
        raise typer.Exit(1)
    c.print('\n  [yellow]→[/]  Redeploying Lambda waker…')
    try:
        rep = _lambda().update()
    except (RuntimeError, ClientError, Exception) as exc:
        _handle_exc(c, exc)
        raise typer.Exit(1)
    _print_lambda_report(c, rep)
    if rep.state == Enum__Setup__State.OK:
        c.print('  [green]✓[/]  Lambda waker updated')
    c.print()


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
        c.print(f'  ARN         : {rep.function_arn}')
    if rep.function_url:
        c.print(f'  Function URL: {rep.function_url}')
    for issue in rep.issues:
        sev_colour = {'error': 'red', 'warn': 'yellow', 'info': 'dim'}.get(issue.severity, 'white')
        c.print(f'  [{sev_colour}]{issue.severity.upper()}: {issue.message}[/]')


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
