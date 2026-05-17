# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Cli__EC2
# Typer group for `sg aws ec2 *` commands.
# Bodies owned by Slice B (v0.2.29__sg-aws-ec2).
# ═══════════════════════════════════════════════════════════════════════════════

import typer

from sgraph_ai_service_playwright__cli.aws._shared.Mutation__Gate import require_mutation_gate

app = typer.Typer(name='ec2', help='EC2 instance management.', no_args_is_help=True)

_SLICE = "Slice B owns this body — see library/dev_packs/v0.2.29__sg-aws-ec2/"


@app.command('list')
def list_(state:   str  = typer.Option('all', '--state'),
          prefix:  str  = typer.Option('', '--prefix'),
          as_json: bool = typer.Option(False, '--json')):
    """List EC2 instances."""
    raise NotImplementedError(_SLICE)


@app.command('describe')
def describe(id_or_name: str  = typer.Argument(...),
             as_json:    bool = typer.Option(False, '--json')):
    """Show full instance details."""
    raise NotImplementedError(_SLICE)


@app.command('ssh-info')
def ssh_info(id_or_name: str = typer.Argument(...)):
    """Print SSH connection info (public DNS, key, user)."""
    raise NotImplementedError(_SLICE)


@app.command('tags')
def tags(id_or_name: str  = typer.Argument(...),
         as_json:    bool = typer.Option(False, '--json')):
    """List instance tags."""
    raise NotImplementedError(_SLICE)


@app.command('instance-types')
def instance_types(family:  str  = typer.Option('', '--family'),
                   as_json: bool = typer.Option(False, '--json')):
    """List available instance types in region."""
    raise NotImplementedError(_SLICE)


@app.command('pricing')
def pricing(instance_type: str  = typer.Argument(...),
            region:        str  = typer.Option('', '--region'),
            as_json:       bool = typer.Option(False, '--json')):
    """Show on-demand price per hour for an instance type."""
    raise NotImplementedError(_SLICE)


@app.command('create')
@require_mutation_gate('SG_AWS__EC2__ALLOW_MUTATIONS')
def create(ami:    str  = typer.Option(..., '--ami'),
           type_:  str  = typer.Option('t3.micro', '--type'),
           key:    str  = typer.Option('', '--key'),
           name:   str  = typer.Option('', '--name'),
           yes:    bool = typer.Option(False, '--yes', '-y')):
    """Launch an EC2 instance (gated)."""
    raise NotImplementedError(_SLICE)


@app.command('start')
@require_mutation_gate('SG_AWS__EC2__ALLOW_MUTATIONS')
def start(id_or_name: str  = typer.Argument(...),
          yes:        bool = typer.Option(False, '--yes', '-y')):
    """Start a stopped EC2 instance (gated)."""
    raise NotImplementedError(_SLICE)


@app.command('stop')
@require_mutation_gate('SG_AWS__EC2__ALLOW_MUTATIONS')
def stop(id_or_name: str  = typer.Argument(...),
         yes:        bool = typer.Option(False, '--yes', '-y')):
    """Stop a running EC2 instance (gated)."""
    raise NotImplementedError(_SLICE)


@app.command('terminate')
@require_mutation_gate('SG_AWS__EC2__ALLOW_MUTATIONS')
def terminate(id_or_name: str  = typer.Argument(...),
              yes:        bool = typer.Option(False, '--yes', '-y')):
    """Terminate an EC2 instance (gated)."""
    raise NotImplementedError(_SLICE)


@app.command('wait')
def wait(id_or_name: str = typer.Argument(...),
         state:      str = typer.Option('running', '--state'),
         timeout:    int = typer.Option(300, '--timeout')):
    """Wait for an instance to reach a target state."""
    raise NotImplementedError(_SLICE)
