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


app = typer.Typer(name            = 'sg'                                                      ,
                  help            = 'SG/Compute CLI — manage ephemeral EC2 stacks.'        ,
                  no_args_is_help = True                                                    ,
                  add_completion  = False                                                   )

# ── aws ──────────────────────────────────────────────────────────────────────
from sgraph_ai_service_playwright__cli.aws.cli.Cli__Aws import app as _aws_app
app.add_typer(_aws_app, name='aws',          help='AWS resource management (DNS, ACM, …).')

# ── catalog ──────────────────────────────────────────────────────────────────
from scripts.catalog import app as _catalog_app
app.add_typer(_catalog_app, name='catalog',  help='List stack types or live stacks across all specs.')

# ── docker ───────────────────────────────────────────────────────────────────
from scripts.docker_stack import app as _docker_app
app.add_typer(_docker_app, name='docker',    help='Ephemeral Docker EC2 stacks (AL2023 + Docker CE).')
app.add_typer(_docker_app, name='dk',        hidden=True)

# ── doctor ───────────────────────────────────────────────────────────────────
from scripts.doctor import app as _doctor_app
app.add_typer(_doctor_app, name='doctor',    help='Preflight checks — AWS account / region / ECR / IAM.')

# ── elastic ──────────────────────────────────────────────────────────────────
from scripts.elastic import app as _elastic_app
app.add_typer(_elastic_app, name='elastic',  help='Ephemeral Elasticsearch + Kibana EC2 stacks.')
app.add_typer(_elastic_app, name='el',       hidden=True)

# ── firefox ──────────────────────────────────────────────────────────────────
from sgraph_ai_service_playwright__cli.firefox.cli import app as _firefox_app
app.add_typer(_firefox_app, name='firefox',  help='Ephemeral Firefox (noVNC + mitmproxy) EC2 stacks.')
app.add_typer(_firefox_app, name='ff',       hidden=True)

# ── local-claude ─────────────────────────────────────────────────────────────
from sg_compute_specs.local_claude.cli.Cli__Local_Claude import app as _local_claude_app
app.add_typer(_local_claude_app, name='local-claude', help='Ephemeral Local Claude EC2 stacks.')
app.add_typer(_local_claude_app, name='lc',           hidden=True)

# ── neko ─────────────────────────────────────────────────────────────────────
from sgraph_ai_service_playwright__cli.neko.cli import app as _neko_app
app.add_typer(_neko_app, name='neko',        help='Ephemeral Neko (WebRTC browser) EC2 stacks.')
app.add_typer(_neko_app, name='nk',          hidden=True)

# ── nodes ────────────────────────────────────────────────────────────────────
from sg_compute.cli.Cli__Compute__Node import app as _nodes_app
app.add_typer(_nodes_app, name='nodes',      help='List or delete compute nodes across all specs.')

# ── ollama ───────────────────────────────────────────────────────────────────
from sg_compute_specs.ollama.cli.Cli__Ollama import app as _ollama_app
app.add_typer(_ollama_app, name='ollama',    help='Ephemeral Ollama GPU EC2 stacks.')
app.add_typer(_ollama_app, name='ol',        hidden=True)

# ── open-design ──────────────────────────────────────────────────────────────
from sg_compute_specs.open_design.cli import app as _open_design_app
app.add_typer(_open_design_app, name='open-design', help='Ephemeral Open Design EC2 stacks.')
app.add_typer(_open_design_app, name='od',          hidden=True)

# ── opensearch ───────────────────────────────────────────────────────────────
from scripts.opensearch import app as _opensearch_app
app.add_typer(_opensearch_app, name='opensearch', help='Ephemeral OpenSearch + Dashboards EC2 stacks.')
app.add_typer(_opensearch_app, name='os',         hidden=True)

# ── playwright (sg_compute_specs/playwright) ─────────────────────────────────
from sg_compute_specs.playwright.cli.Cli__Playwright import app as _playwright_app
app.add_typer(_playwright_app, name='playwright', help='Ephemeral Playwright EC2 stacks.')
app.add_typer(_playwright_app, name='pw',         hidden=True)

# ── podman ───────────────────────────────────────────────────────────────────
from scripts.podman import app as _podman_app
app.add_typer(_podman_app, name='podman',    help='Ephemeral Podman EC2 stacks (AL2023, SSM).')
app.add_typer(_podman_app, name='lx',        hidden=True)

# ── prometheus ───────────────────────────────────────────────────────────────
from scripts.prometheus import app as _prometheus_app
app.add_typer(_prometheus_app, name='prometheus', help='Ephemeral Prometheus + cAdvisor EC2 stacks.')
app.add_typer(_prometheus_app, name='prom',       hidden=True)

# ── vault-app ────────────────────────────────────────────────────────────────
from sg_compute_specs.vault_app.cli.Cli__Vault_App import app as _vault_app_app
app.add_typer(_vault_app_app, name='vault-app', help='Ephemeral Vault App EC2 stacks.')
app.add_typer(_vault_app_app, name='va',        hidden=True)

# ── vnc ──────────────────────────────────────────────────────────────────────
from scripts.vnc import app as _vnc_app
app.add_typer(_vnc_app, name='vnc',          help='Ephemeral VNC (chromium + nginx + mitmproxy) EC2 stacks.')

# ── observability (hidden) ───────────────────────────────────────────────────
from scripts.observability import app as _observability_app
app.add_typer(_observability_app, name='observability', hidden=True)
app.add_typer(_observability_app, name='ob',            hidden=True)


# ── repl ─────────────────────────────────────────────────────────────────────
import typer as _typer

@app.command()
def repl():
    """Interactive shell — navigate sections and run commands without the sg prefix."""
    from sg_compute.cli.Cli__SG__Repl import run_repl
    run_repl()


if __name__ == '__main__':
    app()
