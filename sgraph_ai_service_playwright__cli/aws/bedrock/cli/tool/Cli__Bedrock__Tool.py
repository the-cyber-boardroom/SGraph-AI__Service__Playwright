# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Cli__Bedrock__Tool
# Typer group for `sg aws bedrock tool *` commands.
# EXPERIMENTAL — requires AgentCore SDK.
# All session-mutating commands are gated by SG_AWS__BEDROCK__ALLOW_MUTATIONS=1.
# ═══════════════════════════════════════════════════════════════════════════════

import json
from typing                                                                      import Optional

import typer
from rich.console                                                                import Console
from rich.table                                                                  import Table

from sg_compute.cli.base.Spec__CLI__Errors                                       import spec_cli_errors
from sgraph_ai_service_playwright__cli.aws._shared.Mutation__Gate               import require_mutation_gate
from sgraph_ai_service_playwright__cli.aws.bedrock.service.Bedrock__Tool__AWS__Client import Bedrock__Tool__AWS__Client
from sgraph_ai_service_playwright__cli.aws.bedrock.service.Bedrock__Capture__Writer   import Bedrock__Capture__Writer

BEDROCK_GATE = 'SG_AWS__BEDROCK__ALLOW_MUTATIONS'

tool_app              = typer.Typer(name='tool',                help='Bedrock inline tools — EXPERIMENTAL.',          no_args_is_help=True)
browser_app           = typer.Typer(name='browser',             help='AgentCore browser tool sessions.',              no_args_is_help=True)
browser_session_app   = typer.Typer(name='session',             help='Browser session management.',                   no_args_is_help=True)
code_interp_app       = typer.Typer(name='code-interpreter',    help='AgentCore code-interpreter tool sessions.',     no_args_is_help=True)
code_session_app      = typer.Typer(name='session',             help='Code-interpreter session management.',          no_args_is_help=True)

tool_app.add_typer(browser_app,        name='browser')
browser_app.add_typer(browser_session_app, name='session')
tool_app.add_typer(code_interp_app,    name='code-interpreter')
code_interp_app.add_typer(code_session_app, name='session')


def _client() -> Bedrock__Tool__AWS__Client:
    return Bedrock__Tool__AWS__Client()


# ══════════════════════════════════════════════════════════════════════════════
# Browser sessions
# ══════════════════════════════════════════════════════════════════════════════

@browser_session_app.command('start')
@require_mutation_gate(BEDROCK_GATE)
@spec_cli_errors
def browser_session_start(
    region      : Optional[str] = typer.Option(None,  '--region', '-r', help='AWS region (default: current region).'),
    yes         : bool          = typer.Option(False, '--yes',   '-y',  help='Skip confirmation.'),
    json_output : bool          = typer.Option(False, '--json',         help='Output JSON.'),
):
    """Start a new AgentCore browser session. [EXPERIMENTAL]"""
    if not yes:
        typer.confirm('Start browser session?', abort=True)
    client  = _client()
    session = client.browser_start(region=region)
    writer  = Bedrock__Capture__Writer()
    path   = writer.write_browser_action(str(session.session_id),
                                         {'action': 'start', 'region': session.region})
    if json_output:
        typer.echo(json.dumps(dict(session_id   = str(session.session_id),
                                   tool_type    = str(session.tool_type) ,
                                   status       = session.status         ,
                                   region       = session.region         ,
                                   capture_path = str(path)              ), indent=2))
        return
    c = Console(highlight=False)
    c.print(f'\n  Browser session started: [bold]{session.session_id}[/]  region={session.region}  capture={path}\n')


