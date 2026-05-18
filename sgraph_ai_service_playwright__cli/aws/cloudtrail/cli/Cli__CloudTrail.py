# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Cli__CloudTrail
# Typer group for `sg aws cloudtrail *` commands.
# Bodies owned by Slice F (v0.2.29__sg-aws-cloudtrail). Read-only — no gate.
# ═══════════════════════════════════════════════════════════════════════════════

import json

import typer
from rich.console import Console
from rich.table   import Table

from sgraph_ai_service_playwright__cli.aws.cloudtrail.service.CloudTrail__AWS__Client import CloudTrail__AWS__Client

app    = typer.Typer(name='cloudtrail', help='CloudTrail events and trail management (read-only).', no_args_is_help=True)
events = typer.Typer(name='events',     help='Query CloudTrail events.',                            no_args_is_help=True)
trail  = typer.Typer(name='trail',      help='Inspect CloudTrail trails.',                          no_args_is_help=True)

app.add_typer(events, name='events')
app.add_typer(trail,  name='trail')


@app.callback()
def _setup_ctx(ctx: typer.Context):
    if ctx.obj is None:
        ctx.obj = {}
    ctx.obj.setdefault('cloudtrail_client', CloudTrail__AWS__Client())


# ── events list ───────────────────────────────────────────────────────────────

@events.command('list')
def events_list(ctx:     typer.Context,
                user:    str  = typer.Option('', '--user',    help='Filter by IAM username.'),
                service: str  = typer.Option('', '--service', help='Filter by event source (e.g. s3.amazonaws.com).'),
                action:  str  = typer.Option('', '--action',  help='Filter by event name (e.g. PutObject).'),
                since:   str  = typer.Option('1h', '--since', help='Time window: 30s, 5m, 2h, 1d, or ISO UTC.'),
                limit:   int  = typer.Option(100, '--limit',  help='Maximum events to return (max 1000).'),
                as_json: bool = typer.Option(False, '--json', help='Output JSON instead of a table.')):
    """List CloudTrail events with optional filters."""
    client = ctx.obj['cloudtrail_client']
    try:
        ev_list = client.lookup_events(user=user, service=service,
                                        action=action, since=since, limit=limit)
    except Exception as exc:
        typer.echo(f'Error: {exc}', err=True)
        raise typer.Exit(1)
    if as_json:
        typer.echo(json.dumps([dict(
            event_id          = e.event_id,
            event_time        = e.event_time,
            event_name        = e.event_name,
            username          = e.username,
            source_ip_address = e.source_ip_address,
            aws_region        = e.aws_region,
            error_code        = e.error_code,
            error_message     = e.error_message,
        ) for e in ev_list], indent=2))
        return
    c = Console(highlight=False)
    c.print()
    c.print(f'  CloudTrail events  ·  {len(ev_list)} returned  ·  window: {since}')
    c.print()
    if not ev_list:
        c.print('  No events found.')
        c.print()
        return
    t = Table(box=None, show_header=True, padding=(0, 2))
    t.add_column('Time',       style='dim',   min_width=20, no_wrap=True)
    t.add_column('Event',      style='bold',  min_width=22)
    t.add_column('User',       style='',      min_width=14)
    t.add_column('Source IP',  style='',      min_width=15)
    t.add_column('Region',     style='cyan',  min_width=12)
    t.add_column('Error',      style='red',   min_width=8)
    for e in ev_list:
        t.add_row(e.event_time[:19], e.event_name, e.username,
                  e.source_ip_address, e.aws_region, e.error_code)
    c.print(t)
    c.print()


# ── events show ───────────────────────────────────────────────────────────────

