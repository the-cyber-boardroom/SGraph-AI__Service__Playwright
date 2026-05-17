# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Verb__Bedrock__Chat__Llama
# `sg aws bedrock chat llama [PROMPT] [--prompt|-p TEXT] [--model 3.1|4-scout|4-maverick]
#                             [--input FILE] [--json] [--cost-override N]`
# Positional PROMPT and --prompt/-p are equivalent; --prompt wins if both given.
# ═══════════════════════════════════════════════════════════════════════════════

from typing                                                                      import Optional

import typer

from sgraph_ai_service_playwright__cli.aws.bedrock.cli.chat.verbs.Verb__Bedrock__Chat__Helpers import resolve_prompt, run_chat


def register_llama(app: typer.Typer) -> None:

    @app.command('llama')
    def chat_llama(
        prompt_arg   : Optional[str]   = typer.Argument(None,                       help='Prompt text (alternative to --prompt).'),
        prompt       : Optional[str]   = typer.Option(None,  '--prompt', '-p',     help='Prompt text.'),
        model        : str             = typer.Option('default', '--model', '-m',  help='Model alias: 3.1, 4-scout (default), 4-maverick.'),
        input_file   : Optional[str]   = typer.Option(None, '--input',             help='Path to a file whose content is appended to the prompt.'),
        json_output  : bool            = typer.Option(False, '--json',             help='Output JSON instead of a Rich panel.'),
        cost_override: Optional[float] = typer.Option(None, '--cost-override',     help='Override the per-call cost cap (USD).'),
    ):
        """Chat with a Meta Llama model via Bedrock Converse."""
        prompt_text = resolve_prompt(prompt_arg, prompt, input_file)
        run_chat('llama', model, prompt_text, False, json_output, cost_override)
