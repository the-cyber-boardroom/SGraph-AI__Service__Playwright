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


@app.command(name='dashboard', help='All screens in one app with tabbed navigation (1..6 / ←→ to switch).')
def dashboard(parent: str = typer.Option('', '--parent', '-p', help='Local edge zone (default edge.sg-labs.local)'),
              aws_parent: str = typer.Option('', '--aws-parent', help='AWS edge zone (default edge.sg-labs.app)')):
    local_source = _source('local', parent)
    if not sys.stdout.isatty():                                                      # piped / CI → static card of the local edge
        _render_static(local_source)
        return
    aws_source = _source('aws', aws_parent)
    from sg_compute_specs.sg_edge.tui.screens.SG_Edge__TUI__App import SG_Edge__TUI__App
    SG_Edge__TUI__App(local_source=local_source, aws_source=aws_source, docker_source=_docker_source()).run()


@app.command(name='diagnose', help='Print terminal capability checks (run before reporting broken TUI output).')
def diagnose():
    import os
    import shutil
    import subprocess
    term   = os.environ.get('TERM', '')   or '(unset)'
    lang   = os.environ.get('LANG', '')   or '(unset)'
    lc_all = os.environ.get('LC_ALL', '') or '(unset)'
    colors = '(tput unavailable)'
    if shutil.which('tput'):
        try:
            colors = subprocess.run(['tput', 'colors'], capture_output=True, text=True).stdout.strip() or colors
        except Exception:
            pass
    print('SG/Edge TUI — terminal diagnostics')
    print(f'  TERM        = {term}')
    print(f'  LANG        = {lang}')
    print(f'  LC_ALL      = {lc_all}')
    print(f'  tput colors = {colors}   (expect 256)')
    print('  unicode test : █▓▒░ ▁▂▃▄▅▆▇█ ╭─╮ │ ╰─╯ ● ◐ ○ ✓ ✗ ⚠ ▸ ≈ ▲ ▼')
    print('  truecolor    : \x1b[38;2;255;100;0mTRUECOLOR\x1b[0m   (renders orange ⇒ 24-bit ok)')
    print('  if blocks/boxes show as ? or tofu, the locale or font is wrong — see the TUI guide.')


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


_docker_factory = None                                                               # tests assign a callable → SG_Edge__TUI__Docker__Source


def _docker_source():
    if _docker_factory is not None:
        return _docker_factory()
    from sg_compute.host_plane.pods.service.Pod__Runtime__Docker          import Pod__Runtime__Docker
    from sg_compute_specs.sg_edge.tui.source.SG_Edge__TUI__Docker__Source import SG_Edge__TUI__Docker__Source
    return SG_Edge__TUI__Docker__Source(runtime=Pod__Runtime__Docker())


@app.command(name='deployment', help='Screen 1 — Deployment Reality: what is deployed, at a glance.')
def deployment(target: str = typer.Option('local', '--target', '-t', help='Data source: local | aws'),
               parent: str = typer.Option('',      '--parent', '-p', help='Edge parent zone (defaults per target)')):
    source = _source(target, parent)
    if not sys.stdout.isatty():                                                      # piped / CI / no real terminal → static card
        _render_static(source)
        return
    from sg_compute_specs.sg_edge.tui.screens.SG_Edge__TUI__Screen__Deployment import SG_Edge__TUI__Screen__Deployment
    SG_Edge__TUI__Screen__Deployment(source=source, docker_source=_docker_source()).run()


@app.command(name='docker', help='Local Docker — what containers are running on this host (docker ps).')
def docker():
    src = _docker_source()
    if not sys.stdout.isatty():                                                      # piped / CI → plain text list
        from sg_compute_specs.sg_edge.tui.screens.SG_Edge__TUI__Docker__Render import docker_plain
        print(docker_plain(src.containers(), src.available()))
        return
    from sg_compute_specs.sg_edge.tui.screens.SG_Edge__TUI__Screen__Docker import SG_Edge__TUI__Screen__Docker
    SG_Edge__TUI__Screen__Docker(docker_source=src).run()


@app.command(name='slugs', help='Slug inventory in a Textual DataTable (cursor/scroll/click; Enter → detail).')
def slugs(target: str = typer.Option('local', '--target', '-t', help='Data source: local | aws'),
          parent: str = typer.Option('',      '--parent', '-p', help='Edge parent zone (defaults per target)')):
    source = _source(target, parent)
    if not sys.stdout.isatty():                                                      # piped / CI → plain rows
        from sg_compute_specs.sg_edge.tui.screens.widgets.SG_Edge__TUI__Table import type_safe_table
        cols, rows = type_safe_table(source.snapshot().slugs, ['slug', 'state', 'backend_ip', 'backend_port'])
        print('  '.join(cols))
        for row in rows:
            print('  '.join(row))
        return
    from sg_compute_specs.sg_edge.tui.screens.SG_Edge__TUI__Screen__Slugs import SG_Edge__TUI__Screen__Slugs
    table = SG_Edge__TUI__Screen__Slugs(source=source)
    table.run()
    if table.opened_slug:                                                            # row selected → open Slug detail
        from sg_compute_specs.sg_edge.tui.screens.SG_Edge__TUI__Screen__Slug_Detail import SG_Edge__TUI__Screen__Slug_Detail
        SG_Edge__TUI__Screen__Slug_Detail(source=source, slug=table.opened_slug).run()


