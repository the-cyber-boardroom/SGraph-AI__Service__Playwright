# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — sg_edge: Cli__SG_Edge__Bench
# Typer app for `sg edge bench` (= `sg edge_bench`) — the doc-05 measurement harness.
#
#   list                       list the scenario catalog (id / tier / target)
#   scenario <ID>              run one scenario (P-03, F-01, X-12, …)
#   primitives | flows | failures   run a whole tier
#   full                       run every scenario
#   --repeat N --target local|aws-bench --json --output FILE
#
# Commands have no logic — they call Edge_Bench__Suite and render with rich.Console.
# LOCAL scenarios run in-process against a temp `sg edge local` stack; AWS_BENCH
# scenarios are skipped (live backend is Slice-5/6, not built). Exit code is
# non-zero when any non-skipped scenario fails (CI gate).
# ═══════════════════════════════════════════════════════════════════════════════

import json

import typer
from rich.console import Console

app = typer.Typer(name='bench', help='SG/Edge bench harness (doc-05).', no_args_is_help=True)

_suite_factory = None                                                                # tests may assign a callable → Edge_Bench__Suite


def _suite():
    if _suite_factory is not None:
        return _suite_factory()
    from sg_compute_specs.sg_edge.bench.Edge_Bench__Suite import Edge_Bench__Suite
    return Edge_Bench__Suite()


def _target(name: str):
    from sg_compute_specs.sg_edge.bench.enums.Enum__Edge_Bench__Target import Enum__Edge_Bench__Target
    try:
        return Enum__Edge_Bench__Target(name)
    except ValueError:
        raise typer.BadParameter(f"--target must be 'local' or 'aws-bench', got {name!r}")


def _tier(name: str):
    from sg_compute_specs.sg_edge.bench.enums.Enum__Edge_Bench__Tier import Enum__Edge_Bench__Tier
    return Enum__Edge_Bench__Tier(name)


# ── catalog ───────────────────────────────────────────────────────────────────

@app.command(name='list', help='List the scenario catalog (id / tier / target).')
def list_scenarios(output_json: bool = typer.Option(False, '--json')):
    c = Console(highlight=False)
    descs = _suite().list()
    if output_json:
        print(json.dumps([d.json() for d in descs], indent=2))
        return
    c.print('\n  [bold]SG/Edge bench — scenario catalog[/]')
    for d in descs:
        tag = '[green]local[/]' if str(d.target) == 'local' else '[dim]aws-bench[/]'
        c.print(f'    [cyan]{d.id}[/]  [{str(d.tier):<9}] {tag:<18}  [bold]{d.name}[/]')
        c.print(f'        [dim]{d.doc}[/]')
    c.print('\n  [dim]   run: sg edge bench scenario F-01   |   tier: sg edge bench primitives   |   all: sg edge bench full[/]\n')


# ── runners ───────────────────────────────────────────────────────────────────

@app.command(name='scenario', help='Run one bench scenario by id (P-03, F-01, X-12, …).')
def scenario(scenario_id: str = typer.Argument(..., metavar='SCENARIO_ID', help='Scenario id e.g. F-01'),
             repeat     : int = typer.Option(5, '--repeat', '-n', help='Runs per scenario'),
             target     : str = typer.Option('local', '--target', help='local | aws-bench'),
             output_json: bool = typer.Option(False, '--json', help='Machine-readable JSON output'),
             output     : str = typer.Option('', '--output', help='Write the suite JSON to this file')):
    c = Console(highlight=False)
    try:
        result = _suite().run_scenario(scenario_id, repeat=repeat, target=_target(target))
    except ValueError as exc:
        c.print(f'\n  [red]✗  {exc}[/]\n')
        raise typer.Exit(1)
    _render_one(c, result)
    if output:
        _write_json(output, [result.json()])
    if output_json:
        print(json.dumps(result.json(), indent=2))
    if not result.passed and not result.skipped:
        raise typer.Exit(1)


