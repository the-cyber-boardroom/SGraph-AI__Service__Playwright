# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Verb__Bedrock__Chat__Claude
# `sg aws bedrock chat claude --prompt TEXT [--model opus-4.7|sonnet-4.6|haiku-4.5]
#                              [--input FILE] [--stream] [--json]
#                              [--cost-override N] [--no-capture]`
# ═══════════════════════════════════════════════════════════════════════════════

from typing                                                                      import Optional

import typer

from sgraph_ai_service_playwright__cli.aws.bedrock.cli.chat.verbs.Verb__Bedrock__Chat__Helpers import load_prompt, run_chat


def register_claude(app: typer.Typer) -> None:

    @app.command('claude')
    def chat_claude(
        prompt       : str          = typer.Option(...,   '--prompt', '-p',   help='Prompt text.'),
        model        : str          = typer.Option('default', '--model', '-m',help='Model alias: opus-4.7, sonnet-4.6, haiku-4.5, etc. Default: haiku-3.5.'),
        input_file   : Optional[str]= typer.Option(None, '--input',          help='Path to a file whose content is appended to the prompt.'),
        stream       : bool         = typer.Option(False,'--stream',          help='Stream output via NDJSON (requires --json).'),
        json_output  : bool         = typer.Option(False,'--json',            help='Output JSON instead of a Rich panel.'),
        cost_override: Optional[float]= typer.Option(None,'--cost-override', help='Override the per-call cost cap (USD).'),
    ):
        """Chat with an Anthropic Claude model via Bedrock Converse."""
        prompt_text = load_prompt(prompt, input_file)
        run_chat('claude', model, prompt_text, stream, json_output, cost_override)
