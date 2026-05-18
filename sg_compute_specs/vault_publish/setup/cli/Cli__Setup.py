# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — vault-publish setup: Cli__Setup
# Typer app for `sg vault-publish setup` sub-commands.
#
#   sg vault-publish setup iam check    — report vs Waker__Policy__Template
#   sg vault-publish setup iam status   — pretty-print live role config
#   sg vault-publish setup iam create   — create role + policy (mutation-gated)
#   sg vault-publish setup iam update   — sync policy with template (mutation-gated)
#   sg vault-publish setup iam delete   — delete role (delete-gated)
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

from sg_compute_specs.vault_publish.setup.schemas.Enum__Setup__State import Enum__Setup__State
from sg_compute_specs.vault_publish.setup.service.Setup__IAM         import Setup__IAM

app        = typer.Typer(name='setup',  help='Setup and drift-check for vault-publish AWS resources.', no_args_is_help=True)
iam_app    = typer.Typer(name='iam',    help='IAM execution role management.',                         no_args_is_help=True)
lambda_app = typer.Typer(name='lambda', help='Lambda waker function management (Phase B2).',           no_args_is_help=True)
cf_app     = typer.Typer(name='cf',     help='CloudFront distribution management (Phase B3).',         no_args_is_help=True)
acm_app    = typer.Typer(name='acm',    help='ACM wildcard certificate management (Phase B3).',        no_args_is_help=True)
dns_app    = typer.Typer(name='dns',    help='Route 53 DNS record management (Phase B3).',             no_args_is_help=True)

app.add_typer(iam_app,    name='iam')
app.add_typer(lambda_app, name='lambda')
app.add_typer(cf_app,     name='cf')
app.add_typer(acm_app,    name='acm')
app.add_typer(dns_app,    name='dns')


def _iam() -> Setup__IAM:
    return Setup__IAM()


# ── shared pre-flight helpers ─────────────────────────────────────────────────

def _print_role_notice(c: Console, svc: Setup__IAM) -> None:
    notice = svc.assumed_role_notice()
    if notice:
        c.print(f'  [dim]ℹ  {notice}[/]')


def _preflight(c: Console, svc: Setup__IAM) -> bool:
    """Validate credentials via STS GetCallerIdentity. Returns True if OK."""
    info = svc.credentials_ok()
    if info['ok']:
        c.print(f"  [dim]✓  identity: {info['arn']}[/]")
        return True
    c.print(f'\n  [red]✗  credential check failed[/]')
    c.print(f"  [red]   {info['error']}[/]")
    err = info['error']
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


# ── sg vault-publish setup iam check ─────────────────────────────────────────

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


# ── sg vault-publish setup iam status ────────────────────────────────────────

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


# ── sg vault-publish setup iam create ────────────────────────────────────────

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
    except RuntimeError as exc:
        c.print(f'  [red]✗  {exc}[/]')
        raise typer.Exit(1)
    except ClientError as exc:
        _print_aws_error(c, exc)
        raise typer.Exit(1)
    except Exception as exc:
        c.print(f'  [red]✗  {exc}[/]')
        raise typer.Exit(1)
    _print_iam_report(c, rep)
    if rep.state == Enum__Setup__State.OK:
        c.print('  [green]✓[/]  IAM role ready')
    c.print()


# ── sg vault-publish setup iam update ────────────────────────────────────────

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
    except RuntimeError as exc:
        c.print(f'  [red]✗  {exc}[/]')
        raise typer.Exit(1)
    except ClientError as exc:
        _print_aws_error(c, exc)
        raise typer.Exit(1)
    except Exception as exc:
        c.print(f'  [red]✗  {exc}[/]')
        raise typer.Exit(1)
    _print_iam_report(c, rep)
    if rep.state == Enum__Setup__State.OK:
        c.print('  [green]✓[/]  Policy updated and matches template')
    c.print()


