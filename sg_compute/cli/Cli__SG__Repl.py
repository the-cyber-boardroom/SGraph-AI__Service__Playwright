# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute — Cli__SG__Repl
# Interactive REPL for `sg repl`. Thin navigation wrapper over sg_app.
# All dispatch delegates back to sg_app — no parallel logic, no hardcoded
# section registry. Navigates arbitrary depth by tracking a path list.
#
# Pseudo-commands (handled before dispatch):
#   as <role>   — pin role for the REPL session (prompt shows [role] suffix)
#   as          — clear pinned role
#   q / quit / exit / Ctrl-D — exit
#   Ctrl-C      — if a role is pinned, clear it; otherwise exit
# ═══════════════════════════════════════════════════════════════════════════════

import typer.main
from rich.console                                                                   import Console
from osbot_utils.type_safe.Type_Safe                                                import Type_Safe

from sgraph_ai_service_playwright__cli.credentials.service.Sg__Aws__Context         import Sg__Aws__Context

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


def _children(sg_app, path):                                                    # visible sub-commands at current path
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


def _resolve(sg_app, base_path, words):
    """Prefix-resolve words through the click tree starting from base_path.

    Returns (full_path, trailing_args).
    Returns (None, candidates) when a step is ambiguous.
    Stops early when a word starts with '-' or no child matches (rest become args).
    """
    current = list(base_path)
    for i, word in enumerate(words):
        if word.startswith('-') or not _is_group(sg_app, current):             # option flag or leaf — rest are args
            return current, list(words[i:])
        available = _children(sg_app, current) - ({'repl'} if not current else set())
        hits      = _match(word, available)
        if len(hits) == 1:
            current.append(hits[0])
        elif len(hits) > 1:
            return None, hits                                                   # ambiguous
        else:
            return current, list(words[i:])                                    # no match — rest are args
    return current, []

# ═══════════════════════════════════════════════════════════════════════════════
# Cli__SG__Repl — Type_Safe wrapper exposing prompt + as-handler for testability
# ═══════════════════════════════════════════════════════════════════════════════

class Cli__SG__Repl(Type_Safe):
    context        : Sg__Aws__Context
    path           : list = None
    exit_words     : list = None

    def setup(self) -> 'Cli__SG__Repl':
        if self.exit_words is None:
            self.exit_words = ['exit', 'quit', 'q']
        if self.path is None:
            self.path = []
        return self

    def _prompt(self) -> str:
        base        = 'sg/' + '/'.join(self.path) if self.path else 'sg'
        role_suffix = f' [{self.context.current_role}]' if self.context.has_role() else ''
        return f'{base}{role_suffix}> '

    def _handle_as(self, tokens) -> bool:                                       # True = handled; don't dispatch
        if not tokens or tokens[0] != 'as':
            return False
        if len(tokens) == 1:
            self.context.clear_role()
            console.print('  [dim]role cleared[/dim]')
        else:
            role_name = tokens[1]
            self.context.set_role(role_name)
            console.print(f'  [dim]switched to role: {role_name}[/dim]')
        return True

# ═══════════════════════════════════════════════════════════════════════════════
# REPL loop
# ═══════════════════════════════════════════════════════════════════════════════

def run_repl(sg_app=None):
    if sg_app is None:                                                          # `sg-repl` console-script entry point
        from sg_compute.cli.Cli__SG import app as _sg_app
        sg_app = _sg_app

    try:
        import readline                                                         # arrow keys + history; stdlib on Linux/Mac
    except ImportError:
        pass

    repl      = Cli__SG__Repl(context=Sg__Aws__Context()).setup()
    role_line = f'role: {repl.context.current_role}' if repl.context.has_role() else 'role: (none)'

    console.print('\n  [bold]SG/Compute shell[/bold]  —  type a section to enter it, [bold]help[/bold] to list all')
    console.print(f'  [dim]{role_line}[/dim]   [dim]as <role> to pin, Ctrl-C to clear[/dim]\n')

    while True:
        try:
            line = input(repl._prompt()).strip()
        except KeyboardInterrupt:
            console.print()
            if repl.context.has_role():
                repl.context.clear_role()
                console.print('  [dim]role cleared (Ctrl-C)[/dim]')
                continue
            break
        except EOFError:
            console.print()
            break

        if not line:
            continue

        parts = line.split()
        cmd   = parts[0]

        if cmd in repl.exit_words:
            break

        if cmd in ('..', 'back'):
            if repl.path:
                repl.path.pop()
            _invoke(sg_app, (repl.path + ['--help']) if repl.path else ['--help'])
            continue

        if cmd in ('?', 'help', 'h'):
            _invoke(sg_app, repl.path + ['--help'])
            continue

        if repl._handle_as(parts):                                              # as <role> pseudo-command
            continue

        resolved, trailing = _resolve(sg_app, repl.path, parts)

        if resolved is None:
            console.print(f'  [dim]{" ".join(trailing)}[/dim]')                # ambiguous — show candidates
        elif len(parts) == 1 and not trailing and _is_group(sg_app, resolved) and resolved != repl.path:
            repl.path[:] = resolved                                             # single word → group: navigate
            _invoke(sg_app, repl.path + ['--help'])
        else:
            _invoke(sg_app, resolved + trailing)                               # execute without navigating
