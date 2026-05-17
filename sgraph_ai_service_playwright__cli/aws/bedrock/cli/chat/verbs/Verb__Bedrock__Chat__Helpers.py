# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Verb__Bedrock__Chat__Helpers
# Shared helpers used by all chat verb registrations.
# ═══════════════════════════════════════════════════════════════════════════════

import json
import uuid
from datetime                                                                    import date
from pathlib                                                                     import Path
from typing                                                                      import Optional

import typer
from rich.console                                                                import Console
from rich.panel                                                                  import Panel

from sgraph_ai_service_playwright__cli.aws.bedrock.service.Bedrock__Runtime__AWS__Client import Bedrock__Runtime__AWS__Client
from sgraph_ai_service_playwright__cli.aws.bedrock.service.Bedrock__Model__Resolver      import Bedrock__Model__Resolver
from sgraph_ai_service_playwright__cli.aws.bedrock.service.Bedrock__Capture__Writer      import Bedrock__Capture__Writer
from sgraph_ai_service_playwright__cli.aws.bedrock.service.Bedrock__Cost__Calculator     import Bedrock__Cost__Calculator
from sgraph_ai_service_playwright__cli.aws.bedrock.service.Bedrock__Stream__Adapter      import Bedrock__Stream__Adapter
from sgraph_ai_service_playwright__cli.aws.bedrock.schemas.Schema__Bedrock__Chat__Response import Schema__Bedrock__Chat__Response
from sgraph_ai_service_playwright__cli.aws.bedrock.primitives.Safe_Str__Bedrock__Model_Id  import Safe_Str__Bedrock__Model_Id

_console = Console(stderr=True)


def load_prompt(prompt: str, input_file: Optional[str]) -> str:                  # Combine --prompt and optional --input file content
    text = prompt or ''
    if input_file:
        try:
            text = text + '\n\n' + Path(input_file).read_text(encoding='utf-8')
        except Exception as exc:
            _console.print(f'[red]Cannot read input file {input_file}: {exc}[/]')
            raise typer.Exit(1)
    return text.strip()


def run_chat(provider: str, alias: str, prompt_text: str,
             stream: bool, json_output: bool,
             cost_override: Optional[float],
             runtime: Bedrock__Runtime__AWS__Client    = None,
             resolver: Bedrock__Model__Resolver         = None,
             writer: Bedrock__Capture__Writer           = None,
             calc: Bedrock__Cost__Calculator            = None) -> Schema__Bedrock__Chat__Response:
    """Execute one chat call; write capture; return schema."""                   # inline
    if runtime  is None: runtime  = Bedrock__Runtime__AWS__Client()
    if resolver is None: resolver = Bedrock__Model__Resolver()
    if writer   is None: writer   = Bedrock__Capture__Writer()
    if calc     is None: calc     = Bedrock__Cost__Calculator()

    region   = runtime.current_region()
    model_id = resolver.resolve(provider, alias, region)

    # Cost pre-flight
    try:
        calc.check_cost_cap(model_id, len(prompt_text), cost_override)
    except ValueError as exc:
        _console.print(Panel(str(exc), title='[red]Cost cap exceeded[/]', border_style='red'))
        raise typer.Exit(1)

    # Execute call
    if stream:
        stream_events = list(runtime.converse_stream(model_id, prompt_text, region=region))
        adapter       = Bedrock__Stream__Adapter()
        response_text = adapter.collect(stream_events)
        input_tokens  = 0
        output_tokens = 0
        if json_output:
            for line in adapter.to_ndjson(iter(stream_events)):
                typer.echo(line)
    else:
        resp          = runtime.converse(model_id, prompt_text, region=region)
        response_text = runtime.extract_text(resp)
        input_tokens, output_tokens = runtime.extract_usage(resp)

    cost  = calc.estimate(model_id, input_tokens, output_tokens)
    run_id= uuid.uuid4().hex
    iso_day = str(date.today())

    # Capture
    payload = dict(model_id      = model_id      ,
                   region        = region         ,
                   prompt        = prompt_text    ,
                   response_text = response_text  ,
                   input_tokens  = input_tokens   ,
                   output_tokens = output_tokens  ,
                   cost_usd      = cost           ,
                   run_id        = run_id         ,
                   iso_day       = iso_day        )
    captured = writer.write_chat(iso_day, run_id, payload)

    try:
        safe_mid = Safe_Str__Bedrock__Model_Id(model_id)
    except ValueError:
        safe_mid = Safe_Str__Bedrock__Model_Id('')

    schema = Schema__Bedrock__Chat__Response(
        model_id      = safe_mid               ,
        region        = region                 ,
        prompt        = prompt_text            ,
        response_text = response_text          ,
        input_tokens  = input_tokens           ,
        output_tokens = output_tokens          ,
        cost_usd      = cost                   ,
        run_id        = run_id                 ,
        iso_day       = iso_day                ,
        capture_path  = str(captured)          ,
    )

    if not stream:
        if json_output:
            typer.echo(json.dumps(dict(model_id      = str(schema.model_id)  ,
                                       region        = schema.region          ,
                                       response_text = schema.response_text   ,
                                       input_tokens  = schema.input_tokens    ,
                                       output_tokens = schema.output_tokens   ,
                                       cost_usd      = schema.cost_usd        ,
                                       capture_path  = schema.capture_path    ), indent=2))
        else:
            c = Console(highlight=False)
            c.print()
            c.print(Panel(response_text, title=f'[bold]{model_id}[/]  [{region}]', border_style='cyan'))
            c.print(f'  tokens in={input_tokens} out={output_tokens}  est.cost=${cost:.6f}  capture={captured}')
            c.print()

    return schema
