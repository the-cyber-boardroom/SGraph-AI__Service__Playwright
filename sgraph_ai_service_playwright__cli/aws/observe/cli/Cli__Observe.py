# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Cli__Observe
# Typer group for `sg aws observe *` commands.
# Bodies owned by Slice H (v0.2.29__sg-aws-observability).
# Folder is `observe` (not `observability`) to avoid clash with the existing
# __cli/observability/ AMP/OpenSearch/AMG infra package.
# ═══════════════════════════════════════════════════════════════════════════════

import typer

app = typer.Typer(name='observe', help='Unified observability REPL (S3, CloudWatch, CloudTrail).', no_args_is_help=True)

_SLICE = "Slice H owns this body — see library/dev_packs/v0.2.29__sg-aws-observability/"


@app.command('tail')
def tail(source:  str  = typer.Option('', '--source'),
         stream:  str  = typer.Option('', '--stream'),
         since:   str  = typer.Option('1h', '--since'),
         as_json: bool = typer.Option(False, '--json')):
    """Stream recent entries from a source."""
    raise NotImplementedError(_SLICE)


@app.command('query')
def query(query_text: str  = typer.Argument(..., help='Query string.'),
          source:     str  = typer.Option('', '--source'),
          since:      str  = typer.Option('24h', '--since'),
          limit:      int  = typer.Option(100, '--limit'),
          as_json:    bool = typer.Option(False, '--json')):
    """Run a query against a source."""
    raise NotImplementedError(_SLICE)


@app.command('stats')
def stats(source:  str  = typer.Option(..., '--source'),
          stream:  str  = typer.Option('', '--stream'),
          by:      str  = typer.Option(..., '--by'),
          since:   str  = typer.Option('24h', '--since'),
          as_json: bool = typer.Option(False, '--json')):
    """Aggregate statistics from a source."""
    raise NotImplementedError(_SLICE)


@app.command('agent-trace')
def agent_trace(session_id: str  = typer.Argument(..., help='Session correlation ID.'),
                as_json:    bool = typer.Option(False, '--json')):
    """Pull a full cross-source trace for a session ID."""
    raise NotImplementedError(_SLICE)


@app.command('sources')
def sources(as_json: bool = typer.Option(False, '--json')):
    """List connected sources and their status."""
    raise NotImplementedError(_SLICE)


@app.command('replay')
def replay(session_file: str = typer.Argument(..., help='Path to captured session file.')):
    """Replay a captured session."""
    raise NotImplementedError(_SLICE)