@app.command(name='control', help='Control Center — action-capable cockpit (register/request/setup/teardown).')
def control(target: str = typer.Option('local', '--target', '-t', help='Data source: local | aws'),
            parent: str = typer.Option('',      '--parent', '-p', help='Edge parent zone (defaults per target)')):
    source = _source(target, parent)
    if not sys.stdout.isatty():                                                      # piped / CI → read-only card + native-command footer (rule 3: no mutation)
        from sg_compute_specs.sg_edge.tui.service.SG_Edge__TUI__Card import SG_Edge__TUI__Card
        print(SG_Edge__TUI__Card().render(source.snapshot()))
        print('\nnative commands (the screen calls the same backend — never TUI-only):')
        for verb, cmd in (('register', 'sg edge local register <slug>'),
                          ('unregister', 'sg edge local unregister <slug>'),
                          ('request',  'sg edge local request <slug>'),
                          ('setup',    'sg edge local setup'),
                          ('teardown', 'sg edge local teardown')):
            print(f'  {verb:<11} {cmd}')
        return
    from sg_compute_specs.sg_edge.tui.screens.SG_Edge__TUI__Screen__Control_Center import SG_Edge__TUI__Screen__Control_Center
    SG_Edge__TUI__Screen__Control_Center(source=source).run()


@app.command(name='topology', help='Screen 2 — Topology: the layered flow (browser → wildcard → fleet → slugs).')
def topology(target: str = typer.Option('local', '--target', '-t', help='Data source: local | aws'),
             parent: str = typer.Option('',      '--parent', '-p', help='Edge parent zone (defaults per target)')):
    source = _source(target, parent)
    if not sys.stdout.isatty():                                                      # piped / CI / no real terminal → static card (itself a layered topology)
        _render_static(source)
        return
    from sg_compute_specs.sg_edge.tui.screens.SG_Edge__TUI__Screen__Topology import SG_Edge__TUI__Screen__Topology
    topo = SG_Edge__TUI__Screen__Topology(source=source)
    topo.run()
    if topo.opened_slug:                                                             # Enter drilled in → open the Slug-detail screen for that slug
        from sg_compute_specs.sg_edge.tui.screens.SG_Edge__TUI__Screen__Slug_Detail import SG_Edge__TUI__Screen__Slug_Detail
        SG_Edge__TUI__Screen__Slug_Detail(source=source, slug=topo.opened_slug).run()


@app.command(name='slug', help='Screen 4 — Slug detail: deep-dive one slug (↑/↓ to switch).')
def slug(name  : str = typer.Argument('', help='Slug to focus (default: first registered)'),
         target: str = typer.Option('local', '--target', '-t', help='Data source: local | aws'),
         parent: str = typer.Option('',      '--parent', '-p', help='Edge parent zone (defaults per target)')):
    source = _source(target, parent)
    if not sys.stdout.isatty():                                                      # piped / CI / no real terminal → plain text detail
        from sg_compute_specs.sg_edge.tui.screens.SG_Edge__TUI__Slug_Detail__Render import slug_detail_plain
        snap   = source.snapshot()
        target_slug = name or (snap.slugs[0].slug if snap.slugs else '')
        print(slug_detail_plain(snap, target_slug))
        return
    from sg_compute_specs.sg_edge.tui.screens.SG_Edge__TUI__Screen__Slug_Detail import SG_Edge__TUI__Screen__Slug_Detail
    SG_Edge__TUI__Screen__Slug_Detail(source=source, slug=name).run()


@app.command(name='events', help='Screen 5 — Live Activity: streamed state-transition events + honest sparklines.')
def events(target: str = typer.Option('local', '--target', '-t', help='Data source: local | aws'),
           parent: str = typer.Option('',      '--parent', '-p', help='Edge parent zone (defaults per target)')):
    source = _source(target, parent)
    if not sys.stdout.isatty():                                                      # piped / CI → a live feed is meaningless statically; show the current-state card
        _render_static(source)
        return
    from sg_compute_specs.sg_edge.tui.screens.SG_Edge__TUI__Screen__Events import SG_Edge__TUI__Screen__Events
    SG_Edge__TUI__Screen__Events(source=source).run()


_compare_sources_factory = None                                                      # tests assign a callable(local_parent, aws_parent) → (local_source, aws_source)


def _compare_sources(local_parent : str, aws_parent : str):
    if _compare_sources_factory is not None:
        return _compare_sources_factory(local_parent, aws_parent)
    return _source('local', local_parent), _source('aws', aws_parent)


@app.command(name='compare', help='Screen 3 — Local vs Edge: what differs between the local and AWS edge.')
def compare(local_parent: str = typer.Option('', '--local-parent', help='Local edge zone (default edge.sg-labs.local)'),
            aws_parent  : str = typer.Option('', '--aws-parent',   help='AWS edge zone (default edge.sg-labs.app)')):
    local_source, aws_source = _compare_sources(local_parent, aws_parent)
    if not sys.stdout.isatty():                                                      # piped / CI / no real terminal → plain text diff
        from sg_compute_specs.sg_edge.tui.screens.SG_Edge__TUI__Compare__Render import compare_plain
        print(compare_plain(local_source.snapshot(), aws_source.snapshot()))
        return
    from sg_compute_specs.sg_edge.tui.screens.SG_Edge__TUI__Screen__Compare import SG_Edge__TUI__Screen__Compare
    SG_Edge__TUI__Screen__Compare(local_source=local_source, aws_source=aws_source).run()
