# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Verb__Bedrock__Chat__Claude
# `sg aws bedrock chat claude [PROMPT] [--prompt|-p TEXT] [--model ALIAS]
#                              [--input FILE] [--stream] [--json]
#                              [--cost-override N]`
# Positional PROMPT and --prompt/-p are equivalent; --prompt wins if both given.
# ═══════════════════════════════════════════════════════════════════════════════

from typing                                                                      import List, Optional

import typer

from sgraph_ai_service_playwright__cli.aws.bedrock.cli.chat.verbs.Verb__Bedrock__Chat__Helpers import resolve_prompt, run_chat


def register_claude(app: typer.Typer) -> None:

    @app.command('claude')
    def chat_claude(
        prompt_arg   : Optional[List[str]] = typer.Argument(None,                   help='Prompt text — quoted or as multiple words (alternative to --prompt).'),
        prompt       : Optional[str]   = typer.Option(None,  '--prompt', '-p',     help='Prompt text.'),
        model        : str             = typer.Option('default', '--model', '-m',  help='Model alias: opus-4.7, sonnet-4.6, haiku-4.5, etc. Default: haiku-3.5.'),
        input_file   : Optional[str]   = typer.Option(None, '--input',             help='Path to a file whose content is appended to the prompt.'),
        stream       : bool            = typer.Option(False, '--stream',           help='Stream output via NDJSON (requires --json).'),
        json_output  : bool            = typer.Option(False, '--json',             help='Output JSON instead of a Rich panel.'),
        cost_override: Optional[float] = typer.Option(None, '--cost-override',     help='Override the per-call cost cap (USD).'),
    ):
        """Chat with an Anthropic Claude model via Bedrock Converse."""
        prompt_text = resolve_prompt(prompt_arg, prompt, input_file)
        run_chat('claude', model, prompt_text, stream, json_output, cost_override)
