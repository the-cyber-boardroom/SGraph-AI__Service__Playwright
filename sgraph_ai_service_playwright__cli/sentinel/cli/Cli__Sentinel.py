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
