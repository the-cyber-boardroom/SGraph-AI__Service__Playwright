# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute — Cli__SG__Repl
# Interactive REPL for `sg repl`. Thin navigation wrapper over sg_app.
# All dispatch delegates back to sg_app — no parallel logic, no hardcoded
# section registry. Works for every current and future sg sub-command.
# ═══════════════════════════════════════════════════════════════════════════════

import typer.main
from rich.console import Console

console = Console(highlight=False)

# ═══════════════════════════════════════════════════════════════════════════════
# helpers
# ═══════════════════════════════════════════════════════════════════════════════

def _invoke(sg_app, args):
    try:
        sg_app(args, standalone_mode=True)
    except SystemExit:
        pass


def _sections(sg_app):                                                          # discover from the live app — stays in sync automatically
    click_app = typer.main.get_command(sg_app)
    return {name for name, cmd in click_app.commands.items()
            if not cmd.hidden and name != 'repl'}

# ═══════════════════════════════════════════════════════════════════════════════
# REPL loop
# ═══════════════════════════════════════════════════════════════════════════════

def run_repl(sg_app):
    try:
        import readline                                                         # arrow keys + history; stdlib on Linux/Mac
    except ImportError:
        pass

    console.print('\n  [bold]SG/Compute shell[/bold]  —  type a section to enter it, [bold]help[/bold] to list all\n')

    sections = _sections(sg_app)
    section  = None

    while True:
        try:
            prompt = f'sg/{section}> ' if section else 'sg> '
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

        if section is None:
            if cmd in ('?', 'help', 'h'):
                _invoke(sg_app, ['--help'])
            elif cmd in sections:
                section = cmd
                _invoke(sg_app, [section, '--help'])
            else:
                console.print(f'  [yellow]Unknown: {cmd!r}[/yellow]')
                _invoke(sg_app, ['--help'])
        else:
            if cmd in ('..', 'back'):
                section = None
                _invoke(sg_app, ['--help'])
            elif cmd in ('?', 'help', 'h'):
                _invoke(sg_app, [section, '--help'])
            else:
                _invoke(sg_app, [section, cmd] + args)
