# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Verb__Bedrock__Chat__List_Models
# `sg aws bedrock chat list-models [--provider X] [--json]`
# Lists foundation models enabled in the current account/region.
# ═══════════════════════════════════════════════════════════════════════════════

import json
from typing                                                                      import Optional

import typer
from botocore.exceptions                                                         import ClientError
from rich.console                                                                import Console
from rich.table                                                                  import Table

from sgraph_ai_service_playwright__cli.aws.bedrock.service.Bedrock__Control__AWS__Client import Bedrock__Control__AWS__Client


def register_list_models(app: typer.Typer) -> None:

    @app.command('list-models')
    def list_models(provider   : Optional[str] = typer.Option(None,  '--provider', '-p', help='Filter by provider (e.g. Anthropic, Amazon, Meta).'),
                    json_output: bool          = typer.Option(False, '--json',           help='Output JSON instead of a table.')):
        """List Bedrock foundation models enabled in the current account and region."""
        client = Bedrock__Control__AWS__Client()
        try:
            models = client.list_models(provider_filter=provider)
        except ClientError as exc:
            code = exc.response.get('Error', {}).get('Code', 'Unknown')
            msg  = exc.response.get('Error', {}).get('Message', str(exc))
            c = Console(highlight=False)
            c.print()
            c.print(f'  [red][✗] {code}[/red]: {msg}')
            c.print( '      Run:  sg aws bedrock check')
            c.print( '      Or:   sg aws bedrock setup --print-policy')
            c.print()
            raise typer.Exit(1)
        except Exception as exc:
            c = Console(highlight=False)
            c.print(f'  [red]Error:[/red] {exc}')
            raise typer.Exit(1)
        region = client.current_region()

        if json_output:
            typer.echo(json.dumps([dict(model_id          = str(m.model_id)         ,
                                        model_name        = m.model_name             ,
                                        provider          = str(m.provider)          ,
                                        provider_name     = m.provider_name          ,
                                        input_modalities  = m.input_modalities       ,
                                        output_modalities = m.output_modalities      ,
                                        region            = m.region                 )
                                    for m in models], indent=2))
            return

        c = Console(highlight=False)
        c.print()
        c.print(f'  Bedrock models  ·  region={region}  ·  {len(models)} models')
        c.print()
        t = Table(box=None, show_header=True, padding=(0, 2))
        t.add_column('Model ID',          style='bold',  min_width=40)
        t.add_column('Provider',          style='cyan',  min_width=12)
        t.add_column('Input modalities',  style='',      min_width=14)
        t.add_column('Output modalities', style='',      min_width=14)
        for m in models:
            t.add_row(str(m.model_id), m.provider_name, m.input_modalities, m.output_modalities)
        c.print(t)
        c.print()
