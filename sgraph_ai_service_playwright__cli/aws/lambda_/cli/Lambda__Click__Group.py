# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Lambda__Click__Group
# Two-level dynamic Click group hierarchy for `sg aws lambda`.
#
# Lambda__App__Group : children = 'list' + all function names (5-min cached)
# Lambda__Function__Group : children = verb commands for one function
#
# Both subclass click.Group directly so REPL navigation works:
# the REPL walks node.commands.items() to find children — having real Command
# objects registered there is what makes prefix navigation work.
#
# CLI:  `sg aws lambda waker info`
#   1. Lambda__App__Group.get_command('waker') → resolves → Lambda__Function__Group
#   2. Lambda__Function__Group.get_command('info') → cmd_info
#   3. cmd_info reads ctx.obj['function_name']
#
# REPL: `aws lambda` → `sg-c` (prefix nav) → `info`
#   Same path — REPL calls list_commands() to enumerate children then
#   resolves the prefix.
# ═══════════════════════════════════════════════════════════════════════════════

import click
from rich.console import Console

from sgraph_ai_service_playwright__cli.aws.lambda_.service.Lambda__Name__Resolver   import Lambda__Name__Resolver
from sgraph_ai_service_playwright__cli.aws.lambda_.cli.verbs.verb_info               import cmd_info
from sgraph_ai_service_playwright__cli.aws.lambda_.cli.verbs.verb_details            import cmd_details
from sgraph_ai_service_playwright__cli.aws.lambda_.cli.verbs.verb_config             import cmd_config
from sgraph_ai_service_playwright__cli.aws.lambda_.cli.verbs.verb_logs               import cmd_logs
from sgraph_ai_service_playwright__cli.aws.lambda_.cli.verbs.verb_invocations        import cmd_invocations
from sgraph_ai_service_playwright__cli.aws.lambda_.cli.verbs.verb_invoke             import cmd_invoke
from sgraph_ai_service_playwright__cli.aws.lambda_.cli.verbs.verb_deploy             import cmd_deploy
from sgraph_ai_service_playwright__cli.aws.lambda_.cli.verbs.verb_delete             import cmd_delete
from sgraph_ai_service_playwright__cli.aws.lambda_.cli.verbs.verb_url                import cmd_url
from sgraph_ai_service_playwright__cli.aws.lambda_.cli.verbs.verb_tags               import cmd_tags
from sgraph_ai_service_playwright__cli.aws.lambda_.cli.verbs.verb_versions           import cmd_versions
from sgraph_ai_service_playwright__cli.aws.lambda_.cli.verbs.verb_aliases            import cmd_aliases

console = Console()

# ── verb registry ─────────────────────────────────────────────────────────────

VERB_REGISTRY = {
    'info'        : cmd_info,
    'details'     : cmd_details,
    'config'      : cmd_config,
    'logs'        : cmd_logs,
    'invocations' : cmd_invocations,
    'invoke'      : cmd_invoke,
    'deploy'      : cmd_deploy,
    'delete'      : cmd_delete,
    'url'         : cmd_url,
    'tags'        : cmd_tags,
    'versions'    : cmd_versions,
    'aliases'     : cmd_aliases,
}

VERB_ORDER = ['info', 'details', 'config', 'logs', 'invocations',
              'invoke', 'deploy', 'delete', 'url', 'tags', 'versions', 'aliases']


# ── per-function group ────────────────────────────────────────────────────────

class Lambda__Function__Group(click.Group):                                       # one function; children = verb commands

    def __init__(self, function_name: str, **attrs):
        super().__init__(name=function_name, **attrs)
        self._function_name = function_name
        for verb, cmd in VERB_REGISTRY.items():                                   # register all verbs as real children
            self.add_command(cmd, verb)

    def list_commands(self, ctx):
        return VERB_ORDER

    def get_command(self, ctx, name):
        return VERB_REGISTRY.get(name)

    def invoke(self, ctx):
        ctx.ensure_object(dict)
        ctx.obj['function_name'] = self._function_name
        super().invoke(ctx)

    def make_context(self, info_name, args, parent=None, **extra):
        ctx = super().make_context(info_name, args, parent=parent, **extra)
        ctx.ensure_object(dict)
        ctx.obj['function_name'] = self._function_name
        return ctx


# ── top-level group ───────────────────────────────────────────────────────────

class Lambda__App__Group(click.Group):                                            # top-level; children = 'list' + function names

    def __init__(self, resolver: Lambda__Name__Resolver = None, **attrs):
        help_text = (
            'Lambda function management.\n\n'
            'Usage:\n'
            '  sg aws lambda list               — list all functions\n'
            '  sg aws lambda <name> info        — function summary\n'
            '  sg aws lambda <name> logs        — CloudWatch logs\n'
            '  sg aws lambda <name> invocations — recent invocations\n\n'
            '<name> accepts fuzzy substrings — e.g. "waker" for "sg-compute-vault-publish-waker".'
        )
        super().__init__(name='lambda', help=help_text, **attrs)
        self._resolver = resolver or Lambda__Name__Resolver()
        self.add_command(cmd_list, 'list')

    def list_commands(self, ctx):
        try:
            names = self._resolver.all_function_names()
        except Exception:
            names = []
        return ['list'] + sorted(names)

    def get_command(self, ctx, name):
        if name == 'list':
            return cmd_list
        try:
            resolved = self._resolver.resolve(name)
        except ValueError as exc:
            console.print(f'[red]✗  {exc}[/red]')
            return None
        grp = Lambda__Function__Group(function_name=resolved)
        return grp


# ── list command ──────────────────────────────────────────────────────────────

import json

from rich.table import Table
from sgraph_ai_service_playwright__cli.aws.lambda_.service.Lambda__AWS__Client import Lambda__AWS__Client


@click.command('list')
@click.option('--runtime', default=None,  help='Filter by runtime (e.g. python3.12).')
@click.option('--json', 'as_json', is_flag=True, default=False, help='Output as JSON.')
def cmd_list(runtime, as_json):
    """List all Lambda functions in the account/region."""
    fns = Lambda__AWS__Client().list_functions()
    if runtime:
        fns = [f for f in fns if str(f.runtime) == runtime]
    if as_json:
        click.echo(json.dumps([f.json() for f in fns], indent=2))
        return
    if not fns:
        console.print('[dim]No Lambda functions found.[/dim]')
        return
    tbl = Table(title='Lambda Functions')
    tbl.add_column('Name',         style='cyan')
    tbl.add_column('Runtime',      style='green')
    tbl.add_column('State',        style='yellow')
    tbl.add_column('Handler',      style='white')
    tbl.add_column('Memory',       style='dim')
    tbl.add_column('Last modified',style='dim')
    for f in fns:
        tbl.add_row(
            str(f.name), str(f.runtime), str(f.state),
            f.handler, str(f.memory_size), f.last_modified or '—'
        )
    console.print(tbl)
