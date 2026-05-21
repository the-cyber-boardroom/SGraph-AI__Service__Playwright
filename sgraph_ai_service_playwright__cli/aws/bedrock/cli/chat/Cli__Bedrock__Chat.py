# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Cli__Bedrock__Chat
# Typer group for `sg aws bedrock chat *` commands.
# All commands delegate to service classes — no boto3 here.
# ═══════════════════════════════════════════════════════════════════════════════

import typer

from sgraph_ai_service_playwright__cli.aws.bedrock.cli.chat.verbs.Verb__Bedrock__Chat__List_Models import register_list_models
from sgraph_ai_service_playwright__cli.aws.bedrock.cli.chat.verbs.Verb__Bedrock__Chat__Claude      import register_claude
from sgraph_ai_service_playwright__cli.aws.bedrock.cli.chat.verbs.Verb__Bedrock__Chat__Nova        import register_nova
from sgraph_ai_service_playwright__cli.aws.bedrock.cli.chat.verbs.Verb__Bedrock__Chat__Llama       import register_llama
from sgraph_ai_service_playwright__cli.aws.bedrock.cli.chat.verbs.Verb__Bedrock__Chat__Any         import register_any
from sgraph_ai_service_playwright__cli.aws.bedrock.tui.cli.Cli__Bedrock__Chat__Tui                 import register_tui

chat_app = typer.Typer(name='chat', help='Bedrock chat completions.', no_args_is_help=True)

register_list_models(chat_app)
register_claude(chat_app)
register_nova(chat_app)
register_llama(chat_app)
register_any(chat_app)
register_tui(chat_app)