# ── sg vault-publish setup iam delete ────────────────────────────────────────

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
    except RuntimeError as exc:
        c.print(f'  [red]✗  {exc}[/]')
        raise typer.Exit(1)
    except ClientError as exc:
        _print_aws_error(c, exc)
        raise typer.Exit(1)
    except Exception as exc:
        c.print(f'  [red]✗  {exc}[/]')
        raise typer.Exit(1)
    c.print('  [green]✓[/]  IAM role deleted')
    c.print()


# ── lambda stubs (Phase B2) ───────────────────────────────────────────────────

_NOT_YET_B2 = '\n  [dim]⌛  Phase B2 — not yet implemented[/]\n'
_NOT_YET_B3 = '\n  [dim]⌛  Phase B3 — not yet implemented[/]\n'


@lambda_app.command(name='check', help='Check Lambda waker function vs expected state.')
def lambda_check():
    Console(highlight=False).print(_NOT_YET_B2)


@lambda_app.command(name='status', help='Pretty-print live Lambda function configuration.')
def lambda_status():
    Console(highlight=False).print(_NOT_YET_B2)


@lambda_app.command(name='create', help='Deploy Lambda waker function (Phase B2).')
def lambda_create():
    Console(highlight=False).print(_NOT_YET_B2)


@lambda_app.command(name='update', help='Redeploy / sync Lambda waker function (Phase B2).')
def lambda_update():
    Console(highlight=False).print(_NOT_YET_B2)


# ── CloudFront stubs (Phase B3) ───────────────────────────────────────────────

@cf_app.command(name='check', help='Check CloudFront wildcard distribution vs expected state.')
def cf_check():
    Console(highlight=False).print(_NOT_YET_B3)


@cf_app.command(name='status', help='Pretty-print live CloudFront distribution.')
def cf_status():
    Console(highlight=False).print(_NOT_YET_B3)


@cf_app.command(name='create', help='Create CloudFront wildcard distribution (Phase B3).')
def cf_create():
    Console(highlight=False).print(_NOT_YET_B3)


@cf_app.command(name='update', help='Sync CloudFront distribution with expected config (Phase B3).')
def cf_update():
    Console(highlight=False).print(_NOT_YET_B3)


# ── ACM stubs (Phase B3) ─────────────────────────────────────────────────────

@acm_app.command(name='check', help='Check ACM wildcard certificate vs expected state.')
def acm_check():
    Console(highlight=False).print(_NOT_YET_B3)


@acm_app.command(name='status', help='Pretty-print live ACM certificate.')
def acm_status():
    Console(highlight=False).print(_NOT_YET_B3)


@acm_app.command(name='create', help='Request ACM wildcard certificate (Phase B3).')
def acm_create():
    Console(highlight=False).print(_NOT_YET_B3)


# ── DNS stubs (Phase B3) ─────────────────────────────────────────────────────

@dns_app.command(name='check', help='Check Route 53 wildcard DNS record vs expected state.')
def dns_check():
    Console(highlight=False).print(_NOT_YET_B3)


@dns_app.command(name='status', help='Pretty-print live Route 53 DNS record.')
def dns_status():
    Console(highlight=False).print(_NOT_YET_B3)


@dns_app.command(name='create', help='Create Route 53 wildcard DNS record (Phase B3).')
def dns_create():
    Console(highlight=False).print(_NOT_YET_B3)


# ── internal ──────────────────────────────────────────────────────────────────

_STATE_ICON = {
    Enum__Setup__State.OK      : '[green]✓ OK[/]',
    Enum__Setup__State.MISSING : '[red]✗ MISSING[/]',
    Enum__Setup__State.DRIFT   : '[yellow]⚠ DRIFT[/]',
    Enum__Setup__State.ERROR   : '[red]✗ ERROR[/]',
    Enum__Setup__State.UNKNOWN : '[dim]? UNKNOWN[/]',
}


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
