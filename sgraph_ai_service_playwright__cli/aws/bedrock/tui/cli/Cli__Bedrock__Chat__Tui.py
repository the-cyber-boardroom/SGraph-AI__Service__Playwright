# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — bedrock tui: Cli__Bedrock__Chat__Tui
# Backs `sg aws bedrock chat tui` (interactive Nova chat) + `chat tui-diagnose`.
# Textual is imported lazily inside the command so importing this module never
# requires it. When stdout is not a TTY (piped / CI) a single non-stream turn is run
# from stdin and printed with its cost — safe to pipe. The engine is built via a
# factory seam tests replace with an in-memory engine (no AWS, no mocks).
# ═══════════════════════════════════════════════════════════════════════════════

import os
import sys
from pathlib            import Path
from typing             import Optional

import typer

_engine_factory = None                                                            # tests assign () -> Bedrock__Chat__Engine

DEFAULT_REGION_FOR_TESTS = 'us-east-1'


def build_engine():
    if _engine_factory is not None:
        return _engine_factory()
    from sgraph_ai_service_playwright__cli.aws.bedrock.service.Bedrock__Runtime__AWS__Client import Bedrock__Runtime__AWS__Client
    from sgraph_ai_service_playwright__cli.aws.bedrock.service.Bedrock__Stream__Adapter      import Bedrock__Stream__Adapter
    from sgraph_ai_service_playwright__cli.aws.bedrock.tui.source.Bedrock__Chat__AWS_Source   import Bedrock__Chat__AWS_Source
    from sgraph_ai_service_playwright__cli.aws.bedrock.tui.service.Bedrock__Chat__Engine       import Bedrock__Chat__Engine
    source = Bedrock__Chat__AWS_Source(runtime=Bedrock__Runtime__AWS__Client(), adapter=Bedrock__Stream__Adapter())
    return Bedrock__Chat__Engine(source=source)


def resolve_region(engine) -> str:
    if _engine_factory is not None:
        return DEFAULT_REGION_FOR_TESTS
    return engine.source.runtime.current_region()


def load_context(context_file: Optional[str]):
    if not context_file:
        return None
    from sgraph_ai_service_playwright__cli.aws.bedrock.tui.schemas.Schema__Bedrock__Chat__Context import Schema__Bedrock__Chat__Context
    body  = Path(context_file).read_text(encoding='utf-8')
    label = f'{Path(context_file).name} ({len(body)} chars)'
    return Schema__Bedrock__Chat__Context(label=label, body=body)


def run_one_shot(engine, region: str, model: str, context, prompt: str) -> None:  # no-TTY fallback: one turn, printed with cost
    session = engine.new_session(region=region, model_alias=model, context=context)
    turn    = engine.send_turn(session, prompt)
    print(session.messages[-1].text)
    print(f'\n[in {turn.input_tokens} · out {turn.output_tokens} · '
          f'${turn.cost_usd:.6f} · {turn.latency_ms}ms]')


def build_tools(tools_spec: str) -> dict:                                         # '--tools core.vfs:read' → the screen's tool kwargs
    if not tools_spec:
        return {}
    from sgraph_ai_service_playwright__cli.tui.tool_api.core.vfs.Vfs__Tui_Api__Provider import Vfs__Tui_Api__Provider  # lazy (memory_fs, 3.12)
    from sgraph_ai_service_playwright__cli.aws.bedrock.tui.tui_api.Bedrock__Tool_Config__Builder import Bedrock__Tool_Config__Builder
    from sgraph_ai_service_playwright__cli.tui.tool_api.service.Tui_Api__Execution_Center        import Tui_Api__Execution_Center
    from sgraph_ai_service_playwright__cli.tui.tool_api.service.Tui_Api__Loadout__Assembler      import Tui_Api__Loadout__Assembler
    from sgraph_ai_service_playwright__cli.tui.tool_api.service.Tui_Api__Privilege__Resolver     import Tui_Api__Privilege__Resolver
    from sgraph_ai_service_playwright__cli.tui.tool_api.service.Tui_Api__Registry                import Tui_Api__Registry

    registry  = Tui_Api__Registry().register(Vfs__Tui_Api__Provider())            # the chat enables the VFS core tool
    resolver  = Tui_Api__Privilege__Resolver()
    center    = Tui_Api__Execution_Center(registry=registry, resolver=resolver)
    assembler = Tui_Api__Loadout__Assembler()
    loadout   = assembler.from_tools(tools_spec)
    granted   = assembler.granted_actions(loadout, registry, resolver)
    tool_config, name_map = Bedrock__Tool_Config__Builder().build(granted)
    return {'registry': registry, 'center': center, 'tool_config': tool_config, 'name_map': name_map}


