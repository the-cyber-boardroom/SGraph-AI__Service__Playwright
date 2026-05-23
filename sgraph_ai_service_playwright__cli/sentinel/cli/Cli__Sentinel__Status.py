# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Cli__Sentinel__Status
# `sg sentinel status` — what's deployed (L1 function, L2 lambda) and the region.
# Read-only; emits the Aws__Context__Banner so the operator confirms the target.
# Exposed as a function the root group registers directly (a leaf, not a group).
# ═══════════════════════════════════════════════════════════════════════════════

import json

import typer
from rich.console import Console

from sgraph_ai_service_playwright__cli.aws._shared.Aws__Context__Banner    import Aws__Context__Banner
from sgraph_ai_service_playwright__cli.sentinel.service.Sentinel__Deployer import Sentinel__Deployer
from sg_compute.cli.base.Spec__CLI__Errors                                import spec_cli_errors

console = Console()


@spec_cli_errors
def status_command(region  : str  = typer.Option('', '--region', help='AWS region.'),
                   as_json : bool = typer.Option(False, '--json', help='Output as JSON.')):
    """Show what SG/Sentinel has deployed for the current account/region."""
    banner = Aws__Context__Banner().resolve(region)
    info   = Sentinel__Deployer(region=region or 'us-east-1',
                                account_id=banner.get('account_id', '')).status()
    if as_json:
        typer.echo(json.dumps(info, indent=2))
        return
    console.print(Aws__Context__Banner().render(region))
    console.print(f"L1 (CF Function): {'[green]present[/green]' if info['l1_function'] else '[dim]absent[/dim]'}")
    console.print(f"L2 (Lambda@Edge): {'[green]present[/green]' if info['l2_lambda'] else '[dim]absent[/dim]'}")
