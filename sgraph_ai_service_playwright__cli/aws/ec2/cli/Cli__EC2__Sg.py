# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Cli__EC2__Sg
# Typer CLI surface for `sg aws ec2 sg *` commands.
#
# Command tree (P0 reads only — no deletes; SG deletes land in Slice 5):
#   sg aws ec2 sg list    [--vpc <vpc-id>] [--name <substring>] [--json]
#   sg aws ec2 sg show    <sg-id-or-name>                        [--json]
#   sg aws ec2 sg rules   <sg-id-or-name>                        [--json]
#   sg aws ec2 sg orphans [--vpc <vpc-id>]                       [--json]
# ═══════════════════════════════════════════════════════════════════════════════

import json

import typer
from rich.console import Console
from rich.table   import Table

from sg_compute.cli.base.Spec__CLI__Errors                            import spec_cli_errors
from sgraph_ai_service_playwright__cli.aws.ec2.service.EC2__AWS__Client import EC2__AWS__Client


console = Console()

app = typer.Typer(name='sg', help='EC2 security-group inspection and orphan-detection.',
                  no_args_is_help=True)


# ── helpers ───────────────────────────────────────────────────────────────────

@app.callback()
def _setup_ctx(ctx: typer.Context):
    if ctx.obj is None:
        ctx.obj = {}
    ctx.obj.setdefault('ec2_client', EC2__AWS__Client())


def _resolve_sg(client, sg_id_or_name: str, vpc_id: str = ''):                 # Wraps describe_security_group, converting ambiguity ValueError → typer.BadParameter
    try:
        return client.describe_security_group(sg_id_or_name, vpc_id=vpc_id)
    except ValueError as exc:
        raise typer.BadParameter(str(exc))


def _rule_to_dict(rule) -> dict:
    return dict(
        ip_protocol      = str(rule.ip_protocol),
        from_port        = int(rule.from_port),
        to_port          = int(rule.to_port),
        direction        = str(rule.direction),
        cidr_ipv4        = str(rule.cidr_ipv4),
        cidr_ipv6        = str(rule.cidr_ipv6),
        referenced_sg_id = str(rule.referenced_sg_id),
        description      = str(rule.description),
    )


def _sg_to_dict(sg) -> dict:                                                   # JSON-safe view of Schema__EC2__Security_Group
    return dict(
        sg_id                 = str(sg.sg_id),
        name                  = str(sg.name),
        vpc_id                = str(sg.vpc_id),
        description           = str(sg.description),
        owner_id              = str(sg.owner_id),
        ingress_rules         = [_rule_to_dict(r) for r in sg.ingress_rules],
        egress_rules          = [_rule_to_dict(r) for r in sg.egress_rules],
        attached_eni_ids      = [str(e) for e in sg.attached_eni_ids],
        attached_instance_ids = [str(i) for i in sg.attached_instance_ids],
    )


def _format_port_range(rule) -> str:
    if int(rule.from_port) == -1 and int(rule.to_port) == -1:
        return 'all'
    if int(rule.from_port) == int(rule.to_port):
        return str(rule.from_port)
    return f'{rule.from_port}-{rule.to_port}'


def _format_target(rule) -> str:
    if str(rule.cidr_ipv4):
        return str(rule.cidr_ipv4)
    if str(rule.cidr_ipv6):
        return str(rule.cidr_ipv6)
    if str(rule.referenced_sg_id):
        return str(rule.referenced_sg_id)
    return '—'


def _render_sg_summary_table(sgs: list, title: str) -> None:
    if not sgs:
        console.print('No security groups found.')
        return
    t = Table(title=title)
    t.add_column('SG ID',    style='cyan')
    t.add_column('Name',     style='green')
    t.add_column('VPC',      style='dim')
    t.add_column('Ingress',  style='dim', justify='right')
    t.add_column('Egress',   style='dim', justify='right')
    for sg in sgs:
        t.add_row(str(sg.sg_id),
                  str(sg.name)   or '—',
                  str(sg.vpc_id) or '—',
                  str(len(sg.ingress_rules)),
                  str(len(sg.egress_rules)))
    console.print(t)


def _render_rules_table(sg, title: str) -> None:
    rows = [(r, 'ingress') for r in sg.ingress_rules] + \
           [(r, 'egress')  for r in sg.egress_rules]
    if not rows:
        console.print('(no rules)')
        return
    t = Table(title=title)
    t.add_column('Direction',   style='bold')
    t.add_column('Protocol',    style='cyan')
    t.add_column('Ports',       style='dim')
    t.add_column('Target',      style='green')
    t.add_column('Description', style='dim')
    for rule, _label in rows:
        t.add_row(str(rule.direction),
                  str(rule.ip_protocol) or '—',
                  _format_port_range(rule),
                  _format_target(rule),
                  str(rule.description) or '')
    console.print(t)


# ── list ──────────────────────────────────────────────────────────────────────

