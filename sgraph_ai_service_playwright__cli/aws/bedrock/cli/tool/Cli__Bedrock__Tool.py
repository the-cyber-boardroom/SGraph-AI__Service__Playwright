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

def _parse_viewport(spec: str) -> Optional[dict]:                                # `1920x1080` → {'width': 1920, 'height': 1080}
    if not spec:
        return None
    if 'x' not in spec.lower():
        raise typer.BadParameter(f'--viewport must be WIDTHxHEIGHT (e.g. 1920x1080), got {spec!r}.')
    w, _, h = spec.lower().partition('x')
    try:
        return {'width': int(w), 'height': int(h)}
    except ValueError:
        raise typer.BadParameter(f'--viewport must be WIDTHxHEIGHT integers, got {spec!r}.')


@browser_session_app.command('start')
@require_mutation_gate(BEDROCK_GATE)
@spec_cli_errors
def browser_session_start(
    viewport    : Optional[str] = typer.Option(None,  '--viewport',   '-v', help='Viewport size WIDTHxHEIGHT (e.g. 1920x1080). Determines what `screenshot` captures.'),
    timeout     : Optional[int] = typer.Option(None,  '--timeout',    '-t', help='Session timeout in seconds (default: AWS default).'),
    browser_id  : Optional[str] = typer.Option(None,  '--browser-id', '-b', help='Browser identifier (default: aws.browser.v1 — AWS-managed sandbox).'),
    region      : Optional[str] = typer.Option(None,  '--region',     '-r', help='AWS region (default: current region).'),
    yes         : bool          = typer.Option(False, '--yes',        '-y', help='Skip confirmation.'),
    json_output : bool          = typer.Option(False, '--json',             help='Output JSON.'),
):
    """Start a new AgentCore browser session. [EXPERIMENTAL]"""
    if not yes:
        typer.confirm('Start browser session?', default=True, abort=True)
    client       = _client()
    viewport_dict = _parse_viewport(viewport) if viewport else None
    session = client.browser_start(region=region, browser_identifier=browser_id,
                                   viewport=viewport_dict, session_timeout_seconds=timeout)
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
    browser_id : Optional[str] = typer.Option(None, '--browser-id', '-b', help='Browser identifier (default: aws.browser.v1).'),
    region     : Optional[str] = typer.Option(None, '--region',     '-r', help='AWS region.'),
    json_output: bool          = typer.Option(False,'--json',             help='Output JSON.'),
):
    """List active AgentCore browser sessions. [EXPERIMENTAL]"""
    client   = _client()
    sessions = client.browser_list(region=region, browser_identifier=browser_id)
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
    browser_id : Optional[str] = typer.Option(None,  '--browser-id', '-b', help='Browser identifier (default: aws.browser.v1).'),
    region     : Optional[str] = typer.Option(None,  '--region',     '-r', help='AWS region.'),
    yes        : bool          = typer.Option(False, '--yes',        '-y', help='Skip confirmation.'),
):
    """Print the CDP streamEndpoint for the session so an external Playwright
    client can navigate it. (Full in-process navigate is a follow-up — needs
    Playwright connected over CDP to the SigV4-signed stream URL.) [EXPERIMENTAL]"""
    if not yes:
        typer.confirm(f'Fetch stream endpoint for session {session_id!r} (to navigate to {url!r})?', default=True, abort=True)
    client = _client()
    resp   = client.browser_navigate(session_id, url, region=region, browser_identifier=browser_id)
    writer = Bedrock__Capture__Writer()
    writer.write_browser_action(session_id, {'action': 'navigate', 'url': url, 'response': resp})
    endpoints = resp.get('stream_endpoints', {}) or {}
    c = Console(highlight=False)
    c.print()
    c.print(f'  [yellow]Note:[/] in-process navigate not yet wired — returning CDP stream endpoints.')
    c.print(f'  Session:       {session_id}')
    c.print(f'  Requested URL: {url}')
    c.print()
    c.print(f'  [bold]automation:[/] {endpoints.get("automation", "")}')
    c.print(f'  [bold]live_view:[/]  {endpoints.get("live_view", "")}')
    c.print()
    c.print('  [dim]Auth: the stream URL needs SigV4 signing with your AWS credentials[/]')
    c.print('  [dim]      (botocore SigV4QueryAuth or a signed-WebSocket wrapper).[/]')
    c.print('  [dim]Then: chromium.connect_over_cdp(stream_url).contexts[0].pages[0].goto(url)[/]')
    c.print()


@browser_session_app.command('screenshot')
@require_mutation_gate(BEDROCK_GATE)
@spec_cli_errors
def browser_session_screenshot(
    session_id  : str          = typer.Argument(..., help='Browser session ID.'),
    output_file : Optional[str]= typer.Option(None, '--output',     '-o', help='Save screenshot to this path.'),
    browser_id  : Optional[str]= typer.Option(None, '--browser-id', '-b', help='Browser identifier (default: aws.browser.v1).'),
    region      : Optional[str]= typer.Option(None, '--region',     '-r', help='AWS region.'),
    yes         : bool         = typer.Option(False,'--yes',        '-y', help='Skip confirmation.'),
):
    """Take a full-screen PNG screenshot from a browser session.

    AWS `invoke_browser:screenshot` is intentionally minimal — PNG only,
    full-viewport capture (no clip/full-page/element/format options).
    Viewport size is set at session-start time via `start --viewport WxH`.

    For full-page (scroll-and-stitch), clipped regions, element captures,
    or non-PNG formats, you have to drive the session via CDP/Playwright
    over the streamEndpoint URL (see `navigate` for endpoint details).
    [EXPERIMENTAL]"""
    if not yes:
        typer.confirm(f'Screenshot session {session_id!r}?', default=True, abort=True)   # read-only op — default Y
    client     = _client()
    image_data = client.browser_screenshot(session_id, region=region, browser_identifier=browser_id)
    writer     = Bedrock__Capture__Writer()
    folder     = writer.browser_session_path(session_id)
    folder.mkdir(parents=True, exist_ok=True)
    if output_file:
        out = output_file
    else:
        import uuid
        out = str(folder / f'screenshot_{uuid.uuid4().hex[:8]}.png')
    with open(out, 'wb') as fh:                                                  # `browser_screenshot` raises on empty data; if we got here, write it
        fh.write(image_data)
    c = Console(highlight=False)
    c.print(f'\n  Screenshot saved: {out}  ({len(image_data):,} bytes)\n')


