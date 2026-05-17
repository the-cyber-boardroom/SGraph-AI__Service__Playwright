# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Cli__Bedrock__Agent
# Typer group for `sg aws bedrock agent *` commands.
# EXPERIMENTAL — requires AgentCore SDK or boto3 bedrock-agent.
# All mutating commands are gated by SG_AWS__BEDROCK__ALLOW_MUTATIONS=1.
# ═══════════════════════════════════════════════════════════════════════════════

import json
import uuid
from datetime                                                                    import date
from typing                                                                      import Optional

import typer
from rich.console                                                                import Console
from rich.table                                                                  import Table

from sg_compute.cli.base.Spec__CLI__Errors                                       import spec_cli_errors
from sgraph_ai_service_playwright__cli.aws._shared.Mutation__Gate               import require_mutation_gate
from sgraph_ai_service_playwright__cli.aws.bedrock.service.Bedrock__Agent__AWS__Client import Bedrock__Agent__AWS__Client
from sgraph_ai_service_playwright__cli.aws.bedrock.service.Bedrock__Capture__Writer    import Bedrock__Capture__Writer
from sgraph_ai_service_playwright__cli.aws.bedrock.service.Bedrock__Model__Resolver    import Bedrock__Model__Resolver

BEDROCK_GATE = 'SG_AWS__BEDROCK__ALLOW_MUTATIONS'

agent_app  = typer.Typer(name='agent',  help='Bedrock Agents (AgentCore) — EXPERIMENTAL.', no_args_is_help=True)
memory_app = typer.Typer(name='memory', help='Agent memory management.',                    no_args_is_help=True)
agent_app.add_typer(memory_app, name='memory')


def _client() -> Bedrock__Agent__AWS__Client:
    return Bedrock__Agent__AWS__Client()


# ── agent create ──────────────────────────────────────────────────────────────

@agent_app.command('create')
@require_mutation_gate(BEDROCK_GATE)
@spec_cli_errors
def agent_create(
    name        : str          = typer.Option(...,   '--name',   '-n', help='Agent name.'),
    model       : str          = typer.Option(...,   '--model',  '-m', help='Model alias or model ID (e.g. claude, haiku-4.5).'),
    tools       : str          = typer.Option('',   '--tools',        help='Comma-separated tool names: browser, code-interpreter.'),
    memory      : str          = typer.Option('none','--memory',      help='Memory scope: short, long, both, none.'),
    yes         : bool         = typer.Option(False, '--yes',   '-y', help='Skip confirmation prompt.'),
    json_output : bool         = typer.Option(False, '--json',        help='Output JSON.'),
):
    """Create an AgentCore agent. [EXPERIMENTAL]"""
    if not yes:
        typer.confirm(f'Create agent {name!r}?', abort=True)
    resolver = Bedrock__Model__Resolver()
    client   = _client()
    region   = client.current_region()
    try:
        model_id = resolver.resolve(model if model not in ('claude','nova','llama') else model, 'default', region)
    except ValueError:
        model_id = model                                                          # raw model ID passed directly
    agent  = client.create_agent(name, model_id, tools=tools, memory=memory)
    writer = Bedrock__Capture__Writer()
    path   = writer.write_agent_definition(name, {'agent_id'  : agent.agent_id  ,
                                                   'agent_arn' : str(agent.agent_arn),
                                                   'model_id'  : str(agent.model_id) ,
                                                   'status'    : agent.status        ,
                                                   'tools'     : tools               ,
                                                   'memory'    : memory              })
    if json_output:
        typer.echo(json.dumps(dict(agent_id   = agent.agent_id         ,
                                   agent_arn  = str(agent.agent_arn)   ,
                                   agent_name = agent.agent_name       ,
                                   model_id   = str(agent.model_id)    ,
                                   status     = agent.status           ,
                                   capture    = str(path)              ), indent=2))
        return
    c = Console(highlight=False)
    c.print(f'\n  Agent [bold]{name}[/] created  id={agent.agent_id}  capture={path}\n')


# ── agent list ────────────────────────────────────────────────────────────────

@agent_app.command('list')
@spec_cli_errors
def agent_list(json_output: bool = typer.Option(False, '--json', help='Output JSON.')):
    """List AgentCore agents. [EXPERIMENTAL]"""
    client = _client()
    agents = client.list_agents()
    if json_output:
        typer.echo(json.dumps([dict(agent_id  = a.agent_id        ,
                                    agent_name= a.agent_name      ,
                                    model_id  = str(a.model_id)   ,
                                    status    = a.status          ,
                                    region    = a.region          ) for a in agents], indent=2))
        return
    c = Console(highlight=False)
    c.print()
    t = Table(box=None, show_header=True, padding=(0, 2))
    t.add_column('ID',     style='dim',  min_width=12)
    t.add_column('Name',   style='bold', min_width=16)
    t.add_column('Model',  style='',     min_width=20)
    t.add_column('Status', style='cyan', min_width=10)
    t.add_column('Region', style='',     min_width=12)
    for a in agents:
        t.add_row(a.agent_id, a.agent_name, str(a.model_id), a.status, a.region)
    c.print(t)
    c.print()


# ── agent get ─────────────────────────────────────────────────────────────────

