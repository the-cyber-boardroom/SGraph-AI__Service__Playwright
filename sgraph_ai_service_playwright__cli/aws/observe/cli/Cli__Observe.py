# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Cli__Observe
# Typer group for `sg aws observe *` commands.
# Unified read-only observability REPL across S3, CloudWatch, CloudTrail.
# Folder is `observe` (not `observability`) to avoid clash with the existing
# __cli/observability/ AMP/OpenSearch/AMG infra package.
# ═══════════════════════════════════════════════════════════════════════════════

import json
import sys

import typer

from sgraph_ai_service_playwright__cli.aws._shared.source_contract.Source__Query import Source__Query
from sgraph_ai_service_playwright__cli.aws.observe.Source__Registry              import Source__Registry
from sgraph_ai_service_playwright__cli.aws.observe.service.Observe__Agent__Tracer import Observe__Agent__Tracer
from sgraph_ai_service_playwright__cli.aws.observe.service.Observe__Session__Writer import Observe__Session__Writer

app = typer.Typer(name='observe', help='Unified observability REPL (S3, CloudWatch, CloudTrail).', no_args_is_help=True)

_registry : Source__Registry = None                                     # injectable for tests


def _get_registry() -> Source__Registry:
    global _registry
    if _registry is None:
        _registry = Source__Registry()
    return _registry


# ═══════════════════════════════════════════════════════════════════════════════

@app.command('sources')
def sources(as_json: bool = typer.Option(False, '--json')):
    """List connected sources and their status."""
    reg     = _get_registry()
    entries = reg.list_sources()
    result  = []
    for entry in entries:
        name    = entry['name']
        adapter = entry['adapter']
        try:
            connected = adapter._connected
        except Exception:
            connected = False
        try:
            streams = adapter.list_streams()
            count   = len(streams)
        except Exception:
            count = 0
        result.append({
            'name'         : name,
            'connected'    : connected,
            'stream_count' : count,
            'last_event'   : '',
        })
    if as_json:
        typer.echo(json.dumps(result))
    else:
        if not result:
            typer.echo('No sources registered.')
            return
        for s in result:
            status = 'connected' if s['connected'] else 'disconnected'
            typer.echo(f"  {s['name']:<20} {status:<15} streams={s['stream_count']}")


@app.command('tail')
def tail(source:  str  = typer.Option('', '--source'),
         stream:  str  = typer.Option('', '--stream'),
         since:   str  = typer.Option('1h', '--since'),
         as_json: bool = typer.Option(False, '--json')):
    """Stream recent entries from a source."""
    reg     = _get_registry()
    adapter = reg.get_source(source)
    if adapter is None:
        typer.echo(f'Source not found: {source!r}. Use `sources` to list available.', err=True)
        raise typer.Exit(1)
    src_stream = Source__Stream_obj = adapter.tail(stream=stream, since=since)
    events = list(src_stream)
    if as_json:
        out = [{'timestamp': ev.timestamp, 'source': ev.source,
                'stream': ev.stream, 'message': ev.message} for ev in events]
        typer.echo(json.dumps(out))
    else:
        if not events:
            typer.echo('No events found.')
            return
        for ev in events:
            typer.echo(f"[{ev.timestamp}] {ev.message}")


@app.command('query')
def query(query_text: str  = typer.Argument(..., help='Query string.'),
          source:     str  = typer.Option('', '--source'),
          since:      str  = typer.Option('24h', '--since'),
          limit:      int  = typer.Option(100, '--limit'),
          as_json:    bool = typer.Option(False, '--json')):
    """Run a query against a source."""
    reg     = _get_registry()
    adapter = reg.get_source(source) if source else None
    if source and adapter is None:
        typer.echo(f'Source not found: {source!r}.', err=True)
        raise typer.Exit(1)
    q = Source__Query(text=query_text, source=source, since=since, limit=limit)
    if adapter:
        page = adapter.query(q)
        all_events = page.events
    else:
        all_events = []
        for entry in reg.list_sources():
            try:
                page = entry['adapter'].query(q)
                all_events.extend(page.events)
            except Exception:
                pass
    if as_json:
        out = [{'timestamp': ev.timestamp, 'source': ev.source,
                'stream': ev.stream, 'message': ev.message} for ev in all_events]
        typer.echo(json.dumps(out))
    else:
        if not all_events:
            typer.echo('No results found.')
            return
        for ev in all_events:
            typer.echo(f"[{ev.timestamp}] [{ev.source}/{ev.stream}] {ev.message}")


@app.command('stats')
def stats(source:  str  = typer.Option(..., '--source'),
          stream:  str  = typer.Option('', '--stream'),
          by:      str  = typer.Option(..., '--by'),
          since:   str  = typer.Option('24h', '--since'),
          as_json: bool = typer.Option(False, '--json')):
    """Aggregate statistics from a source."""
    from sgraph_ai_service_playwright__cli.aws._shared.source_contract.Enum__Source__Aggregation import Enum__Source__Aggregation
    reg     = _get_registry()
    adapter = reg.get_source(source)
    if adapter is None:
        typer.echo(f'Source not found: {source!r}.', err=True)
        raise typer.Exit(1)
    try:
        agg = Enum__Source__Aggregation(by)
    except ValueError:
        typer.echo(f'Unknown aggregation {by!r}. Valid: count, sum, avg, min, max, unique', err=True)
        raise typer.Exit(1)
    result = adapter.stats(stream=stream, agg=agg)
    if as_json:
        typer.echo(json.dumps({
            'stream'      : result.stream,
            'aggregation' : result.aggregation,
            'total'       : result.total,
            'buckets'     : result.buckets,
        }))
    else:
        typer.echo(f"source={source}  stream={stream or '(all)'}  agg={by}  total={result.total}")


@app.command('agent-trace')
def agent_trace(session_id: str  = typer.Argument(..., help='Session correlation ID.'),
                as_json:    bool = typer.Option(False, '--json')):
    """Pull a full cross-source trace for a session ID."""
    reg     = _get_registry()
    tracer  = Observe__Agent__Tracer(registry=reg)
    summary = tracer.trace_summary(session_id)
    if as_json:
        typer.echo(json.dumps(summary))
    else:
        typer.echo(f"session_id={session_id}  total_events={summary['total_events']}")
        for src, count in summary['by_source'].items():
            typer.echo(f"  {src}: {count} event(s)")
        for ev in summary['events']:
            typer.echo(f"  [{ev['timestamp']}] [{ev['source']}/{ev['stream']}] {ev['message']}")


@app.command('replay')
def replay(session_file: str = typer.Argument(..., help='Path to captured session file.')):
    """Replay a captured session."""
    writer = Observe__Session__Writer()
    events = writer.read(session_file)
    if not events:
        typer.echo(f'No events found in {session_file!r}.')
        return
    for ev in events:
        ts  = ev.get('timestamp', '')
        src = ev.get('source', '')
        msg = ev.get('message', '')
        typer.echo(f"[{ts}] [{src}] {msg}")
