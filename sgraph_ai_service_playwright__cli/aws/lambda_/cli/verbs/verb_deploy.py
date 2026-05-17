# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — verb_deploy
# `sg aws lambda <name> deploy` — deploy or update a Lambda function.
# Replaces `sg aws lambda deployment deploy <name>` (new shape).
# Mutation guard required.
# ═══════════════════════════════════════════════════════════════════════════════

import json
import os

import click
from rich.console import Console

from sg_compute.cli.base.Spec__CLI__Errors                                               import spec_cli_errors
from sgraph_ai_service_playwright__cli.aws.lambda_.enums.Enum__Lambda__Runtime           import Enum__Lambda__Runtime
from sgraph_ai_service_playwright__cli.aws.lambda_.primitives.Safe_Str__Lambda__Name     import Safe_Str__Lambda__Name
from sgraph_ai_service_playwright__cli.aws.lambda_.schemas.Schema__Lambda__Deploy__Request import Schema__Lambda__Deploy__Request
from sgraph_ai_service_playwright__cli.aws.lambda_.service.Lambda__Deployer              import Lambda__Deployer

console = Console()


def _mutation_guard():
    if not os.environ.get('SG_AWS__LAMBDA__ALLOW_MUTATIONS'):
        console.print('[red]Set SG_AWS__LAMBDA__ALLOW_MUTATIONS=1 to allow Lambda mutations.[/red]')
        raise SystemExit(1)


@click.command('deploy')
@click.pass_context
@click.option('--code-path', required=True,         help='Path to folder containing function code.')
@click.option('--handler',   required=True,         help='Handler spec e.g. handler:handler.')
@click.option('--role-arn',  default='',            help='IAM execution role ARN.')
@click.option('--runtime',   default='python3.11',  help='Lambda runtime.')
@click.option('--memory',    default=256,            help='Memory in MB.')
@click.option('--timeout',   default=900,            help='Timeout in seconds.')
@click.option('--json',      'as_json', is_flag=True, default=False, help='Output as JSON.')
def cmd_deploy(ctx, code_path, handler, role_arn, runtime, memory, timeout, as_json):
    """Deploy or update a Lambda function from a local folder."""
    _mutation_guard()
    fn_name = ctx.obj['function_name']
    with spec_cli_errors():
        try:
            rt = Enum__Lambda__Runtime(runtime)
        except ValueError:
            console.print(f'[red]Unknown runtime: {runtime}[/red]')
            raise SystemExit(1)
        req = Schema__Lambda__Deploy__Request(
            name        = Safe_Str__Lambda__Name(fn_name),
            folder_path = code_path,
            handler     = handler,
            role_arn    = role_arn,
            runtime     = rt,
            memory_size = memory,
            timeout     = timeout,
        )
        resp = Lambda__Deployer().deploy_from_folder(req)
        if as_json:
            click.echo(json.dumps(resp.json(), indent=2))
            return
        if resp.success:
            verb = 'Created' if resp.created else 'Updated'
            console.print(f'[green]{verb}[/green] {fn_name}')
            console.print(f'  ARN: {resp.function_arn}')
        else:
            console.print(f'[red]Failed:[/red] {resp.message}')
            raise SystemExit(1)