@agent_app.command('get')
@spec_cli_errors
def agent_get(agent_id  : str  = typer.Argument(..., help='AgentCore agent ID.'),
              json_output: bool = typer.Option(False, '--json', help='Output JSON.')):
    """Get details of one AgentCore agent. [EXPERIMENTAL]"""
    client = _client()
    agent  = client.get_agent(agent_id)
    if json_output:
        typer.echo(json.dumps(dict(agent_id  = agent.agent_id       ,
                                   agent_arn = str(agent.agent_arn) ,
                                   agent_name= agent.agent_name     ,
                                   model_id  = str(agent.model_id)  ,
                                   status    = agent.status         ,
                                   region    = agent.region         ), indent=2))
        return
    c = Console(highlight=False)
    c.print()
    t = Table(box=None, show_header=False, padding=(0, 2))
    t.add_column(style='bold', min_width=12, no_wrap=True)
    t.add_column()
    t.add_row('agent_id',  agent.agent_id)
    t.add_row('name',      agent.agent_name)
    t.add_row('arn',       str(agent.agent_arn))
    t.add_row('model_id',  str(agent.model_id))
    t.add_row('status',    agent.status)
    t.add_row('region',    agent.region)
    c.print(t)
    c.print()


# ── agent invoke ──────────────────────────────────────────────────────────────

@agent_app.command('invoke')
@require_mutation_gate(BEDROCK_GATE)
@spec_cli_errors
def agent_invoke(
    agent_id   : str          = typer.Argument(..., help='AgentCore agent ID.'),
    prompt     : str          = typer.Option(...,   '--prompt', '-p', help='Prompt text.'),
    session_id : Optional[str]= typer.Option(None, '--session',      help='Session ID (omit to create new).'),
    alias_id   : str          = typer.Option('TSTALIASID', '--alias',  help='Agent alias ID.'),
    yes        : bool         = typer.Option(False, '--yes', '-y',    help='Skip confirmation.'),
    json_output: bool         = typer.Option(False, '--json',         help='Output JSON.'),
):
    """Invoke an AgentCore agent. [EXPERIMENTAL]"""
    if not yes:
        typer.confirm(f'Invoke agent {agent_id!r}?', abort=True)
    sid    = session_id or uuid.uuid4().hex
    client = _client()
    result = client.invoke_agent(agent_id, alias_id, sid, prompt)
    writer = Bedrock__Capture__Writer()
    path   = writer.write_agent_session(agent_id, sid, dict(agent_id  = agent_id ,
                                                             session_id= sid      ,
                                                             prompt    = prompt   ,
                                                             result    = result   ))
    if json_output:
        typer.echo(json.dumps(dict(session_id  = sid          ,
                                   text        = result.get('text',''),
                                   capture     = str(path)    ), indent=2))
        return
    c = Console(highlight=False)
    c.print()
    c.print(result.get('text', ''))
    c.print(f'\n  session={sid}  capture={path}\n')


# ── agent stop ────────────────────────────────────────────────────────────────

@agent_app.command('stop')
@require_mutation_gate(BEDROCK_GATE)
@spec_cli_errors
def agent_stop(
    session_id : str  = typer.Argument(..., help='Session ID to stop.'),
    agent_id   : str  = typer.Option(...,   '--agent',  help='Agent ID owning this session.'),
    alias_id   : str  = typer.Option('TSTALIASID', '--alias', help='Agent alias ID.'),
    yes        : bool = typer.Option(False, '--yes', '-y', help='Skip confirmation.'),
):
    """Stop an AgentCore session. [EXPERIMENTAL]"""
    if not yes:
        typer.confirm(f'Stop session {session_id!r}?', abort=True)
    client = _client()
    client.stop_session(session_id, agent_id, alias_id)
    c = Console(highlight=False)
    c.print(f'\n  Session {session_id} stopped.\n')


# ── memory list ───────────────────────────────────────────────────────────────

@memory_app.command('list')
def memory_list(
    agent      : str  = typer.Option(..., '--agent', '-a', help='Agent name or ID.'),
    json_output: bool = typer.Option(False, '--json', help='Output JSON.'),
):
    """List memory snapshots for an agent. [EXPERIMENTAL]"""
    import glob, os
    writer  = Bedrock__Capture__Writer()
    root    = writer.capture_root() / 'agents' / agent / 'memory'
    entries = []
    if root.exists():
        for f in sorted(root.rglob('*.json')):
            entries.append({'path': str(f), 'scope': f.parent.name})
    if json_output:
        typer.echo(json.dumps(entries, indent=2))
        return
    c = Console(highlight=False)
    c.print()
    if not entries:
        c.print(f'  No memory snapshots found for agent [bold]{agent}[/].\n')
        return
    for e in entries:
        c.print(f'  scope={e["scope"]}  path={e["path"]}')
    c.print()


# ── memory clear ─────────────────────────────────────────────────────────────

@memory_app.command('clear')
@require_mutation_gate(BEDROCK_GATE)
def memory_clear(
    agent : str  = typer.Option(..., '--agent', '-a', help='Agent name or ID.'),
    scope : str  = typer.Option(..., '--scope',       help='Memory scope: short, long, both.'),
    yes   : bool = typer.Option(False, '--yes', '-y', help='Skip confirmation.'),
):
    """Clear agent memory snapshots locally. [EXPERIMENTAL]"""
    if not yes:
        typer.confirm(f'Clear {scope} memory for agent {agent!r}?', abort=True)
    import shutil
    writer = Bedrock__Capture__Writer()
    scopes = ['short', 'long'] if scope == 'both' else [scope]
    c      = Console(highlight=False)
    c.print()
    for sc in scopes:
        path = writer.capture_root() / 'agents' / agent / 'memory' / sc
        if path.exists():
            shutil.rmtree(path)
            c.print(f'  Cleared [bold]{sc}[/] memory for agent [bold]{agent}[/]  path={path}')
        else:
            c.print(f'  No {sc} memory found for agent {agent}.')
    c.print()
