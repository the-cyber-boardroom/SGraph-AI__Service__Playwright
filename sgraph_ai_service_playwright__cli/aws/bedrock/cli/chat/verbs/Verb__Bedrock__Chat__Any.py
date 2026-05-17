# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Verb__Bedrock__Chat__Any
# `sg aws bedrock chat any [PROMPT] [--prompt|-p TEXT] --provider PROVIDER
#                           [--model M] [--input FILE] [--json] [--cost-override N]`
# Generic escape hatch — works with any provider in the alias table.
# Positional PROMPT and --prompt/-p are equivalent; --prompt wins if both given.
# ═══════════════════════════════════════════════════════════════════════════════

from typing                                                                      import List, Optional

import typer

from sgraph_ai_service_playwright__cli.aws.bedrock.cli.chat.verbs.Verb__Bedrock__Chat__Helpers import resolve_prompt, run_chat


def register_any(app: typer.Typer) -> None:

    @app.command('any')
    def chat_any(
        prompt_arg   : Optional[List[str]] = typer.Argument(None,                   help='Prompt text — quoted or as multiple words (alternative to --prompt).'),
        prompt       : Optional[str]   = typer.Option(None,  '--prompt',   '-p',   help='Prompt text.'),
        provider     : str             = typer.Option(...,   '--provider',         help='Provider key: claude, nova, llama, openai, other.'),
        model        : str             = typer.Option('default', '--model', '-m',  help='Model alias. Omit for the provider default.'),
        input_file   : Optional[str]   = typer.Option(None, '--input',             help='Path to a file whose content is appended to the prompt.'),
        json_output  : bool            = typer.Option(False, '--json',             help='Output JSON instead of a Rich panel.'),
        cost_override: Optional[float] = typer.Option(None, '--cost-override',     help='Override the per-call cost cap (USD).'),
    ):
        """Chat with any Bedrock provider using its alias name."""
        prompt_text = resolve_prompt(prompt_arg, prompt, input_file)
        run_chat(provider, model, prompt_text, False, json_output, cost_override)
