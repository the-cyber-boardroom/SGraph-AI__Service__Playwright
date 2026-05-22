# SG/Edge local edge — TUI API (for humans)

Drive the local SG/Edge edge as a structured API — by hand, from pytest, the
explorer, or the chat. Every action is the same backend the `sg edge local *`
commands and the Control Center use.

```bash
sg edge tui api list                                  # the actions this edge exposes
sg edge tui api describe sg-edge.local --json         # the manifest (tiers/scopes/schemas)
sg edge tui api status   sg-edge.local                # orientation: deployed?, available actions
sg edge tui api invoke   sg-edge.local setup
sg edge tui api invoke   sg-edge.local register --params '{"slug":"alice"}'
sg edge tui api invoke   sg-edge.local request  --params '{"slug":"alice"}'
sg edge tui api invoke   sg-edge.local teardown --dry-run   # preview without deleting
sg edge tui api explore                               # the Swagger-style TUI explorer
```

Mutations prompt for confirmation (or set `SG_TUI_API__ALLOW_MUTATIONS=1` for
scripted use). On the AWS edge the mutating actions are unavailable (read-only;
live-EC2 pending).
