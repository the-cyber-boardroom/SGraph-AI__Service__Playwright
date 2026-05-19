# ═══════════════════════════════════════════════════════════════════════════════
# sg_compute_specs vault_app/fargate/cli — Cli__Vault_App__Fargate
# Parent Typer app for `sg vault-app fargate *` commands.
# Mounts sub-apps: setup (Slice 4). Task-level commands (Slice 6).
# ═══════════════════════════════════════════════════════════════════════════════

import typer

from sg_compute_specs.vault_app.fargate.cli.Cli__Vault_App__Fargate__Setup import app as setup_app
from sg_compute_specs.vault_app.fargate.cli.Cli__Vault_App__Fargate__Start import (
    fargate_start,
    fargate_stop,
    fargate_restart,
    fargate_health,
    fargate_url,
    fargate_open,
    fargate_logs,
    fargate_list,
    fargate_info,
    fargate_timings,
)

app = typer.Typer(name='fargate', help='Vault-App on Fargate.', no_args_is_help=True)

app.add_typer(setup_app, name='setup')

# ── task-level commands mounted directly on the fargate app ──────────────────

app.command('start'  )(fargate_start   )
app.command('stop'   )(fargate_stop    )
app.command('restart')(fargate_restart )
app.command('health' )(fargate_health  )
app.command('url'    )(fargate_url     )
app.command('open'   )(fargate_open    )
app.command('logs'   )(fargate_logs    )
app.command('list'   )(fargate_list    )
app.command('info'   )(fargate_info    )
app.command('timings')(fargate_timings )
