# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — Firefox: Cli__Firefox
# Per-spec CLI app. Mounted at: sg-compute spec firefox <verb>
#
# Commands
# ────────
#   sg-compute spec firefox list              [--region X]
#   sg-compute spec firefox info <stack-name> [--region X]
#   sg-compute spec firefox create            [--region X] [--instance-type T] [--max-hours N]
#   sg-compute spec firefox delete <name>     [--region X] [--yes]
#   sg-compute spec firefox set-credentials   --node <id> --username <u> --password <p> [--region X]
#   sg-compute spec firefox upload-mitm-script --node <id> --file <path> [--region X]
# ═══════════════════════════════════════════════════════════════════════════════

import typer
from rich.console                                                                    import Console

DEFAULT_REGION = 'eu-west-2'

app = typer.Typer(no_args_is_help=True,
                  help='Manage Firefox compute nodes — ephemeral EC2 instances with Firefox + MITM proxy.')


def _service():
    from sg_compute_specs.firefox.service.Firefox__Service import Firefox__Service
    return Firefox__Service().setup()


@app.command()
def list(region: str = typer.Option(DEFAULT_REGION, '--region', '-r', help='AWS region.')):
    try:
        result = _service().list_stacks(region=region)
        console = Console(highlight=False, width=200)
        for stack in result.stacks:
            console.print(f'{stack.stack_name}  {stack.state}  {stack.public_ip or "(no IP)"}  {stack.region}')
        if not result.stacks:
            console.print('No active firefox stacks.')
    except Exception as e:
        if 'credential' in str(e).lower() or 'NoCredential' in type(e).__name__:
            typer.echo(f'AWS credentials not configured: {e}', err=True)
            raise typer.Exit(1)
        raise


@app.command()
def info(stack_name: str = typer.Argument(..., help='Firefox stack name.'),
         region    : str = typer.Option(DEFAULT_REGION, '--region', '-r', help='AWS region.')):
    try:
        result = _service().get_stack_info(region=region, stack_name=stack_name)
        if result is None:
            typer.echo(f'Stack {stack_name!r} not found in {region}', err=True)
            raise typer.Exit(1)
        console = Console(highlight=False, width=200)
        console.print(result.json())
    except typer.Exit:
        raise
    except Exception as e:
        if 'credential' in str(e).lower() or 'NoCredential' in type(e).__name__:
            typer.echo(f'AWS credentials not configured: {e}', err=True)
            raise typer.Exit(1)
        raise


@app.command()
def create(region       : str  = typer.Option(DEFAULT_REGION, '--region'      , '-r'),
           instance_type: str  = typer.Option('t3.large'    , '--instance-type', '-t'),
           max_hours    : int  = typer.Option(1             , '--max-hours'         ),
           name         : str  = typer.Option(''            , '--name'              , help='Override stack name.'),
           enable_shell : bool = typer.Option(False         , '--enable-shell'      , help='Disable the shell command allowlist on the sidecar (allows docker images, exec, etc.).')):
    from sg_compute_specs.firefox.schemas.Schema__Firefox__Stack__Create__Request import Schema__Firefox__Stack__Create__Request
    try:
        svc  = _service()
        req  = Schema__Firefox__Stack__Create__Request(
            instance_type = instance_type,
            max_hours     = max_hours    ,
            enable_shell  = enable_shell ,
        )
        if name:
            req.stack_name.__init__(name)
        req.region.__init__(region)
        resp = svc.create_stack(req)
        console = Console(highlight=False, width=200)
        console.print(f'Launched: {resp.stack_name}  instance={resp.instance_id}  region={resp.region}')
    except Exception as e:
        if 'credential' in str(e).lower() or 'NoCredential' in type(e).__name__:
            typer.echo(f'AWS credentials not configured: {e}', err=True)
            raise typer.Exit(1)
        raise


@app.command()
def delete(stack_name: str  = typer.Argument(..., help='Firefox stack name.'),
           region    : str  = typer.Option(DEFAULT_REGION, '--region', '-r', help='AWS region.'),
           yes       : bool = typer.Option(False, '--yes', '-y', help='Skip confirmation.')):
    if not yes:
        typer.confirm(f'Delete firefox stack {stack_name!r} in {region}?', abort=True)
    try:
        result  = _service().delete_stack(region=region, stack_name=stack_name)
        console = Console(highlight=False, width=200)
        if result.deleted:
            console.print(f'Deleted: {stack_name}')
        else:
            console.print(f'Delete failed for {stack_name}', style='bold red')
            raise typer.Exit(1)
    except typer.Exit:
        raise
    except Exception as e:
        if 'credential' in str(e).lower() or 'NoCredential' in type(e).__name__:
            typer.echo(f'AWS credentials not configured: {e}', err=True)
            raise typer.Exit(1)
        raise


@app.command('set-credentials')
def set_credentials(node    : str = typer.Option(..., '--node'    , '-n', help='Firefox node (stack) name.'),
                    username: str = typer.Option(..., '--username' , '-u', help='Credentials username.'),
                    password: str = typer.Option(..., '--password' , '-p', help='Credentials password.'),
                    region  : str = typer.Option(DEFAULT_REGION, '--region', '-r', help='AWS region.')):
    try:
        result  = _service().set_credentials(region=region, node_id=node, username=username, password=password)
        console = Console(highlight=False, width=200)
        if result.updated:
            console.print(f'Credentials updated for {node}')
        else:
            console.print(f'Failed to update credentials for {node}: {result.message}', style='bold red')
            raise typer.Exit(1)
    except typer.Exit:
        raise
    except Exception as e:
        if 'credential' in str(e).lower() or 'NoCredential' in type(e).__name__:
            typer.echo(f'AWS credentials not configured: {e}', err=True)
            raise typer.Exit(1)
        raise


@app.command('upload-mitm-script')
def upload_mitm_script(node  : str = typer.Option(..., '--node'  , '-n', help='Firefox node (stack) name.'),
                       file  : str = typer.Option(..., '--file'  , '-f', help='Path to the mitmproxy script file.'),
                       region: str = typer.Option(DEFAULT_REGION, '--region', '-r', help='AWS region.')):
    import pathlib
    script_path = pathlib.Path(file)
    if not script_path.is_file():
        typer.echo(f'File not found: {file}', err=True)
        raise typer.Exit(1)
    content = script_path.read_text(encoding='utf-8')
    try:
        result  = _service().upload_mitm_script(region=region, node_id=node, script_content=content)
        console = Console(highlight=False, width=200)
        if result.uploaded:
            console.print(f'Mitm script uploaded to {node} ({len(content)} bytes)')
        else:
            console.print(f'Failed to upload script to {node}: {result.message}', style='bold red')
            raise typer.Exit(1)
    except typer.Exit:
        raise
    except Exception as e:
        if 'credential' in str(e).lower() or 'NoCredential' in type(e).__name__:
            typer.echo(f'AWS credentials not configured: {e}', err=True)
            raise typer.Exit(1)
        raise
