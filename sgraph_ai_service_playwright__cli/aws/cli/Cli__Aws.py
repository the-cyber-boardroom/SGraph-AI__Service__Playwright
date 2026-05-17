# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Cli__Aws
# Top-level group for `sg aws *` commands.
# Subclasses TyperGroup to inject the dynamic Lambda__App__Group as the
# 'lambda' command so it is available at Click-tree resolution time (not
# just at import-time, since Typer rebuilds the Click tree on every
# get_command() call).
# ═══════════════════════════════════════════════════════════════════════════════

import typer
from typer.core import TyperGroup

from sgraph_ai_service_playwright__cli.aws.dns.cli.Cli__Dns                 import dns_app
from sgraph_ai_service_playwright__cli.aws.acm.cli.Cli__Acm                 import acm_app
from sgraph_ai_service_playwright__cli.aws.billing.cli.Cli__Billing         import billing_app
from sgraph_ai_service_playwright__cli.aws.cf.cli.Cli__Cf                   import cf_app
from sgraph_ai_service_playwright__cli.aws.iam.cli.Cli__Iam                 import iam_app
from sgraph_ai_service_playwright__cli.aws.lambda_.cli.Lambda__Click__Group import Lambda__App__Group


class _AwsGroup(TyperGroup):                                                       # injects dynamic Lambda__App__Group as 'lambda'

    def list_commands(self, ctx):
        base = list(super().list_commands(ctx))
        if 'lambda' not in base:
            base = sorted(set(base + ['lambda']))
        return base

    def get_command(self, ctx, name):
        if name == 'lambda':
            return Lambda__App__Group()
        return super().get_command(ctx, name)


app = typer.Typer(
    name            = 'aws',
    help            = 'AWS resource management (DNS, ACM, billing, CloudFront, IAM, Lambda, …).',
    no_args_is_help = True,
    cls             = _AwsGroup,
)

app.add_typer(dns_app,     name='dns'    )
app.add_typer(acm_app,     name='acm'    )
app.add_typer(billing_app, name='billing')
app.add_typer(cf_app,      name='cf'     )
app.add_typer(iam_app,     name='iam'    )
