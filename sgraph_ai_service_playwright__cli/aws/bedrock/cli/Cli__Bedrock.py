# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Cli__Bedrock
# Typer group for `sg aws bedrock *` commands.
# Sub-trees: check, setup, chat (read-only), agent (EXPERIMENTAL/gated),
#            tool (EXPERIMENTAL/gated).
# ═══════════════════════════════════════════════════════════════════════════════

import typer

from sgraph_ai_service_playwright__cli.aws.bedrock.cli.chat.Cli__Bedrock__Chat    import chat_app
from sgraph_ai_service_playwright__cli.aws.bedrock.cli.agent.Cli__Bedrock__Agent  import agent_app
from sgraph_ai_service_playwright__cli.aws.bedrock.cli.tool.Cli__Bedrock__Tool    import tool_app
from sgraph_ai_service_playwright__cli.aws.bedrock.cli.verbs.verb_check           import register_check
from sgraph_ai_service_playwright__cli.aws.bedrock.cli.verbs.verb_setup           import register_setup

app = typer.Typer(name='bedrock', help='AWS Bedrock — check, setup, chat, agents, tools.', no_args_is_help=True)

register_check(app)
register_setup(app)

app.add_typer(chat_app,  name='chat')
app.add_typer(agent_app, name='agent')
app.add_typer(tool_app,  name='tool')