def run_tui(model: str = 'default', region: str = '', context_file: Optional[str] = None, tools: str = '') -> None:
    engine  = build_engine()
    region  = region or resolve_region(engine)
    context = load_context(context_file)

    if not sys.stdout.isatty():                                                   # piped / CI → one-shot from stdin (no tools)
        prompt = sys.stdin.read().strip() if not sys.stdin.isatty() else ''
        if prompt:
            run_one_shot(engine, region, model, context, prompt)
        else:
            print('sg aws bedrock chat tui needs a TTY; pipe a prompt on stdin for a one-shot turn.')
        return

    from sgraph_ai_service_playwright__cli.aws.bedrock.tui.screens.Bedrock__Chat__Screen import Bedrock__Chat__Screen
    Bedrock__Chat__Screen(engine, region=region, model_alias=model, context=context, **build_tools(tools)).run()


def run_diagnose() -> None:
    term = os.environ.get('TERM', '') or '(unset)'
    lang = os.environ.get('LANG', '') or '(unset)'
    print('sg aws bedrock chat tui — terminal diagnose')
    print(f'  TERM      : {term}')
    print(f'  LANG      : {lang}')
    print(f'  isatty    : {sys.stdout.isatty()}')
    print('  unicode   : █▓▒░ ▁▂▃▄▅▆▇█ ╭─╮ │ ╰─╯ ● ◐ ○ ✓ ✗ ⟳ ▸')
    print('  truecolor : \x1b[38;2;255;100;0mTRUECOLOR\x1b[0m   (orange ⇒ 24-bit ok)')


def chat_registry():                                                              # the chat as a TUI API provider (decision #8)
    from sgraph_ai_service_playwright__cli.aws.bedrock.tui.tui_api.Bedrock__Chat__Tui_Api__Provider import Bedrock__Chat__Tui_Api__Provider
    from sgraph_ai_service_playwright__cli.tui.tool_api.service.Tui_Api__Registry                   import Tui_Api__Registry
    return Tui_Api__Registry().register(Bedrock__Chat__Tui_Api__Provider(engine=build_engine()))


def register_tui(parent_app: typer.Typer) -> None:
    from sgraph_ai_service_playwright__cli.tui.tool_api.cli.Cli__Tui_Api import make_tui_api_app

    tui_app = typer.Typer(name='tui', help='Interactive Nova chat + its TUI API (`tui api`).',
                          invoke_without_command=True)

    @tui_app.callback(invoke_without_command=True)
    def launch(ctx          : typer.Context,
               model        : str           = typer.Option('default', '--model', '-m', help='Nova alias: default(lite) | lite | micro | pro | premier.'),
               region       : str           = typer.Option('',        '--region',      help='AWS region (defaults to the resolved region).'),
               context_file : Optional[str] = typer.Option(None,      '--context',     help='Seed the chat with a file as context to talk about.'),
               tools        : str           = typer.Option('',        '--tools',       help="Enable tools, e.g. 'core.vfs:read' — switches to the agentic (non-streaming) loop.")):
        """Launch the chat TUI (bare `tui`); sub-commands `api` / `diagnose` below."""
        if ctx.invoked_subcommand is None:
            run_tui(model=model, region=region, context_file=context_file, tools=tools)

    @tui_app.command('diagnose')
    def diagnose():
        """Print terminal capability checks for the chat TUI."""
        run_diagnose()

    tui_app.add_typer(make_tui_api_app(chat_registry()), name='api')              # `sg aws bedrock chat tui api …`
    parent_app.add_typer(tui_app, name='tui')