@events.command('show')
def events_show(ctx:      typer.Context,
                event_id: str  = typer.Argument(..., help='CloudTrail EventId (UUID).'),
                as_json:  bool = typer.Option(False, '--json', help='Output JSON.')):
    """Show full event JSON for a single EventId."""
    client = ctx.obj['cloudtrail_client']
    try:
        event = client.get_event(event_id)
    except Exception as exc:
        typer.echo(f'Error: {exc}', err=True)
        raise typer.Exit(1)
    if event is None:
        typer.echo(f'Event not found: {event_id}', err=True)
        raise typer.Exit(1)
    payload = dict(
        event_id           = event.event_id,
        event_time         = event.event_time,
        event_name         = event.event_name,
        username           = event.username,
        source_ip_address  = event.source_ip_address,
        aws_region         = event.aws_region,
        request_parameters = event.request_parameters,
        response_elements  = event.response_elements,
        resources          = event.resources,
        error_code         = event.error_code,
        error_message      = event.error_message,
    )
    if as_json:
        typer.echo(json.dumps(payload, indent=2))
        return
    c = Console(highlight=False)
    c.print()
    t = Table(box=None, show_header=False, padding=(0, 2))
    t.add_column(style='bold',  min_width=22, no_wrap=True)
    t.add_column()
    for k, v in payload.items():
        t.add_row(k, str(v))
    c.print(t)
    c.print()


# ── trail list ────────────────────────────────────────────────────────────────

@trail.command('list')
def trail_list(ctx:     typer.Context,
               as_json: bool = typer.Option(False, '--json', help='Output JSON instead of a table.')):
    """List all CloudTrail trails in the account."""
    client = ctx.obj['cloudtrail_client']
    try:
        trails = client.list_trails()
    except Exception as exc:
        typer.echo(f'Error: {exc}', err=True)
        raise typer.Exit(1)
    if as_json:
        typer.echo(json.dumps([dict(
            name                         = tr.name,
            s3_bucket_name               = tr.s3_bucket_name,
            home_region                  = tr.home_region,
            is_multi_region_trail        = tr.is_multi_region_trail,
            include_global_service_events= tr.include_global_service_events,
            log_file_validation_enabled  = tr.log_file_validation_enabled,
            trail_arn                    = tr.trail_arn,
            is_logging                   = tr.is_logging,
        ) for tr in trails], indent=2))
        return
    c = Console(highlight=False)
    c.print()
    c.print(f'  CloudTrail trails  ·  {len(trails)} found')
    c.print()
    if not trails:
        c.print('  No trails found.')
        c.print()
        return
    t = Table(box=None, show_header=True, padding=(0, 2))
    t.add_column('Name',          style='bold',  min_width=20)
    t.add_column('Home Region',   style='cyan',  min_width=14)
    t.add_column('S3 Bucket',     style='',      min_width=20)
    t.add_column('Multi-Region',  style='',      min_width=12)
    t.add_column('Global Events', style='',      min_width=13)
    t.add_column('Logging',       style='',      min_width=8)
    for tr in trails:
        t.add_row(
            tr.name,
            tr.home_region,
            tr.s3_bucket_name,
            'yes' if tr.is_multi_region_trail else 'no',
            'yes' if tr.include_global_service_events else 'no',
            'yes' if tr.is_logging else 'no',
        )
    c.print(t)
    c.print()


# ── trail show ────────────────────────────────────────────────────────────────

@trail.command('show')
def trail_show(ctx:     typer.Context,
               name:    str  = typer.Argument(..., help='Trail name or ARN.'),
               as_json: bool = typer.Option(False, '--json', help='Output JSON.')):
    """Show trail configuration."""
    client = ctx.obj['cloudtrail_client']
    try:
        tr = client.describe_trail(name)
    except Exception as exc:
        typer.echo(f'Error: {exc}', err=True)
        raise typer.Exit(1)
    if tr is None:
        typer.echo(f'Trail not found: {name}', err=True)
        raise typer.Exit(1)
    payload = dict(
        name                         = tr.name,
        s3_bucket_name               = tr.s3_bucket_name,
        home_region                  = tr.home_region,
        is_multi_region_trail        = tr.is_multi_region_trail,
        include_global_service_events= tr.include_global_service_events,
        log_file_validation_enabled  = tr.log_file_validation_enabled,
        trail_arn                    = tr.trail_arn,
        is_logging                   = tr.is_logging,
    )
    if as_json:
        typer.echo(json.dumps(payload, indent=2))
        return
    c = Console(highlight=False)
    c.print()
    t = Table(box=None, show_header=False, padding=(0, 2))
    t.add_column(style='bold', min_width=30, no_wrap=True)
    t.add_column()
    for k, v in payload.items():
        t.add_row(k, str(v))
    c.print(t)
    c.print()
