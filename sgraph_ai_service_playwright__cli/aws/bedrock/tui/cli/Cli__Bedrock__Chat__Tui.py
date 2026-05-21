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


def run_tui(model: str = 'default', region: str = '', context_file: Optional[str] = None) -> None:
    engine  = build_engine()
    region  = region or resolve_region(engine)
    context = load_context(context_file)

    if not sys.stdout.isatty():                                                   # piped / CI → one-shot from stdin
        prompt = sys.stdin.read().strip() if not sys.stdin.isatty() else ''
        if prompt:
            run_one_shot(engine, region, model, context, prompt)
        else:
            print('sg aws bedrock chat tui needs a TTY; pipe a prompt on stdin for a one-shot turn.')
        return

    from sgraph_ai_service_playwright__cli.aws.bedrock.tui.screens.Bedrock__Chat__Screen import Bedrock__Chat__Screen
    Bedrock__Chat__Screen(engine, region=region, model_alias=model, context=context).run()


def run_diagnose() -> None:
    term = os.environ.get('TERM', '') or '(unset)'
    lang = os.environ.get('LANG', '') or '(unset)'
    print('sg aws bedrock chat tui — terminal diagnose')
    print(f'  TERM      : {term}')
    print(f'  LANG      : {lang}')
    print(f'  isatty    : {sys.stdout.isatty()}')
    print('  unicode   : █▓▒░ ▁▂▃▄▅▆▇█ ╭─╮ │ ╰─╯ ● ◐ ○ ✓ ✗ ⟳ ▸')
    print('  truecolor : \x1b[38;2;255;100;0mTRUECOLOR\x1b[0m   (orange ⇒ 24-bit ok)')


def register_tui(app: typer.Typer) -> None:

    @app.command('tui')
    def tui(model        : str           = typer.Option('default', '--model', '-m', help='Nova alias: default(lite) | lite | micro | pro | premier.'),
            region       : str           = typer.Option('',        '--region',      help='AWS region (defaults to the resolved region).'),
            context_file : Optional[str] = typer.Option(None,      '--context',     help='Seed the chat with a file as context to talk about.')):
        """Interactive Nova chat with per-turn + per-session cost tracking."""
        run_tui(model=model, region=region, context_file=context_file)

    @app.command('tui-diagnose')
    def tui_diagnose():
        """Print terminal capability checks for the chat TUI."""
        run_diagnose()