@browser_session_app.command('list')
@spec_cli_errors
def browser_session_list(
    json_output: bool = typer.Option(False, '--json', help='Output JSON.'),
):
    """List active AgentCore browser sessions. [EXPERIMENTAL]"""
    client   = _client()
    sessions = client.browser_list()
    if json_output:
        typer.echo(json.dumps([dict(session_id = str(s.session_id),
                                    status     = s.status         ,
                                    region     = s.region         ) for s in sessions], indent=2))
        return
    c = Console(highlight=False)
    c.print()
    t = Table(box=None, show_header=True, padding=(0, 2))
    t.add_column('Session ID', style='bold', min_width=20)
    t.add_column('Status',     style='cyan', min_width=10)
    t.add_column('Region',     style='',     min_width=12)
    for s in sessions:
        t.add_row(str(s.session_id), s.status, s.region)
    c.print(t)
    c.print()


@browser_session_app.command('navigate')
@require_mutation_gate(BEDROCK_GATE)
@spec_cli_errors
def browser_session_navigate(
    session_id : str  = typer.Argument(..., help='Browser session ID.'),
    url        : str  = typer.Argument(..., help='URL to navigate to.'),
    region     : Optional[str] = typer.Option(None,  '--region', '-r', help='AWS region.'),
    yes        : bool          = typer.Option(False, '--yes',   '-y',  help='Skip confirmation.'),
):
    """Navigate a browser session to a URL. [EXPERIMENTAL]"""
    if not yes:
        typer.confirm(f'Navigate session {session_id!r} to {url!r}?', abort=True)
    client = _client()
    resp   = client.browser_navigate(session_id, url, region=region)
    writer = Bedrock__Capture__Writer()
    writer.write_browser_action(session_id, {'action': 'navigate', 'url': url, 'response': resp})
    c = Console(highlight=False)
    c.print(f'\n  Navigated session {session_id} to {url}\n')


@browser_session_app.command('screenshot')
@require_mutation_gate(BEDROCK_GATE)
@spec_cli_errors
def browser_session_screenshot(
    session_id  : str          = typer.Argument(..., help='Browser session ID.'),
    output_file : Optional[str]= typer.Option(None, '--output', '-o', help='Save screenshot to this path.'),
    region      : Optional[str]= typer.Option(None, '--region', '-r', help='AWS region.'),
    yes         : bool         = typer.Option(False,'--yes',    '-y', help='Skip confirmation.'),
):
    """Take a screenshot from a browser session. [EXPERIMENTAL]"""
    if not yes:
        typer.confirm(f'Screenshot session {session_id!r}?', abort=True)
    client     = _client()
    image_data = client.browser_screenshot(session_id, region=region)
    writer     = Bedrock__Capture__Writer()
    folder  = writer.browser_session_path(session_id)
    folder.mkdir(parents=True, exist_ok=True)
    if output_file:
        import shutil, os
        out = output_file
    else:
        import uuid
        out = str(folder / f'screenshot_{uuid.uuid4().hex[:8]}.png')
    if image_data:
        with open(out, 'wb') as fh:
            fh.write(image_data)
    c = Console(highlight=False)
    c.print(f'\n  Screenshot saved: {out}\n')


@browser_session_app.command('stop')
@require_mutation_gate(BEDROCK_GATE)
@spec_cli_errors
def browser_session_stop(
    session_id : str  = typer.Argument(..., help='Browser session ID.'),
    region     : Optional[str] = typer.Option(None,  '--region', '-r', help='AWS region.'),
    yes        : bool          = typer.Option(False, '--yes',   '-y',  help='Skip confirmation.'),
):
    """Stop a browser session. [EXPERIMENTAL]"""
    if not yes:
        typer.confirm(f'Stop browser session {session_id!r}?', abort=True)
    client = _client()
    client.browser_stop(session_id, region=region)
    c = Console(highlight=False)
    c.print(f'\n  Browser session {session_id} stopped.\n')


# ══════════════════════════════════════════════════════════════════════════════
# Code-interpreter sessions
# ══════════════════════════════════════════════════════════════════════════════

