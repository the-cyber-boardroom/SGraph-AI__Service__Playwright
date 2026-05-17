# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Verb__Bedrock__Chat__Any
# `sg aws bedrock chat any --prompt TEXT --provider PROVIDER [--model M]
#                           [--input FILE] [--json] [--cost-override N]`
# Generic escape hatch — works with any provider in the alias table.
# ═══════════════════════════════════════════════════════════════════════════════

from typing                                                                      import Optional

import typer

from sgraph_ai_service_playwright__cli.aws.bedrock.cli.chat.verbs.Verb__Bedrock__Chat__Helpers import load_prompt, run_chat


def register_any(app: typer.Typer) -> None:

    @app.command('any')
    def chat_any(
        prompt       : str          = typer.Option(...,   '--prompt',   '-p', help='Prompt text.'),
        provider     : str          = typer.Option(...,   '--provider',       help='Provider key: claude, nova, llama, openai, other.'),
        model        : str          = typer.Option('default', '--model', '-m',help='Model alias. Omit for the provider default.'),
        input_file   : Optional[str]= typer.Option(None, '--input',          help='Path to a file whose content is appended to the prompt.'),
        json_output  : bool         = typer.Option(False,'--json',            help='Output JSON instead of a Rich panel.'),
        cost_override: Optional[float]= typer.Option(None,'--cost-override', help='Override the per-call cost cap (USD).'),
    ):
        """Chat with any Bedrock provider using its alias name."""
        prompt_text = load_prompt(prompt, input_file)
        run_chat(provider, model, prompt_text, False, json_output, cost_override)
