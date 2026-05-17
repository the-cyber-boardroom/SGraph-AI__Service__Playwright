# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Cli__Bedrock
# Typer group for `sg aws bedrock *` commands. Bodies owned by Slice E.
# ═══════════════════════════════════════════════════════════════════════════════

import typer

app   = typer.Typer(name='bedrock', help='AWS Bedrock — chat, agents, tools.', no_args_is_help=True)
chat  = typer.Typer(name='chat',    help='Bedrock chat completions.',           no_args_is_help=True)
agent = typer.Typer(name='agent',   help='Bedrock Agents (AgentCore).',         no_args_is_help=True)
tool  = typer.Typer(name='tool',    help='Bedrock inline tools (browser, code-interpreter).', no_args_is_help=True)

app.add_typer(chat,  name='chat')
app.add_typer(agent, name='agent')
app.add_typer(tool,  name='tool')