@app.command(name='primitives', help='Run all primitive-tier scenarios.')
def primitives(repeat: int = typer.Option(5, '--repeat', '-n'),
               target: str = typer.Option('local', '--target'),
               output_json: bool = typer.Option(False, '--json'),
               output: str = typer.Option('', '--output')):
    _run_tier('primitive', repeat, target, output_json, output)


@app.command(name='flows', help='Run all flow-tier scenarios.')
def flows(repeat: int = typer.Option(5, '--repeat', '-n'),
          target: str = typer.Option('local', '--target'),
          output_json: bool = typer.Option(False, '--json'),
          output: str = typer.Option('', '--output')):
    _run_tier('flow', repeat, target, output_json, output)


@app.command(name='failures', help='Run all failure-tier scenarios.')
def failures(repeat: int = typer.Option(5, '--repeat', '-n'),
             target: str = typer.Option('local', '--target'),
             output_json: bool = typer.Option(False, '--json'),
             output: str = typer.Option('', '--output')):
    _run_tier('failure', repeat, target, output_json, output)


@app.command(name='full', help='Run every scenario (primitives + flows + failures).')
def full(repeat: int = typer.Option(5, '--repeat', '-n'),
         target: str = typer.Option('local', '--target'),
         output_json: bool = typer.Option(False, '--json'),
         output: str = typer.Option('', '--output')):
    c     = Console(highlight=False)
    suite = _suite().run_all(repeat=repeat, target=_target(target))
    _render_suite(c, suite)
    _emit(suite, output, output_json)
    if not suite.passed:
        raise typer.Exit(1)


def _run_tier(tier_name, repeat, target, output_json, output):
    c     = Console(highlight=False)
    suite = _suite().run_tier(_tier(tier_name), repeat=repeat, target=_target(target))
    _render_suite(c, suite)
    _emit(suite, output, output_json)
    if not suite.passed:
        raise typer.Exit(1)


# ── rendering ─────────────────────────────────────────────────────────────────

_VERDICT_ICON = {'pass': '[green]pass[/]', 'warn': '[yellow]warn[/]', 'fail': '[red]fail[/]'}


def _render_one(c: Console, result) -> None:
    c.print()
    _render_result(c, result)
    c.print()


def _render_suite(c: Console, suite) -> None:
    ran     = [r for r in suite.results if not r.skipped]
    skipped = [r for r in suite.results if r.skipped]
    c.print(f'\n  [bold]SG/Edge bench[/]  target=[cyan]{suite.target}[/]  run_id=[dim]{suite.run_id}[/]')
    for r in suite.results:
        _render_result(c, r)
    overall = '[green]PASS[/]' if suite.passed else '[red]FAIL[/]'
    passed  = sum(1 for r in ran if r.passed)
    c.print(f'\n  {overall}  {passed}/{len(ran)} ran passed  [dim]({len(skipped)} skipped — aws-bench)[/]\n')


def _render_result(c: Console, r) -> None:
    if r.skipped:
        c.print(f'  [dim]·[/]  [cyan]{r.id}[/]  {r.name}  [dim][SKIP] {r.note}[/]')
        return
    head = '[green]PASS[/]' if r.passed else '[red]FAIL[/]'
    c.print(f'  {head}  [cyan]{r.id}[/]  [bold]{r.name}[/]  [dim]({r.runs} runs)[/]')
    for m in r.metrics:
        icon = _VERDICT_ICON.get(str(m.verdict), str(m.verdict))
        c.print(f'      {icon} {m.name:<16} p95={int(m.p95):>5}ms  '
                f'[dim]p50={int(m.p50)} p99={int(m.p99)}  gate<{int(m.target)} fail>={int(m.hard_fail)}[/]')
    if r.note:
        c.print(f'      [red]{r.note}[/]')


# ── output ────────────────────────────────────────────────────────────────────

def _emit(suite, output: str, output_json: bool) -> None:
    if output:
        _write_json(output, suite.json())
    if output_json:
        print(json.dumps(suite.json(), indent=2))


def _write_json(path: str, payload) -> None:
    import os
    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)
    with open(path, 'w') as f:
        f.write(json.dumps(payload, indent=2))
