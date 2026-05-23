# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Cli__Sentinel__Rules
# `sg sentinel rules *` — tiny-core rule visibility.
#
#   sg sentinel rules list            [--json]   # the six MVP rules (metadata)
#   sg sentinel rules show <id>       [--json]   # one rule's metadata
#   sg sentinel rules test            [--json]   # run the engine over the canonical set
#
# `test` shells the real L1 JS engine (node) over a canonical request set and
# renders the resulting signals — the same engine that ships to CloudFront.
# ═══════════════════════════════════════════════════════════════════════════════

import json

import typer
from rich.console import Console
from rich.table   import Table

from sgraph_ai_service_playwright__cli.sentinel.rules.Sentinel__Rule__Registry        import Sentinel__Rule__Registry
from sgraph_ai_service_playwright__cli.sentinel.runtime.layer1.Sentinel__L1__Source   import Sentinel__L1__Source, node_available
from sg_compute.cli.base.Spec__CLI__Errors                                            import spec_cli_errors

app     = typer.Typer(name='rules', help='Tiny-core rule visibility (list / show / test).', no_args_is_help=True)
console = Console()

# (method, path, source_ip) — the canonical request set the parity matrix also drives.
_CANONICAL = [('GET', '/index.html',   '198.51.100.2'),
              ('GET', '/etc/passwd',   '185.10.10.10'),
              ('GET', '/wp-login.php', '91.20.20.20' ),
              ('GET', '/.env',         '77.30.30.30' ),
              ('GET', '/index.html',   '10.0.0.6'    ),                              # banned-ip fixture
              ('GET', '',              '203.0.113.5' )]                              # malformed (empty path)


def _captured(method: str, path: str, source_ip: str) -> dict:
    return {'request_id'  : 'sn-canonical', 'aws_request_id': '',
            'method'      : method, 'path': path, 'querystring': '',
            'host'        : 'static.example.com', 'source_ip': source_ip,
            'user_agent'  : 'sentinel-rules-test',
            'received_at' : '2026-01-01T00:00:00Z', 'cache_status': 'miss'}


@app.command('list')
@spec_cli_errors
def cmd_list(as_json: bool = typer.Option(False, '--json', help='Output as JSON.')):
    """List the six MVP rules and their metadata."""
    rules = Sentinel__Rule__Registry().all()
    if as_json:
        typer.echo(json.dumps([r.json() for r in rules], indent=2))
        return
    t = Table(title='SG/Sentinel — MVP rules (logic in sentinel_l1.js)')
    t.add_column('ID',         style='cyan')
    t.add_column('Name',       style='bold')
    t.add_column('Action',     style='magenta')
    t.add_column('Attack',     style='yellow')
    t.add_column('Confidence', style='dim')
    for r in rules:
        t.add_row(str(r.rule_id), str(r.name), r.action.value, str(r.attack_tag) or '—', str(r.confidence))
    console.print(t)


@app.command('show')
@spec_cli_errors
def cmd_show(rule_id : str  = typer.Argument(..., help='Rule id, e.g. 0012.'),
             as_json : bool = typer.Option(False, '--json', help='Output as JSON.')):
    """Show one rule's metadata."""
    rule = Sentinel__Rule__Registry().get(rule_id)
    if rule is None:
        console.print(f'[red]No such rule:[/red] {rule_id}')
        raise typer.Exit(1)
    if as_json:
        typer.echo(json.dumps(rule.json(), indent=2))
        return
    t = Table(box=None, show_header=False, padding=(0, 2))
    t.add_column(style='bold', min_width=12)
    t.add_column()
    t.add_row('rule_id',     str(rule.rule_id))
    t.add_row('name',        str(rule.name))
    t.add_row('layer',       rule.layer.value)
    t.add_row('action',      rule.action.value)
    t.add_row('attack_tag',  str(rule.attack_tag) or '—')
    t.add_row('confidence',  str(rule.confidence))
    t.add_row('description', str(rule.description))
    console.print()
    console.print(t)
    console.print()


@app.command('test')
@spec_cli_errors
def cmd_test(as_json: bool = typer.Option(False, '--json', help='Output as JSON.')):
    """Run the L1 engine over the canonical request set and show each verdict."""
    if not node_available():
        console.print('[yellow]node not found on PATH — cannot run the L1 engine.[/yellow]')
        raise typer.Exit(1)
    source  = Sentinel__L1__Source()
    results = [source.evaluate(_captured(m, p, ip)) for (m, p, ip) in _CANONICAL]
    if as_json:
        typer.echo(json.dumps(results, indent=2))
        return
    t = Table(title='SG/Sentinel — canonical request set')
    t.add_column('Method',  style='cyan')
    t.add_column('Path',    style='bold')
    t.add_column('IP',      style='dim')
    t.add_column('Verdict', style='magenta')
    t.add_column('Rule',    style='yellow')
    t.add_column('Action')
    for (m, p, ip), sig in zip(_CANONICAL, results):
        verdict = sig.get('verdict', '')
        colour  = 'red' if verdict == 'block' else 'green'
        t.add_row(m, p or '(empty)', ip, f'[{colour}]{verdict}[/{colour}]',
                  sig.get('rule_id', ''), sig.get('action', ''))
    console.print(t)
