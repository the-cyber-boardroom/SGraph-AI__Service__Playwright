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

from sgraph_ai_service_playwright__cli.aws.dns.cli.Cli__Dns                  import dns_app
from sgraph_ai_service_playwright__cli.aws.acm.cli.Cli__Acm                  import acm_app
from sgraph_ai_service_playwright__cli.aws.billing.cli.Cli__Billing          import billing_app
from sgraph_ai_service_playwright__cli.aws.cf.cli.Cli__Cf                    import cf_app
from sgraph_ai_service_playwright__cli.aws.iam.cli.Cli__Iam                  import iam_app
from sgraph_ai_service_playwright__cli.aws.lambda_.cli.Lambda__Click__Group  import Lambda__App__Group
from sgraph_ai_service_playwright__cli.credentials.cli.Cli__Credentials       import app as _credentials_app
from sgraph_ai_service_playwright__cli.aws.s3.cli.Cli__S3                    import app as s3_app
from sgraph_ai_service_playwright__cli.aws.ec2.cli.Cli__EC2                  import app as ec2_app
from sgraph_ai_service_playwright__cli.aws.fargate.cli.Cli__Fargate          import app as fargate_app
from sgraph_ai_service_playwright__cli.aws.bedrock.cli.Cli__Bedrock          import app as bedrock_app
from sgraph_ai_service_playwright__cli.aws.cloudtrail.cli.Cli__CloudTrail    import app as cloudtrail_app
from sgraph_ai_service_playwright__cli.aws.creds.cli.Cli__Creds              import app as creds_app
from sgraph_ai_service_playwright__cli.aws.observe.cli.Cli__Observe          import app as observe_app


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

# ── existing surfaces ─────────────────────────────────────────────────────────
app.add_typer(dns_app,        name='dns'        )
app.add_typer(acm_app,        name='acm'        )
app.add_typer(billing_app,    name='billing'    )
app.add_typer(cf_app,         name='cf'         )
app.add_typer(iam_app,        name='iam'        )

# ── credentials remount (locked decision #13) — also available as `sg credentials` hidden alias ──
app.add_typer(_credentials_app, name='credentials', help='Manage AWS credentials and roles (Keychain-backed).')

# ── v0.2.29 new surfaces (bodies filled in by their respective sibling slices) ──
app.add_typer(s3_app,         name='s3'         )
app.add_typer(ec2_app,        name='ec2'        )
app.add_typer(fargate_app,    name='fargate'    )
app.add_typer(bedrock_app,    name='bedrock'    )
app.add_typer(cloudtrail_app, name='cloudtrail' )
app.add_typer(creds_app,      name='creds'      )
app.add_typer(observe_app,    name='observe'    )
