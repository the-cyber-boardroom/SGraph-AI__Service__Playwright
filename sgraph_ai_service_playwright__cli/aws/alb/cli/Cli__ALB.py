# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI aws/alb — Cli__ALB
# Top-level Typer group for `sg aws alb *` commands.
# Registers lb / tg / listener / stack sub-apps.
# ═══════════════════════════════════════════════════════════════════════════════

import typer

from sgraph_ai_service_playwright__cli.aws.alb.cli.Cli__ALB__LB       import app as lb_app
from sgraph_ai_service_playwright__cli.aws.alb.cli.Cli__ALB__TG       import app as tg_app
from sgraph_ai_service_playwright__cli.aws.alb.cli.Cli__ALB__Listener import app as listener_app
from sgraph_ai_service_playwright__cli.aws.alb.cli.Cli__ALB__Stack    import app as stack_app


app = typer.Typer(
    name            = 'alb',
    help            = 'AWS Application Load Balancer management.',
    no_args_is_help = True,
)

app.add_typer(lb_app,       name='lb')
app.add_typer(tg_app,       name='tg')
app.add_typer(listener_app, name='listener')
app.add_typer(stack_app,    name='stack')