@browser_session_app.command('stop')
@require_mutation_gate(BEDROCK_GATE)
@spec_cli_errors
def browser_session_stop(
    session_id : str  = typer.Argument(..., help='Browser session ID.'),
    browser_id : Optional[str] = typer.Option(None,  '--browser-id', '-b', help='Browser identifier (default: aws.browser.v1).'),
    region     : Optional[str] = typer.Option(None,  '--region',     '-r', help='AWS region.'),
    yes        : bool          = typer.Option(False, '--yes',        '-y', help='Skip confirmation.'),
):
    """Stop a browser session. [EXPERIMENTAL]"""
    if not yes:
        typer.confirm(f'Stop browser session {session_id!r}?', abort=True)
    client = _client()
    client.browser_stop(session_id, region=region, browser_identifier=browser_id)
    c = Console(highlight=False)
    c.print(f'\n  Browser session {session_id} stopped.\n')


# ══════════════════════════════════════════════════════════════════════════════
# Code-interpreter sessions
# ══════════════════════════════════════════════════════════════════════════════

@code_session_app.command('start')
@require_mutation_gate(BEDROCK_GATE)
@spec_cli_errors
def code_session_start(
    language            : str          = typer.Option('python', '--language',            '-l', help='Language hint for local capture metadata (python, javascript, typescript); not sent to AWS.'),
    code_interpreter_id : Optional[str]= typer.Option(None,    '--code-interpreter-id', '-c', help='Code-interpreter identifier (default: aws.codeinterpreter.v1 — AWS-managed sandbox).'),
    region              : Optional[str]= typer.Option(None,    '--region',              '-r', help='AWS region.'),
    yes                 : bool         = typer.Option(False,   '--yes',                 '-y', help='Skip confirmation.'),
    json_output         : bool         = typer.Option(False,   '--json',                      help='Output JSON.'),
):
    """Start a code-interpreter session. [EXPERIMENTAL]"""
    if not yes:
        typer.confirm(f'Start code-interpreter session (language={language})?', default=True, abort=True)
    client  = _client()
    session = client.code_interpreter_start(language=language, region=region, code_interpreter_id=code_interpreter_id)
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
    session_id          : str          = typer.Argument(..., help='Code-interpreter session ID.'),
    code                : str          = typer.Option(...,   '--code',                '-c', help='Code to execute.'),
    language            : str          = typer.Option('python', '--language',         '-l', help='Language: python, javascript, typescript.'),
    code_interpreter_id : Optional[str]= typer.Option(None, '--code-interpreter-id',       help='Code-interpreter identifier (default: aws.codeinterpreter.v1).'),
    region              : Optional[str]= typer.Option(None, '--region',               '-r', help='AWS region.'),
    yes                 : bool         = typer.Option(False,'--yes',                  '-y', help='Skip confirmation.'),
    json_output         : bool         = typer.Option(False,'--json',                       help='Output JSON.'),
):
    """Run code in a code-interpreter session. [EXPERIMENTAL]"""
    if not yes:
        typer.confirm(f'Run code in session {session_id!r}?', default=True, abort=True)
    client = _client()
    result = client.code_interpreter_run(session_id, code, language=language, region=region, code_interpreter_id=code_interpreter_id)
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
    session_id          : str          = typer.Argument(..., help='Code-interpreter session ID.'),
    code_interpreter_id : Optional[str]= typer.Option(None, '--code-interpreter-id',       help='Code-interpreter identifier (default: aws.codeinterpreter.v1).'),
    region              : Optional[str]= typer.Option(None, '--region',               '-r', help='AWS region.'),
    yes                 : bool         = typer.Option(False,'--yes',                  '-y', help='Skip confirmation.'),
):
    """Stop a code-interpreter session. [EXPERIMENTAL]"""
    if not yes:
        typer.confirm(f'Stop code-interpreter session {session_id!r}?', abort=True)
    client = _client()
    client.code_interpreter_stop(session_id, region=region, code_interpreter_id=code_interpreter_id)
    c = Console(highlight=False)
    c.print(f'\n  Code-interpreter session {session_id} stopped.\n')


@code_session_app.command('list')
@spec_cli_errors
def code_session_list(
    code_interpreter_id : Optional[str]= typer.Option(None, '--code-interpreter-id',       help='Code-interpreter identifier (default: aws.codeinterpreter.v1).'),
    region              : Optional[str]= typer.Option(None, '--region',               '-r', help='AWS region.'),
    json_output         : bool         = typer.Option(False,'--json',                       help='Output JSON.'),
):
    """List code-interpreter sessions. [EXPERIMENTAL]"""
    client   = _client()
    sessions = client.code_interpreter_list(region=region, code_interpreter_id=code_interpreter_id)
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
