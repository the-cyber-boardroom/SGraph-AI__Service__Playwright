# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Cli__Sentinel
# `sg sentinel` root group — SG/Sentinel edge guard (logging + blocking).
# Mounts the per-area subgroups; no inline command logic lives here.
#
# Command tree (filled in phase by phase):
#   sg sentinel rules   list | show <id> | test          # tiny-core rule visibility   (Phase 1)
#   sg sentinel local   up | hit | down                  # full stack offline          (Phase 2/3)
#   sg sentinel logs    tail | ls | trace <request-id>   # use case 1 (read the sink)  (Phase 2)
#   sg sentinel blocks  list | why <request-id|ip>       # use case 2                  (Phase 2)
#   sg sentinel deploy  create | destroy | teardown      # live path (mutation-gated)  (Phase 4)
#   sg sentinel status                                   # what's deployed + parity    (Phase 4)
# ═══════════════════════════════════════════════════════════════════════════════

import typer


app = typer.Typer(name            = 'sentinel',
                  help            = 'SG/Sentinel — edge guard (logging + blocking).',
                  no_args_is_help = True)


@app.callback()
def _root():                                                                        # anchors the group so `--help` builds even before subgroups land
    pass


# Subgroups are mounted here as each phase lands (rules, local, logs, blocks, deploy, status).

# ── rules ──────────────────────────────────────────────────────────────────────
from sgraph_ai_service_playwright__cli.sentinel.cli.Cli__Sentinel__Rules import app as _rules_app
app.add_typer(_rules_app, name='rules', help='Tiny-core rule visibility (list / show / test).')

# ── local ──────────────────────────────────────────────────────────────────────
from sgraph_ai_service_playwright__cli.sentinel.cli.Cli__Sentinel__Local import app as _local_app
app.add_typer(_local_app, name='local', help='Offline full stack (local-direct): up / hit / down.')

# ── logs ───────────────────────────────────────────────────────────────────────
from sgraph_ai_service_playwright__cli.sentinel.cli.Cli__Sentinel__Logs import app as _logs_app
app.add_typer(_logs_app, name='logs', help='Read the log sink (ls / tail / trace).')

# ── blocks ─────────────────────────────────────────────────────────────────────
from sgraph_ai_service_playwright__cli.sentinel.cli.Cli__Sentinel__Blocks import app as _blocks_app
app.add_typer(_blocks_app, name='blocks', help='Inspect blocked requests (list / why).')
