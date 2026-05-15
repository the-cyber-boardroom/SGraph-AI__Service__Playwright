# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute — Cli__SG__Repl
# Interactive REPL for the `sg` CLI.
#
# Usage:  sg repl
#
# At the root prompt type a section name to enter it, then short verbs:
#   sg>         nodes          →  sg/nodes>
#   sg/nodes>   list           →  lists all nodes
#   sg/nodes>   info <name>    →  node details
#   sg/nodes>   delete <name>  →  delete one node
#   sg/nodes>   delete-all     →  delete all nodes
#   sg/nodes>   ..             →  back to root
#   sg>         q              →  exit
# ═══════════════════════════════════════════════════════════════════════════════

from rich.console                                                              import Console

console = Console(highlight=False)

DEFAULT_REGION = 'eu-west-2'

# ═══════════════════════════════════════════════════════════════════════════════
# helpers
# ═══════════════════════════════════════════════════════════════════════════════

def _platform():
    from sg_compute.platforms.ec2.EC2__Platform import EC2__Platform
    return EC2__Platform().setup()

# ═══════════════════════════════════════════════════════════════════════════════
# nodes commands
# ═══════════════════════════════════════════════════════════════════════════════

def _nodes_list(args):
    from sg_compute.cli.Renderers import render_node_list
    region  = args[0] if args else DEFAULT_REGION
    listing = _platform().list_nodes(region)
    render_node_list(listing, console)


def _nodes_info(args):
    if not args:
        console.print('[yellow]usage: info <node-id>[/yellow]')
        return
    from sg_compute.cli.Renderers import render_node_info
    node_id = args[0]
    region  = args[1] if len(args) > 1 else DEFAULT_REGION
    node    = _platform().get_node(node_id, region)
    if node is None:
        console.print(f'[red]Node {node_id!r} not found in {region}[/red]')
        return
    render_node_info(node, console)


def _nodes_delete(args):
    if not args:
        console.print('[yellow]usage: delete <node-id>[/yellow]')
        return
    node_id = args[0]
    region  = args[1] if len(args) > 1 else DEFAULT_REGION
    answer  = input(f'  Delete {node_id!r} in {region}? [y/N] ')
    if answer.strip().lower() != 'y':
        console.print('  Cancelled.')
        return
    result = _platform().delete_node(node_id, region)
    if result.deleted:
        console.print(f'  [green]Deleted: {node_id}[/green]')
    else:
        console.print(f'  [red]Failed:  {node_id}[/red]')


def _nodes_delete_all(args):
    region  = args[0] if args else DEFAULT_REGION
    listing = _platform().list_nodes(region)
    nodes   = listing.nodes
    if not nodes:
        console.print('  [dim]No live nodes found.[/dim]')
        return
    console.print(f'  Found [bold]{len(nodes)}[/bold] node(s) in {region}:')
    for n in nodes:
        console.print(f'    [cyan]{n.node_id}[/cyan]  [{n.spec_id}  {n.instance_type}]')
    answer = input(f'\n  Delete all {len(nodes)} node(s)? [y/N] ')
    if answer.strip().lower() != 'y':
        console.print('  Cancelled.')
        return
    platform = _platform()
    for n in nodes:
        result = platform.delete_node(n.node_id, region)
        if result.deleted:
            console.print(f'  [green]Deleted[/green]: {n.node_id}')
        else:
            console.print(f'  [red]FAILED [/red]: {n.node_id}')

# ═══════════════════════════════════════════════════════════════════════════════
# section registry
# ═══════════════════════════════════════════════════════════════════════════════

SECTIONS = {
    'nodes': {
        'list':       (_nodes_list,       'list [region]           list all compute nodes'),
        'info':       (_nodes_info,       'info <name> [region]    show node details'),
        'delete':     (_nodes_delete,     'delete <name> [region]  delete one node'),
        'delete-all': (_nodes_delete_all, 'delete-all [region]     delete all nodes'),
    },
}

# ═══════════════════════════════════════════════════════════════════════════════
# REPL loop
# ═══════════════════════════════════════════════════════════════════════════════

def _print_root(sg_app):
    try:
        sg_app(['--help'], standalone_mode=True)
    except SystemExit:
        pass


def _print_section(sg_app, section):
    try:
        sg_app([section, '--help'], standalone_mode=True)
    except SystemExit:
        pass


def run_repl(sg_app):
    try:
        import readline                                                         # arrow keys + history; stdlib on Linux/Mac
    except ImportError:
        pass

    console.print('\n  [bold]SG/Compute shell[/bold]  —  type a section to enter it, help to list all\n')

    section = None

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
                _print_root(sg_app)
            elif cmd in SECTIONS:
                section = cmd
                _print_section(sg_app, section)
            else:
                console.print(f'  [yellow]Unknown section {cmd!r}[/yellow]')
                _print_root(sg_app)
        else:
            if cmd in ('..', 'back'):
                section = None
                _print_root(sg_app)
            elif cmd in ('?', 'help', 'h'):
                _print_section(sg_app, section)
            elif cmd in SECTIONS[section]:
                fn, _ = SECTIONS[section][cmd]
                try:
                    fn(args)
                    console.print()
                except Exception as e:
                    console.print(f'  [red]Error: {e}[/red]\n')
            else:
                console.print(f'  [yellow]Unknown command {cmd!r}[/yellow]')
                _print_section(sg_app, section)
