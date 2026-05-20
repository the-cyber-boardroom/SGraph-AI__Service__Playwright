# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — sg_edge tui: Cli__SG_Edge__Tui
# `sg edge tui <screen>` — the exploratory TUI screens. Textual is imported lazily
# inside each command so merely registering this sub-app (in Cli__SG_Edge) never
# requires textual — the rest of `sg edge` works whether or not textual is present.
#
#   deployment   Screen 1 — Deployment Reality (what is deployed, at a glance)
#
# --target local|aws picks the data source. When stdout is not a TTY (piped, CI,
# no real terminal) the screen falls back to a static ASCII card and exits — so the
# command is safe to pipe and degrades gracefully over a broken chain.
# ═══════════════════════════════════════════════════════════════════════════════

import sys

import typer

app = typer.Typer(name='tui', help='SG/Edge exploratory TUI screens (Textual).', no_args_is_help=True)

_source_factory = None                                                               # tests assign a callable(target, parent) → Data_Source


@app.callback()
def main():                                                                          # force group behaviour — keeps `tui <screen>` valid even with one command today
    pass


def _source(target : str, parent : str):
    if _source_factory is not None:
        return _source_factory(target, parent)
    if str(target) == 'aws':
        from sg_compute_specs.sg_edge.service.SG_Edge__DNS__Helper        import SG_Edge__DNS__Helper
        from sg_compute_specs.sg_edge.tui.source.SG_Edge__TUI__AWS_Source import SG_Edge__TUI__AWS_Source
        kwargs = {'dns': SG_Edge__DNS__Helper()}
        if parent:
            kwargs['parent_zone'] = parent
        return SG_Edge__TUI__AWS_Source(**kwargs)
    from sg_compute_specs.sg_edge.local.Local__Edge__Stack                  import Local__Edge__Stack
    from sg_compute_specs.sg_edge.tui.source.SG_Edge__TUI__Local_Source     import SG_Edge__TUI__Local_Source
    stack_kwargs = {}
    if parent:
        stack_kwargs['parent'] = parent
    return SG_Edge__TUI__Local_Source(stack=Local__Edge__Stack(**stack_kwargs))


def _render_static(source) -> None:                                                  # no-TTY fallback: a static ASCII card, then exit
    from sg_compute_specs.sg_edge.tui.service.SG_Edge__TUI__Card import SG_Edge__TUI__Card
    print(SG_Edge__TUI__Card().render(source.snapshot()))


@app.command(name='deployment', help='Screen 1 — Deployment Reality: what is deployed, at a glance.')
def deployment(target: str = typer.Option('local', '--target', '-t', help='Data source: local | aws'),
               parent: str = typer.Option('',      '--parent', '-p', help='Edge parent zone (defaults per target)')):
    source = _source(target, parent)
    if not sys.stdout.isatty():                                                      # piped / CI / no real terminal → static card
        _render_static(source)
        return
    from sg_compute_specs.sg_edge.tui.screens.SG_Edge__TUI__Screen__Deployment import SG_Edge__TUI__Screen__Deployment
    SG_Edge__TUI__Screen__Deployment(source=source).run()
