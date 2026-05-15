# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute — Cli__SG
# Top-level typer app for the `sg` CLI. Aggregates the per-spec sub-typers
# without any inline command logic — everything lives in its spec.
#
# Wiring rule: each spec exports `cli.Cli__{Spec}:app` (or `scripts/{spec}.py:app`
# for the older Phase-2 scripts that haven't been migrated to sg_compute_specs
# yet); this file does nothing but `app.add_typer(...)` them.
#
# Console scripts (pyproject.toml):
#   sg          = "sg_compute.cli.Cli__SG:app"   # primary alias
#   sgc         = "sg_compute.cli.Cli__SG:app"   # short alias
#   sg-compute  = "sg_compute.cli.Cli__SG:app"
#   sp          = "sg_compute.cli.Cli__SG:app"   # legacy alias
# ═══════════════════════════════════════════════════════════════════════════════

import typer


app = typer.Typer(name            = 'sg'                                                                ,
                  help            = 'SG/Compute CLI — manage ephemeral EC2 stacks across all specs.'    ,
                  no_args_is_help = True                                                                ,
                  add_completion  = False                                                               )

# ── playwright (sg_compute_specs/playwright) ─────────────────────────────────
from sg_compute_specs.playwright.cli.Cli__Playwright import app as _playwright_app
app.add_typer(_playwright_app, name='playwright')
app.add_typer(_playwright_app, name='pw', hidden=True)                                                  # short alias

# ── observability ────────────────────────────────────────────────────────────
from scripts.observability import app as _observability_app
app.add_typer(_observability_app, name='observability', hidden=True)
app.add_typer(_observability_app, name='ob',            hidden=True)

# ── elastic ──────────────────────────────────────────────────────────────────
from scripts.elastic import app as _elastic_app
app.add_typer(_elastic_app, name='elastic')                                                             # ephemeral Elastic+Kibana EC2 stacks
app.add_typer(_elastic_app, name='el',     hidden=True)

# ── opensearch ───────────────────────────────────────────────────────────────
from scripts.opensearch import app as _opensearch_app
app.add_typer(_opensearch_app, name='opensearch')                                                       # ephemeral OpenSearch+Dashboards EC2 stacks
app.add_typer(_opensearch_app, name='os',         hidden=True)

# ── prometheus ───────────────────────────────────────────────────────────────
from scripts.prometheus import app as _prometheus_app
app.add_typer(_prometheus_app, name='prometheus')                                                       # ephemeral Prometheus+cAdvisor+node-exporter EC2 stacks
app.add_typer(_prometheus_app, name='prom',       hidden=True)

# ── vnc ──────────────────────────────────────────────────────────────────────
from scripts.vnc import app as _vnc_app
app.add_typer(_vnc_app, name='vnc')                                                                     # ephemeral chromium+nginx+mitmproxy EC2 stacks (browser-viewer)

# ── neko ─────────────────────────────────────────────────────────────────────
from sgraph_ai_service_playwright__cli.neko.cli import app as _neko_app
app.add_typer(_neko_app, name='neko')                                                                   # ephemeral Neko WebRTC browser EC2 stacks (experiment)
app.add_typer(_neko_app, name='nk', hidden=True)

# ── firefox ──────────────────────────────────────────────────────────────────
from sgraph_ai_service_playwright__cli.firefox.cli import app as _firefox_app
app.add_typer(_firefox_app, name='firefox')                                                             # ephemeral Firefox noVNC browser EC2 stacks (experiment)
app.add_typer(_firefox_app, name='ff', hidden=True)

# ── podman ───────────────────────────────────────────────────────────────────
from scripts.podman import app as _podman_app
app.add_typer(_podman_app, name='podman')                                                               # ephemeral Podman EC2 stacks
app.add_typer(_podman_app, name='lx',  hidden=True)

# ── docker ───────────────────────────────────────────────────────────────────
from scripts.docker_stack import app as _docker_app
app.add_typer(_docker_app, name='docker')                                                               # ephemeral Docker-on-AL2023 EC2 stacks
app.add_typer(_docker_app, name='dk',   hidden=True)

# ── open-design ──────────────────────────────────────────────────────────────
from sg_compute_specs.open_design.cli import app as _open_design_app
app.add_typer(_open_design_app, name='open-design')                                                     # ephemeral Open Design EC2 stacks
app.add_typer(_open_design_app, name='od',   hidden=True)

# ── ollama ───────────────────────────────────────────────────────────────────
from sg_compute_specs.ollama.cli.Cli__Ollama import app as _ollama_app
app.add_typer(_ollama_app, name='ollama')                                                               # ephemeral Ollama GPU EC2 stacks
app.add_typer(_ollama_app, name='ol', hidden=True)

# ── local-claude ─────────────────────────────────────────────────────────────
from sg_compute_specs.local_claude.cli.Cli__Local_Claude import app as _local_claude_app
app.add_typer(_local_claude_app, name='local-claude')                                                   # local vLLM + Claude Code on EC2 GPU
app.add_typer(_local_claude_app, name='lc', hidden=True)

# ── vault-app ────────────────────────────────────────────────────────────────
from sg_compute_specs.vault_app.cli.Cli__Vault_App import app as _vault_app_app
app.add_typer(_vault_app_app, name='vault-app')                                                         # vault-app substrate on EC2 (just-vault / +playwright)
app.add_typer(_vault_app_app, name='va', hidden=True)

# ── catalog ──────────────────────────────────────────────────────────────────
from scripts.catalog import app as _catalog_app
app.add_typer(_catalog_app, name='catalog')

# ── doctor ───────────────────────────────────────────────────────────────────
from scripts.doctor import app as _doctor_app
app.add_typer(_doctor_app, name='doctor')


if __name__ == '__main__':
    app()
