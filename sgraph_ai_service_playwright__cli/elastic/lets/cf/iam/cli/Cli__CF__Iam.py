# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Cli__CF__Iam
# `sg el lets cf iam …` — provision and inspect the sg-lets-cf least-privilege role
# that the cf command family transparently assumes. Thin Typer surface over the generic
# AWS__Role__Provisioner; the policy comes entirely from the registered profile.
#
#   sg el lets cf iam show            # desired policy + trust + whether the role exists
#   sg el lets cf iam plan            # diff: live role vs the profile (actions to add/remove)
#   sg el lets cf iam create          # create-or-update the role (gated)
#   sg el lets cf iam update          # alias of create — idempotent re-apply (gated)
#   sg el lets cf iam test            # assume the role and print the caller identity
#   sg el lets cf iam delete [--yes]  # delete the role (gated)
#
# Read-only (show/plan/test) always allowed. Mutations require
# SG_AWS__IAM__ALLOW_MUTATIONS=1 and a confirmation.
# ═══════════════════════════════════════════════════════════════════════════════

import json
import os

import typer

from sgraph_ai_service_playwright__cli.aws._shared.Aws__Confirm                    import confirm_or_abort
from sgraph_ai_service_playwright__cli.aws._shared.auth                            import AWS__Role__Profiles as profiles
from sgraph_ai_service_playwright__cli.aws._shared.auth.AWS__Auth__Guard           import aws_auth_guard
from sgraph_ai_service_playwright__cli.aws._shared.auth.AWS__Role__Provisioner     import AWS__Role__Provisioner

FAMILY  = 'el-lets-cf'
iam_app = typer.Typer(name='iam', help='Provision/inspect the sg-lets-cf least-privilege role.', no_args_is_help=True)


@iam_app.callback()
def _setup_ctx(ctx : typer.Context):
    if ctx.obj is None:
        ctx.obj = {}
    ctx.obj.setdefault('provisioner', AWS__Role__Provisioner())


def _profile():
    profile = profiles.get_profile(FAMILY)
    if profile is None:                                                              # registry mis-wiring — fail loud
        typer.echo(f'No role profile registered for family: {FAMILY}')
        raise typer.Exit(1)
    return profile


def _mutation_guard():
    if os.environ.get('SG_AWS__IAM__ALLOW_MUTATIONS') != '1':
        typer.echo('Set SG_AWS__IAM__ALLOW_MUTATIONS=1 to allow IAM mutations.')
        raise typer.Exit(1)


@iam_app.command('show', help='Show the desired policy + trust and whether the role exists.')
@aws_auth_guard('', admin_role='iam-admin')                                                                  # default to the iam-admin base credential; catch auth errors (menu). No transparent assume — these commands MANAGE the role as admin.
def show(ctx : typer.Context, as_json : bool = typer.Option(False, '--json', help='Output as JSON.')):
    profile = _profile()
    plan    = ctx.obj['provisioner'].plan(profile)
    if as_json:
        typer.echo(json.dumps(dict(role_name=plan.role_name, role_arn=plan.role_arn,
                                   exists=plan.exists, policy=json.loads(plan.policy_json)), indent=2))
        return
    typer.echo(f'\nrole   : {plan.role_name}')
    typer.echo(f'arn    : {plan.role_arn or "(unresolved — no credentials)"}')
    typer.echo(f'exists : {plan.exists}')
    typer.echo(f'\ntrust policy:\n{plan.trust_json or "(unresolved)"}')
    typer.echo(f'\ninline policy:\n{plan.policy_json}\n')


@iam_app.command('plan', help='Diff the live role against the profile (actions to add/remove).')
@aws_auth_guard('', admin_role='iam-admin')
def plan(ctx : typer.Context, as_json : bool = typer.Option(False, '--json', help='Output as JSON.')):
    profile = _profile()
    p       = ctx.obj['provisioner'].plan(profile)
    if as_json:
        typer.echo(json.dumps(dict(role_name=p.role_name, exists=p.exists, in_sync=p.in_sync,
                                   actions_to_add=p.actions_to_add, actions_to_remove=p.actions_to_remove), indent=2))
        return
    typer.echo(f'\nrole    : {p.role_name}   (exists={p.exists}, in_sync={p.in_sync})')
    if p.in_sync:
        typer.echo('  ✓ live role matches the profile — nothing to do\n')
        return
    if not p.exists:
        typer.echo('  • role does not exist — `sg el lets cf iam create` will create it')
    for a in p.actions_to_add:
        typer.echo(f'  + {a}')
    for a in p.actions_to_remove:
        typer.echo(f'  - {a}')
    typer.echo('')


@iam_app.command('create', help='Create-or-update the role to match the profile (gated).')
@aws_auth_guard('', admin_role='iam-admin')
def create(ctx     : typer.Context,
           yes     : bool = typer.Option(False, '--yes', '-y', help='Skip confirmation.'),
           dry_run : bool = typer.Option(False, '--dry-run', help='Print the plan; make no changes.')):
    profile = _profile()
    if dry_run:
        return plan(ctx)
    _mutation_guard()
    if not confirm_or_abort(f'Create/update role "{profile.role_name}" for {FAMILY}?', yes=yes, dry_run=dry_run):
        raise typer.Exit(0)
    resp = ctx.obj['provisioner'].apply(profile)
    verb = 'Created' if resp.created else 'Updated'
    typer.echo(f'{verb} {resp.role_name}')
    typer.echo(f'  arn: {resp.role_arn}')


@iam_app.command('update', help='Idempotent re-apply of the profile to the role (gated). Alias of create.')
def update(ctx     : typer.Context,
           yes     : bool = typer.Option(False, '--yes', '-y', help='Skip confirmation.'),
           dry_run : bool = typer.Option(False, '--dry-run', help='Print the plan; make no changes.')):
    return create(ctx, yes=yes, dry_run=dry_run)


@iam_app.command('test', help='Assume the role and print the caller identity (proves it is assumable).')
@aws_auth_guard('', admin_role='iam-admin')
def test(ctx : typer.Context):
    from sgraph_ai_service_playwright__cli.credentials.service.Sg__Aws__Session import Sg__Aws__Session
    profile    = _profile()
    prov       = ctx.obj['provisioner']
    account_id = prov.resolve_account_id()
    if not account_id:
        typer.echo('Could not resolve account id (no usable base credentials).')
        raise typer.Exit(1)
    arn     = profiles.role_arn(profile, account_id)
    session = Sg__Aws__Session.from_context().assume_arn(arn)
    if session is None:
        typer.echo(f'Assume FAILED for {arn}')
        typer.echo('  The role may not exist yet (`sg el lets cf iam create`) or your base identity may lack sts:AssumeRole.')
        raise typer.Exit(1)
    ident = session.client('sts').get_caller_identity()
    typer.echo(f'Assume OK → {ident.get("Arn", "")}')


@iam_app.command('delete', help='Delete the role (gated).')
@aws_auth_guard('', admin_role='iam-admin')
def delete(ctx     : typer.Context,
           yes     : bool = typer.Option(False, '--yes', '-y', help='Skip confirmation.'),
           dry_run : bool = typer.Option(False, '--dry-run', help='Print what would happen; make no changes.')):
    profile = _profile()
    _mutation_guard()
    if not confirm_or_abort(f'Delete role "{profile.role_name}"?', yes=yes, dry_run=dry_run):
        raise typer.Exit(0)
    ok = ctx.obj['provisioner'].delete(profile)
    typer.echo(f'{"Deleted" if ok else "Delete failed for"} {profile.role_name}')
