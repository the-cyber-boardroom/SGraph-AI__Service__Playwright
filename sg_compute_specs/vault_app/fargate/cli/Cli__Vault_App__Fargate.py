# ═══════════════════════════════════════════════════════════════════════════════
# sg_compute_specs vault_app/fargate/cli — Cli__Vault_App__Fargate
# Parent Typer app for `sg vault-app fargate *` commands.
# Mounts sub-apps: setup (Slice 4). start/stop/health/logs (Slice 6).
# ═══════════════════════════════════════════════════════════════════════════════

import typer

from sg_compute_specs.vault_app.fargate.cli.Cli__Vault_App__Fargate__Setup import app as setup_app

app = typer.Typer(name='fargate', help='Vault-App on Fargate.', no_args_is_help=True)

app.add_typer(setup_app, name='setup')
