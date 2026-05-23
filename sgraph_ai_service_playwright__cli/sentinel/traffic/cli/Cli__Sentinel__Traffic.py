# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Cli__Sentinel__Traffic
# `sg sentinel traffic *` — drive the use-case corpus and measure SG/Sentinel.
#
#   sg sentinel traffic cases              [--json]            # list the corpus
#   sg sentinel traffic gen   [--repeat N] [--json]            # in-process (L1+L2): rule accuracy + decision latency
#   sg sentinel traffic send  --url <base> [--repeat N] [--json]  # real HTTP at a target (echo server / live CF)
#
# `gen` is the faithful rule tester (needs node). `send` measures end-to-end against
# any URL — point it at `sg sentinel echo serve` for a baseline, or at a deployed
# CloudFront distribution to see the edge block obvious-bad before it reaches origin.
# ═══════════════════════════════════════════════════════════════════════════════

import json

import typer
from rich.console import Console
from rich.table   import Table

from sgraph_ai_service_playwright__cli.sentinel.runtime.layer1.Sentinel__L1__Source        import node_available
from sgraph_ai_service_playwright__cli.sentinel.runtime.local.Sentinel__Local__Harness     import Sentinel__Local__Harness
from sgraph_ai_service_playwright__cli.sentinel.service.log_sink.InMemory__Log__Sink        import InMemory__Log__Sink
from sgraph_ai_service_playwright__cli.sentinel.traffic.service.Sentinel__Traffic__Corpus           import Sentinel__Traffic__Corpus
from sgraph_ai_service_playwright__cli.sentinel.traffic.service.Sentinel__Traffic__Generator        import Sentinel__Traffic__Generator
from sgraph_ai_service_playwright__cli.sentinel.traffic.service.Sentinel__Traffic__Report__Builder  import Sentinel__Traffic__Report__Builder
from sg_compute.cli.base.Spec__CLI__Errors                                                 import spec_cli_errors

app     = typer.Typer(name='traffic', help='Use-case traffic generator + measurement.', no_args_is_help=True)
console = Console()


def _print_report(report, results) -> None:
    console.print(f'[bold]SG/Sentinel traffic report[/]  [dim](mode={report.mode})[/]')
    console.print(f'  total {report.total}   [green]allowed {report.allowed}[/]   [red]blocked {report.blocked}[/]   '
                  f'accuracy [bold]{report.accuracy_pct}%[/]')
    console.print(f'  malicious blocked  {report.malicious_blocked}/{report.malicious_total}')
    console.print(f'  benign allowed     {report.benign_allowed}/{report.benign_total}')
    console.print(f'  latency ms         min {report.latency_min_ms}  p50 {report.latency_p50_ms}  '
                  f'p95 {report.latency_p95_ms}  max {report.latency_max_ms}  avg {report.latency_avg_ms}')
    misses = [r for r in results if not r.matched]
    if misses:
        t = Table(title='mismatches (observed ≠ expected)')
        t.add_column('Case', style='cyan'); t.add_column('Expected'); t.add_column('Observed', style='red')
        for r in misses:
            t.add_row(str(r.name), f'{r.expected_verdict.value}/{r.expected_rule}',
                      f'{r.observed_verdict.value}/{r.observed_rule or "?"}')
        console.print(t)


@app.command('cases')
@spec_cli_errors
def cmd_cases(as_json: bool = typer.Option(False, '--json', help='Output as JSON.')):
    """List the use-case traffic corpus."""
    cases = Sentinel__Traffic__Corpus().cases()
    if as_json:
        typer.echo(json.dumps([c.json() for c in cases], indent=2)); return
    t = Table(title='SG/Sentinel — traffic corpus')
    t.add_column('Case', style='cyan'); t.add_column('Method'); t.add_column('Path', style='bold')
    t.add_column('Source IP', style='dim'); t.add_column('Category'); t.add_column('Expect')
    for c in cases:
        t.add_row(str(c.name), str(c.method), str(c.path) or '(empty)', str(c.source_ip),
                  c.category.value, f'{c.expected_verdict.value}/{c.expected_rule}')
    console.print(t)


@app.command('gen')
@spec_cli_errors
def cmd_gen(repeat  : int  = typer.Option(1, '--repeat', '-n', help='Replays of the whole corpus.'),
            as_json : bool = typer.Option(False, '--json', help='Output as JSON.')):
    """Replay the corpus in-process through L1+L2 — rule accuracy + decision latency."""
    if not node_available():
        console.print('[red]node not found on PATH — cannot run the L1 engine.[/red]'); raise typer.Exit(1)
    generator = Sentinel__Traffic__Generator(harness=Sentinel__Local__Harness(log_sink=InMemory__Log__Sink()))
    results   = generator.run_local(Sentinel__Traffic__Corpus().cases(), repeat=repeat)
    report    = Sentinel__Traffic__Report__Builder().build(results, mode='local')
    if as_json:
        typer.echo(json.dumps({'report': report.json(), 'results': [r.json() for r in results]}, indent=2)); return
    _print_report(report, results)


@app.command('send')
@spec_cli_errors
def cmd_send(url     : str  = typer.Option(..., '--url', help='Target base URL (echo server or live CF distribution).'),
             repeat  : int  = typer.Option(1, '--repeat', '-n', help='Replays of the whole corpus.'),
             as_json : bool = typer.Option(False, '--json', help='Output as JSON.')):
    """Send the corpus over real HTTP to a target — end-to-end status + latency."""
    generator = Sentinel__Traffic__Generator(harness=Sentinel__Local__Harness(log_sink=InMemory__Log__Sink()))
    results   = generator.run_http(Sentinel__Traffic__Corpus().cases(), base_url=url, repeat=repeat)
    report    = Sentinel__Traffic__Report__Builder().build(results, mode='http')
    if as_json:
        typer.echo(json.dumps({'report': report.json(), 'results': [r.json() for r in results]}, indent=2)); return
    _print_report(report, results)