@app.command('list')
@spec_cli_errors
def sg_list(ctx     : typer.Context,
            vpc     : str  = typer.Option('', '--vpc',
                                           help='Filter by VPC ID.'),
            name    : str  = typer.Option('', '--name',
                                           help='Server-side group-name substring filter.'),
            as_json : bool = typer.Option(False, '--json', help='Output as JSON.')):
    """List security groups visible in the current account / region."""
    client = ctx.obj['ec2_client']
    sgs    = client.list_security_groups(vpc_id=vpc, name_substring=name)
    if as_json:
        typer.echo(json.dumps([_sg_to_dict(s) for s in sgs], indent=2))
        return
    title = 'Security Groups'
    if vpc:  title += f' (vpc={vpc})'
    if name: title += f' (name~{name})'
    _render_sg_summary_table(list(sgs), title=title)


# ── show ──────────────────────────────────────────────────────────────────────

@app.command('show')
@spec_cli_errors
def sg_show(ctx           : typer.Context,
            sg_id_or_name : str  = typer.Argument(..., help='SG ID (sg-*) or group name.'),
            vpc           : str  = typer.Option('', '--vpc', help='Narrow name resolution to a VPC.'),
            as_json       : bool = typer.Option(False, '--json', help='Output as JSON.')):
    """Show full detail for one security group, including attached ENIs and instances."""
    client = ctx.obj['ec2_client']
    sg     = _resolve_sg(client, sg_id_or_name, vpc_id=vpc)
    if sg is None:
        console.print(f'[red]Security group not found:[/red] {sg_id_or_name}')
        raise typer.Exit(1)
    if as_json:
        typer.echo(json.dumps(_sg_to_dict(sg), indent=2))
        return
    t = Table(box=None, show_header=False, padding=(0, 2))
    t.add_column(style='bold', min_width=22)
    t.add_column()
    rows = [
        ('sg id',          str(sg.sg_id)),
        ('name',           str(sg.name)        or '—'),
        ('vpc',            str(sg.vpc_id)      or '—'),
        ('description',    str(sg.description) or '—'),
        ('owner',          str(sg.owner_id)    or '—'),
        ('ingress rules',  str(len(sg.ingress_rules))),
        ('egress rules',   str(len(sg.egress_rules))),
        ('attached enis',  ', '.join(str(e) for e in sg.attached_eni_ids)      or '(none)'),
        ('attached insts', ', '.join(str(i) for i in sg.attached_instance_ids) or '(none)'),
    ]
    for label, value in rows:
        t.add_row(label, value)
    console.print()
    console.print(t)
    console.print()
    _render_rules_table(sg, title=f'Rules — {sg.sg_id}')


# ── rules ─────────────────────────────────────────────────────────────────────

@app.command('rules')
@spec_cli_errors
def sg_rules(ctx           : typer.Context,
             sg_id_or_name : str  = typer.Argument(..., help='SG ID (sg-*) or group name.'),
             vpc           : str  = typer.Option('', '--vpc', help='Narrow name resolution to a VPC.'),
             as_json       : bool = typer.Option(False, '--json', help='Output as JSON.')):
    """Show ingress and egress rules for one security group."""
    client = ctx.obj['ec2_client']
    sg     = _resolve_sg(client, sg_id_or_name, vpc_id=vpc)
    if sg is None:
        console.print(f'[red]Security group not found:[/red] {sg_id_or_name}')
        raise typer.Exit(1)
    if as_json:
        typer.echo(json.dumps(dict(
            sg_id         = str(sg.sg_id),
            name          = str(sg.name),
            vpc_id        = str(sg.vpc_id),
            ingress_rules = [_rule_to_dict(r) for r in sg.ingress_rules],
            egress_rules  = [_rule_to_dict(r) for r in sg.egress_rules],
        ), indent=2))
        return
    _render_rules_table(sg, title=f'Rules — {sg.sg_id} ({sg.name})')


# ── orphans ───────────────────────────────────────────────────────────────────

@app.command('orphans')
@spec_cli_errors
def sg_orphans(ctx     : typer.Context,
               vpc     : str  = typer.Option('', '--vpc',
                                              help='Limit scan to a single VPC.'),
               as_json : bool = typer.Option(False, '--json', help='Output as JSON.')):
    """List security groups with no attached ENIs (potential cleanup targets)."""
    client  = ctx.obj['ec2_client']
    sgs     = client.list_security_groups(vpc_id=vpc)
    orphans = []
    for sg in sgs:
        # Skip the per-VPC 'default' SG: AWS auto-creates it and refuses to delete
        # it, so flagging it as an orphan is pure noise during cleanup.
        if str(sg.name) == 'default':
            continue
        enis = client.list_network_interfaces(sg_id=str(sg.sg_id))             # small per-SG batch — interactive cleanup, not a perf hot path
        if len(enis) == 0:
            orphans.append(sg)
    if as_json:
        typer.echo(json.dumps([_sg_to_dict(s) for s in orphans], indent=2))
        return
    title = 'Orphan Security Groups (no attached ENIs)'
    if vpc:
        title += f' — vpc={vpc}'
    _render_sg_summary_table(orphans, title=title)
