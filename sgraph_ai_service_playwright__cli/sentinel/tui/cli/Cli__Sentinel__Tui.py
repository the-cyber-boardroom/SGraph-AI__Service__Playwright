# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Cli__Sentinel__Tui
# `sg sentinel tui <screen>` — the operator TUI surfaces (Textual). Textual is
# imported lazily inside each command, so registering this sub-app never requires
# textual — the rest of `sg sentinel` works whether or not textual is present.
#
#   rules    The six tiny-core rules (↑/↓ select, enter → detail)
#   logs     Records in the sink (use case 1) — enter → trace by request id
#   blocks   Blocked requests grouped by reason/rule (use case 2)
#   status   Reality + the exact materialised L1 engine code (mockups 1 + 7)
#
# Every command falls back to plain text (or --json) when stdout is not a TTY, so it
# is safe to pipe / run in CI. The sink is the local-FS sink (SG_SENTINEL__LOCAL_SINK_DIR);
# tests assign _source_factory to inject an in-memory source (no AWS, no node).
# ═══════════════════════════════════════════════════════════════════════════════

import json
import sys

import typer

app = typer.Typer(name='tui', help='SG/Sentinel operator TUI surfaces (Textual).', no_args_is_help=True)

_source_factory = None                                                               # tests assign callable() -> Sentinel__TUI__Source


@app.callback()
def main():                                                                          # force group behaviour
    pass


def _sink_label() -> str:
    from sgraph_ai_service_playwright__cli.sentinel.runtime.local.Sentinel__Local__Harness import default_local_sink_dir
    return default_local_sink_dir()


def _source():
    if _source_factory is not None:
        return _source_factory()
    from sgraph_ai_service_playwright__cli.sentinel.runtime.local.Sentinel__Local__Harness import default_local_sink_dir
    from sgraph_ai_service_playwright__cli.sentinel.service.log_sink.Local_FS__Log__Sink    import Local_FS__Log__Sink
    from sgraph_ai_service_playwright__cli.sentinel.tui.source.Sentinel__TUI__Source        import Sentinel__TUI__Source
    return Sentinel__TUI__Source(log_sink=Local_FS__Log__Sink(root_dir=default_local_sink_dir()))


@app.command('rules', help='The six tiny-core rules (enter → detail).')
def rules(as_json: bool = typer.Option(False, '--json', help='Output as JSON.')):
    source = _source()
    if as_json:
        typer.echo(json.dumps([r.json() for r in source.rules()], indent=2)); return
    if not sys.stdout.isatty():
        from sgraph_ai_service_playwright__cli.sentinel.tui.screens.Sentinel__TUI__Rules__Render import rules_plain
        print(rules_plain(source.rules())); return
    from sgraph_ai_service_playwright__cli.sentinel.tui.screens.Sentinel__TUI__Screen__Rules import Sentinel__TUI__Screen__Rules
    Sentinel__TUI__Screen__Rules(source=source).run()


@app.command('logs', help='Records in the sink (enter → trace by request id).')
def logs(as_json: bool = typer.Option(False, '--json', help='Output as JSON.')):
    source = _source()
    if as_json:
        typer.echo(json.dumps([r.json() for r in source.records()], indent=2)); return
    if not sys.stdout.isatty():
        from sgraph_ai_service_playwright__cli.sentinel.tui.screens.Sentinel__TUI__Logs__Render import logs_plain
        print(logs_plain(source.records(), _sink_label())); return
    from sgraph_ai_service_playwright__cli.sentinel.tui.screens.Sentinel__TUI__Screen__Logs import Sentinel__TUI__Screen__Logs
    Sentinel__TUI__Screen__Logs(source=source, sink_label=_sink_label()).run()


@app.command('blocks', help='Blocked requests grouped by reason/rule.')
def blocks(as_json: bool = typer.Option(False, '--json', help='Output as JSON.')):
    source = _source()
    groups = source.block_groups()
    if as_json:
        typer.echo(json.dumps([g.json() for g in groups], indent=2)); return
    if not sys.stdout.isatty():
        from sgraph_ai_service_playwright__cli.sentinel.tui.screens.Sentinel__TUI__Blocks__Render import blocks_plain
        print(blocks_plain(groups, sum(g.count for g in groups))); return
    from sgraph_ai_service_playwright__cli.sentinel.tui.screens.Sentinel__TUI__Screen__Blocks import Sentinel__TUI__Screen__Blocks
    Sentinel__TUI__Screen__Blocks(source=source).run()


@app.command('status', help='Reality + the exact materialised L1 engine code.')
def status(as_json: bool = typer.Option(False, '--json', help='Output as JSON.')):
    source = _source()
    if as_json:
        typer.echo(json.dumps(source.status().json(), indent=2)); return
    if not sys.stdout.isatty():
        from sgraph_ai_service_playwright__cli.sentinel.tui.screens.Sentinel__TUI__Status__Render import status_plain
        print(status_plain(source.status(), _sink_label())); return
    from sgraph_ai_service_playwright__cli.sentinel.tui.screens.Sentinel__TUI__Screen__Status import Sentinel__TUI__Screen__Status
    Sentinel__TUI__Screen__Status(source=source, sink_label=_sink_label()).run()


@app.command('traffic', help='Replay the use-case corpus (L1+L2) and show accuracy + latency.')
def traffic(repeat  : int  = typer.Option(1, '--repeat', '-n', help='Replays of the corpus per run.'),
            as_json : bool = typer.Option(False, '--json', help='Output the report as JSON (runs once).')):
    from sgraph_ai_service_playwright__cli.sentinel.runtime.layer1.Sentinel__L1__Source        import node_available
    from sgraph_ai_service_playwright__cli.sentinel.runtime.local.Sentinel__Local__Harness     import Sentinel__Local__Harness
    from sgraph_ai_service_playwright__cli.sentinel.service.log_sink.InMemory__Log__Sink        import InMemory__Log__Sink
    from sgraph_ai_service_playwright__cli.sentinel.traffic.service.Sentinel__Traffic__Generator import Sentinel__Traffic__Generator
    if not node_available():
        print('node not found on PATH — cannot run the L1 engine.'); raise typer.Exit(1)
    generator = Sentinel__Traffic__Generator(harness=Sentinel__Local__Harness(log_sink=InMemory__Log__Sink()))
    if as_json or not sys.stdout.isatty():                                           # piped / CI / --json → run once, print
        from sgraph_ai_service_playwright__cli.sentinel.traffic.service.Sentinel__Traffic__Corpus          import Sentinel__Traffic__Corpus
        from sgraph_ai_service_playwright__cli.sentinel.traffic.service.Sentinel__Traffic__Report__Builder import Sentinel__Traffic__Report__Builder
        from sgraph_ai_service_playwright__cli.sentinel.tui.screens.Sentinel__TUI__Traffic__Render         import traffic_plain
        results = generator.run_local(Sentinel__Traffic__Corpus().cases(), repeat=repeat)
        report  = Sentinel__Traffic__Report__Builder().build(results, mode='local')
        if as_json:
            typer.echo(json.dumps({'report': report.json(), 'results': [r.json() for r in results]}, indent=2)); return
        print(traffic_plain(report, results)); return
    from sgraph_ai_service_playwright__cli.sentinel.tui.screens.Sentinel__TUI__Screen__Traffic import Sentinel__TUI__Screen__Traffic
    Sentinel__TUI__Screen__Traffic(generator=generator).run()
