# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — verb_setup
# `sg aws bedrock setup [--region TEXT] [--open-console] [--print-policy]`
# Guides the user through IAM policy + model-access setup. Read-only.
# ═══════════════════════════════════════════════════════════════════════════════

import webbrowser
from typing                                                                      import Optional
from pathlib                                                                     import Path

import typer
from rich.console                                                                import Console
from rich.panel                                                                  import Panel

from sgraph_ai_service_playwright__cli.aws.bedrock.service.Bedrock__Setup__Renderer import Bedrock__Setup__Renderer
from sg_compute.cli.base.Spec__CLI__Errors                                  import spec_cli_errors


def register_setup(app: typer.Typer) -> None:

    @app.command('setup')
    @spec_cli_errors
    def bedrock_setup(region       : Optional[str]  = typer.Option(None , '--region'        , help='Override active role region.'),
                      open_console : bool           = typer.Option(False, '--open-console'   , help='Open model-access console in browser.'),
                      print_policy : bool           = typer.Option(False, '--print-policy'   , help='Print minimal IAM policy JSON to stdout.'),
                      output       : Optional[Path] = typer.Option(None , '--output'         , help='Write IAM policy JSON to FILE.')):
        """Guided Bedrock enablement — IAM policy, model access, verify."""
        renderer         = Bedrock__Setup__Renderer()
        effective_region = region or 'us-east-1'

        if print_policy or output:
            policy_json = renderer.iam_policy_json(effective_region)
            if output:
                output.write_text(policy_json + '\n')
                typer.echo(f'Policy written to {output}')
            else:
                typer.echo(policy_json)
            return

        if open_console:
            url = renderer.model_access_deeplink(effective_region)
            typer.echo(f'Opening: {url}')
            if not webbrowser.open(url):
                typer.echo(f'Could not open browser. URL: {url}')
            return

        c     = Console(highlight=False)
        steps = renderer.render_steps(region=effective_region)
        c.print()
        c.print(f'  Bedrock setup  ·  region={effective_region}')
        c.print()
        for step in steps:
            header = f'Step {step.step_no} of {len(steps)}  ·  {step.title}'
            c.print(Panel(step.body, title=header, expand=False))
            if step.deeplink:
                c.print(f'  [dim]Deeplink: {step.deeplink}[/dim]')
            c.print()
