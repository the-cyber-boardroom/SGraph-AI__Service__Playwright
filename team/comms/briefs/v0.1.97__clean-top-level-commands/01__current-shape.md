# Current shape — what `sp --help` lists today (post-v0.1.96)

## Top-level commands (21)

All of these operate on the **Playwright EC2** specifically — there is no general "sp create a stack" — `sp create` provisions a `playwright-ec2`-purposed instance.

| Command | What it does (today) |
|---|---|
| `sp create` | Provision Playwright EC2 |
| `sp list` | List `sg:purpose=playwright-ec2` instances |
| `sp info <name>` | Tag metadata for one Playwright instance |
| `sp delete <name \| --all>` | Terminate one or all Playwright instances |
| `sp connect <name>` | SSM shell on the host |
| `sp shell <name>` | SSM shell inside the playwright container |
| `sp env <name>` | Print export statements for env vars |
| `sp run <vault-key> <script>` | Vault-driven scenario runner |
| `sp exec <name> <cmd>` | Run command on the host or in a container via SSM |
| `sp exec-c <name> <cmd>` | Shorthand for `exec --container sg-playwright-playwright-1` |
| `sp logs <name>` | docker compose logs via SSM |
| `sp diagnose <name>` | Deep system check (ports, disk, OOM, …) |
| `sp forward <name> <port>` | Local SSM port-forward |
| `sp wait <name>` | Poll health endpoint |
| `sp clean <name>` | Pre-AMI-bake cleanup |
| `sp create-from-ami <ami>` | Launch instance from a baked Playwright AMI |
| `sp open <name>` | Open launcher UI in browser |
| `sp screenshot <url>` | Quick navigate + screenshot smoke |
| `sp smoke <urls>` | URL-list smoke test |
| `sp health <name>` | Health checks |
| `sp ensure-passrole` | Attach IAM passrole policy |

## Subgroups (8 visible + 1 hidden)

| Subgroup | Scope | Source |
|---|---|---|
| `sp vault` | Operates on the Playwright EC2's vault checkout | `vault_app` in `scripts/provision_ec2.py` (Phase D D.3) |
| `sp ami` | Operates on `sg:purpose=playwright-ec2` AMIs | `ami_app` in `scripts/provision_ec2.py` (Phase D D.4) |
| `sp elastic` (alias `sp el`) | Elasticsearch + Kibana sister section | `scripts/elastic.py` |
| `sp opensearch` (alias `sp os`) | OpenSearch + Dashboards | `scripts/opensearch.py` |
| `sp prometheus` (alias `sp prom`) | Prometheus + cAdvisor + node-exporter | `scripts/prometheus.py` |
| `sp vnc` | chromium + nginx + mitmproxy browser-viewer | `scripts/vnc.py` |
| `sp linux` (alias `sp lx`) | Bare AL2023 EC2 stacks | `scripts/linux.py` |
| `sp docker` (alias `sp dk`) | AL2023 + Docker CE EC2 stacks | `scripts/docker.py` |
| `sp ob` / `sp observability` (hidden) | AMP + AMG + OpenSearch managed services | `scripts/observability.py` |

## Why this shape feels off

Reading the `--help` output linearly, you can't tell:
- which top-level commands are global vs. Playwright-specific
- which subgroups are stack-types (sister sections that all have the same `create / list / info / delete / health` shape) vs. cross-cutting tools (`vault`, `ami`)
- whether `sp ami create` operates on a Playwright AMI specifically, or on something cross-section

For an operator running multiple stack types in parallel — exactly the use case v0.1.96 enables — this asymmetry is friction. It pays to flatten.
