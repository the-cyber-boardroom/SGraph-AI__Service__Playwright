# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Verb__Bedrock__Chat__Nova
# `sg aws bedrock chat nova [PROMPT] [--prompt|-p TEXT] [--model lite|pro|micro|premier]
#                            [--input FILE] [--json] [--cost-override N]`
# Positional PROMPT and --prompt/-p are equivalent; --prompt wins if both given.
# ═══════════════════════════════════════════════════════════════════════════════

from typing                                                                      import List, Optional

import typer

from sg_compute.cli.base.Spec__CLI__Errors                                       import spec_cli_errors

from sgraph_ai_service_playwright__cli.aws.bedrock.cli.chat.verbs.Verb__Bedrock__Chat__Helpers import resolve_prompt, run_chat


def register_nova(app: typer.Typer) -> None:

    @app.command('nova')
    @spec_cli_errors
    def chat_nova(
        prompt_arg   : Optional[List[str]] = typer.Argument(None,                   help='Prompt text — quoted or as multiple words (alternative to --prompt).'),
        prompt       : Optional[str]   = typer.Option(None,  '--prompt', '-p',     help='Prompt text.'),
        model        : str             = typer.Option('default', '--model', '-m',  help='Model alias: lite (default), pro, micro, premier.'),
        input_file   : Optional[str]   = typer.Option(None, '--input',             help='Path to a file whose content is appended to the prompt.'),
        json_output  : bool            = typer.Option(False, '--json',             help='Output JSON instead of a Rich panel.'),
        cost_override: Optional[float] = typer.Option(None, '--cost-override',     help='Override the per-call cost cap (USD).'),
    ):
        """Chat with an Amazon Nova model via Bedrock Converse."""
        prompt_text = resolve_prompt(prompt_arg, prompt, input_file)
        run_chat('nova', model, prompt_text, False, json_output, cost_override)
