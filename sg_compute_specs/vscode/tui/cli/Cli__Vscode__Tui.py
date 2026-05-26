# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — vscode tui: Cli__Vscode__Tui
# `sg vscode tui <screen>` — the GUI over the `sg vscode` CLI. Textual is imported
# lazily inside the command body so registering this sub-app never requires textual;
# the rest of `sg vscode` works whether or not textual is installed. When stdout is
# not a TTY (piped / CI) the screen falls back to a static ASCII card + a pointer to
# the native commands — it never mutates (separation guide rule 3).
# ═══════════════════════════════════════════════════════════════════════════════

import sys

import typer

app = typer.Typer(name='tui', help='VS Code stacks TUI (Textual).', no_args_is_help=True)

_source_factory = None                                                               # tests assign a callable(region) → data source


@app.callback()
def main():                                                                          # force group behaviour — keeps `tui <screen>` valid with one screen today
    pass


def _source(region: str):
    if _source_factory is not None:
        return _source_factory(region)
    from sg_compute_specs.vscode.tui.source.Vscode__TUI__Data_Source import Vscode__TUI__Data_Source
    src = Vscode__TUI__Data_Source(region=region) if region else Vscode__TUI__Data_Source()
    return src.setup()


def _tui_api_registry():                                                             # vscode stacks as a TUI API (house pattern: explicit registration)
    from sg_compute_specs.vscode.tui.source.Vscode__TUI__Data_Source   import Vscode__TUI__Data_Source
    from sg_compute_specs.vscode.tui.tui_api.Vscode__Tui_Api__Provider  import Vscode__Tui_Api__Provider
    from sgraph_ai_service_playwright__cli.tui.tool_api.service.Tui_Api__Registry import Tui_Api__Registry
    return Tui_Api__Registry().register(Vscode__Tui_Api__Provider(source=Vscode__TUI__Data_Source().setup()))


from sgraph_ai_service_playwright__cli.tui.tool_api.cli.Cli__Tui_Api import make_tui_api_app  # noqa: E402 — wire `sg vscode tui api …` (no textual)
app.add_typer(make_tui_api_app(_tui_api_registry()), name='api')


@app.command(name='stacks', help='Read-only dashboard of vscode stacks (r refresh · d debug · q quit).')
def stacks(region: str = typer.Option('', '--region', '-r', help='AWS region (default eu-west-2).')):
    source = _source(region)
    if not sys.stdout.isatty():                                                      # piped / CI / no real terminal → static card, then exit
        from sg_compute_specs.vscode.tui.service.Vscode__TUI__Card import Vscode__TUI__Card
        print(Vscode__TUI__Card().render(source.snapshot()))
        return
    from sg_compute_specs.vscode.tui.screens.Vscode__TUI__Screen__Stacks import Vscode__TUI__Screen__Stacks
    Vscode__TUI__Screen__Stacks(source=source).run()
