# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute — Cli__SG__Repl
# Interactive REPL for `sg repl`. Thin navigation wrapper over sg_app.
# All dispatch delegates back to sg_app — no parallel logic, no hardcoded
# section registry. Navigates arbitrary depth by tracking a path list.
# ═══════════════════════════════════════════════════════════════════════════════

import typer.main
from rich.console import Console

console = Console(highlight=False)

# ═══════════════════════════════════════════════════════════════════════════════
# click-tree helpers
# ═══════════════════════════════════════════════════════════════════════════════

def _click_node(sg_app, path):                                                  # walk the click command tree along path
    node = typer.main.get_command(sg_app)
    for segment in path:
        if not hasattr(node, 'commands'):
            return None
        node = node.commands.get(segment)
        if node is None:
            return None
    return node


def _children(sg_app, path):                                                    # visible sub-commands at the current path
    node = _click_node(sg_app, path)
    if node and hasattr(node, 'commands'):
        return {name for name, cmd in node.commands.items() if not cmd.hidden}
    return set()


def _is_group(sg_app, path):                                                    # true when the node at path has navigable sub-commands
    node = _click_node(sg_app, path)
    return bool(node and hasattr(node, 'commands') and node.commands)


def _match(prefix, options):                                                    # sorted prefix filter
    return sorted(o for o in options if o.startswith(prefix))


def _invoke(sg_app, args):
    try:
        sg_app(args, standalone_mode=True)
    except SystemExit:
        pass

# ═══════════════════════════════════════════════════════════════════════════════
# REPL loop
# ═══════════════════════════════════════════════════════════════════════════════

def run_repl(sg_app):
    try:
        import readline                                                         # arrow keys + history; stdlib on Linux/Mac
    except ImportError:
        pass

    console.print('\n  [bold]SG/Compute shell[/bold]  —  type a section to enter it, [bold]help[/bold] to list all\n')

    path = []

    while True:
        try:
            prompt = 'sg/' + '/'.join(path) + '> ' if path else 'sg> '
            line   = input(prompt).strip()
        except (EOFError, KeyboardInterrupt):
            console.print()
            break

        if not line:
            continue

        parts = line.split()
        cmd   = parts[0]
        args  = parts[1:]

        if cmd in ('q', 'quit', 'exit'):
            break

        if cmd in ('..', 'back'):
            if path:
                path.pop()
            _invoke(sg_app, (path + ['--help']) if path else ['--help'])
            continue

        if cmd in ('?', 'help', 'h'):
            _invoke(sg_app, path + ['--help'])
            continue

        available = _children(sg_app, path) - ({'repl'} if not path else set())
        hits      = _match(cmd, available)

        if len(hits) == 1:
            hit = hits[0]
            if _is_group(sg_app, path + [hit]):
                path.append(hit)
                _invoke(sg_app, path + ['--help'])
            else:
                _invoke(sg_app, path + [hit] + args)
        elif hits:
            console.print(f'  [dim]{" ".join(hits)}[/dim]')
        else:
            _invoke(sg_app, path + [cmd] + args)                               # pass through verbatim; typer prints a clear error