@code_session_app.command('start')
@require_mutation_gate(BEDROCK_GATE)
@spec_cli_errors
def code_session_start(
    language    : str          = typer.Option('python', '--language', '-l', help='Language: python, javascript, typescript.'),
    region      : Optional[str]= typer.Option(None,    '--region',   '-r', help='AWS region.'),
    yes         : bool         = typer.Option(False,   '--yes',      '-y', help='Skip confirmation.'),
    json_output : bool         = typer.Option(False,   '--json',          help='Output JSON.'),
):
    """Start a code-interpreter session. [EXPERIMENTAL]"""
    if not yes:
        typer.confirm(f'Start code-interpreter session (language={language})?', abort=True)
    client  = _client()
    session = client.code_interpreter_start(language=language, region=region)
    writer  = Bedrock__Capture__Writer()
    path   = writer.write_code_run(str(session.session_id),
                                   {'action': 'start', 'language': language, 'region': session.region})
    if json_output:
        typer.echo(json.dumps(dict(session_id   = str(session.session_id),
                                   tool_type    = str(session.tool_type) ,
                                   language     = session.language       ,
                                   status       = session.status         ,
                                   region       = session.region         ,
                                   capture_path = str(path)              ), indent=2))
        return
    c = Console(highlight=False)
    c.print(f'\n  Code-interpreter session started: [bold]{session.session_id}[/]  language={language}  capture={path}\n')


@code_session_app.command('run')
@require_mutation_gate(BEDROCK_GATE)
@spec_cli_errors
def code_session_run(
    session_id  : str          = typer.Argument(..., help='Code-interpreter session ID.'),
    code        : str          = typer.Option(...,   '--code', '-c', help='Code to execute.'),
    region      : Optional[str]= typer.Option(None, '--region',     help='AWS region.'),
    yes         : bool         = typer.Option(False,'--yes',  '-y', help='Skip confirmation.'),
    json_output : bool         = typer.Option(False,'--json',       help='Output JSON.'),
):
    """Run code in a code-interpreter session. [EXPERIMENTAL]"""
    if not yes:
        typer.confirm(f'Run code in session {session_id!r}?', abort=True)
    client = _client()
    result = client.code_interpreter_run(session_id, code, region=region)
    writer = Bedrock__Capture__Writer()
    writer.write_code_run(session_id, {'action': 'run', 'code': code, 'result': result})
    if json_output:
        typer.echo(json.dumps(result, indent=2, default=str))
        return
    c = Console(highlight=False)
    c.print()
    c.print(str(result))
    c.print()


@code_session_app.command('stop')
@require_mutation_gate(BEDROCK_GATE)
@spec_cli_errors
def code_session_stop(
    session_id : str          = typer.Argument(..., help='Code-interpreter session ID.'),
    region     : Optional[str]= typer.Option(None, '--region', '-r', help='AWS region.'),
    yes        : bool         = typer.Option(False,'--yes',    '-y', help='Skip confirmation.'),
):
    """Stop a code-interpreter session. [EXPERIMENTAL]"""
    if not yes:
        typer.confirm(f'Stop code-interpreter session {session_id!r}?', abort=True)
    client = _client()
    client.code_interpreter_stop(session_id, region=region)
    c = Console(highlight=False)
    c.print(f'\n  Code-interpreter session {session_id} stopped.\n')


@code_session_app.command('list')
@spec_cli_errors
def code_session_list(
    json_output: bool = typer.Option(False, '--json', help='Output JSON.'),
):
    """List code-interpreter sessions. [EXPERIMENTAL]"""
    client   = _client()
    sessions = client.code_interpreter_list()
    if json_output:
        typer.echo(json.dumps([dict(session_id = str(s.session_id),
                                    language   = s.language        ,
                                    status     = s.status          ,
                                    region     = s.region          ) for s in sessions], indent=2))
        return
    c = Console(highlight=False)
    c.print()
    t = Table(box=None, show_header=True, padding=(0, 2))
    t.add_column('Session ID', style='bold', min_width=20)
    t.add_column('Language',   style='cyan', min_width=12)
    t.add_column('Status',     style='',     min_width=10)
    t.add_column('Region',     style='',     min_width=12)
    for s in sessions:
        t.add_row(str(s.session_id), s.language, s.status, s.region)
    c.print(t)
    c.print()
