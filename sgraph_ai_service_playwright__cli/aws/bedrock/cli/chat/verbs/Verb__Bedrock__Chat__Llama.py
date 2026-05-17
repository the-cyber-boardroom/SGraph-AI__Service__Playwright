# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Verb__Bedrock__Chat__Llama
# `sg aws bedrock chat llama --prompt TEXT [--model 3.1|4-scout|4-maverick]
#                             [--input FILE] [--json] [--cost-override N]`
# ═══════════════════════════════════════════════════════════════════════════════

from typing                                                                      import Optional

import typer

from sgraph_ai_service_playwright__cli.aws.bedrock.cli.chat.verbs.Verb__Bedrock__Chat__Helpers import load_prompt, run_chat


def register_llama(app: typer.Typer) -> None:

    @app.command('llama')
    def chat_llama(
        prompt       : str          = typer.Option(...,   '--prompt', '-p',   help='Prompt text.'),
        model        : str          = typer.Option('default', '--model', '-m',help='Model alias: 3.1, 4-scout (default), 4-maverick.'),
        input_file   : Optional[str]= typer.Option(None, '--input',          help='Path to a file whose content is appended to the prompt.'),
        json_output  : bool         = typer.Option(False,'--json',            help='Output JSON instead of a Rich panel.'),
        cost_override: Optional[float]= typer.Option(None,'--cost-override', help='Override the per-call cost cap (USD).'),
    ):
        """Chat with a Meta Llama model via Bedrock Converse."""
        prompt_text = load_prompt(prompt, input_file)
        run_chat('llama', model, prompt_text, False, json_output, cost_override)
