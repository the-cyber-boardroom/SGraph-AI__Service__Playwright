# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Cli__CloudTrail
# Typer group for `sg aws cloudtrail *` commands.
# Bodies owned by Slice F (v0.2.29__sg-aws-cloudtrail). Read-only — no gate.
# ═══════════════════════════════════════════════════════════════════════════════

import typer

app    = typer.Typer(name='cloudtrail', help='CloudTrail events and trail management (read-only).', no_args_is_help=True)
events = typer.Typer(name='events',     help='Query CloudTrail events.',                            no_args_is_help=True)
trail  = typer.Typer(name='trail',      help='Inspect CloudTrail trails.',                          no_args_is_help=True)

app.add_typer(events, name='events')
app.add_typer(trail,  name='trail')

_SLICE = "Slice F owns this body — see library/dev_packs/v0.2.29__sg-aws-cloudtrail/"


@events.command('list')
def events_list(user:    str  = typer.Option('', '--user'),
                service: str  = typer.Option('', '--service'),
                action:  str  = typer.Option('', '--action'),
                since:   str  = typer.Option('1h', '--since'),
                limit:   int  = typer.Option(100, '--limit'),
                as_json: bool = typer.Option(False, '--json')):
    """List CloudTrail events with optional filters."""
    raise NotImplementedError(_SLICE)


@events.command('show')
def events_show(event_id: str  = typer.Argument(...),
                as_json:  bool = typer.Option(False, '--json')):
    """Show full event JSON."""
    raise NotImplementedError(_SLICE)


@trail.command('list')
def trail_list(as_json: bool = typer.Option(False, '--json')):
    """List all CloudTrail trails in the account."""
    raise NotImplementedError(_SLICE)


@trail.command('show')
def trail_show(name:    str  = typer.Argument(...),
               as_json: bool = typer.Option(False, '--json')):
    """Show trail configuration."""
    raise NotImplementedError(_SLICE)
