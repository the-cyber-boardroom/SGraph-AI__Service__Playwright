# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — aws/s3/tui_api: Cli__S3__Tui_Api
# Attaches `sg aws s3 tui api …` to the s3 CLI. s3's Textual UI is `browse` (no `tui`
# group existed), so this introduces a `tui` group whose only member today is `api`.
# The provider is registered explicitly (the house pattern — no command-tree walking).
# ═══════════════════════════════════════════════════════════════════════════════

import typer

from sgraph_ai_service_playwright__cli.aws.s3.tui_api.S3__Tui_Api__Provider   import S3__Tui_Api__Provider
from sgraph_ai_service_playwright__cli.tui.tool_api.cli.Cli__Tui_Api          import make_tui_api_app
from sgraph_ai_service_playwright__cli.tui.tool_api.service.Tui_Api__Registry import Tui_Api__Registry


def s3_registry() -> Tui_Api__Registry:
    return Tui_Api__Registry().register(S3__Tui_Api__Provider())


def register_s3_tui_api(parent_app: typer.Typer) -> None:
    tui_app = typer.Typer(name='tui', help='S3 TUI surfaces (the TUI API lives under `tui api`).',
                          no_args_is_help=True)
    tui_app.add_typer(make_tui_api_app(s3_registry()), name='api')
    parent_app.add_typer(tui_app, name='tui')
