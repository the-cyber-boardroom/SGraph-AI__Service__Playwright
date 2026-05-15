# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Cli__Aws
# Typer parent group for all AWS resource management commands.
# Sub-apps: dns, acm. Future siblings (ec2, iam, …) drop in next to them.
# Registered in scripts/provision_ec2.py as `app.add_typer(_aws_app, name='aws')`.
# ═══════════════════════════════════════════════════════════════════════════════

import typer

from sgraph_ai_service_playwright__cli.aws.dns.cli.Cli__Dns  import dns_app
from sgraph_ai_service_playwright__cli.aws.acm.cli.Cli__Acm  import acm_app

app = typer.Typer(name='aws', help='AWS resource management (DNS, ACM, …).', no_args_is_help=True)
app.add_typer(dns_app, name='dns')
app.add_typer(acm_app, name='acm')
