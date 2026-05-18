# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — verb_check
# `sg aws bedrock check [--region TEXT] [--json]`
# Runs 8 preflight checks; prints a Rich table; exits 1 on any FAIL.
# ═══════════════════════════════════════════════════════════════════════════════

import json
import sys
from typing                                                                      import Optional

import typer
from rich.console                                                                import Console

from sgraph_ai_service_playwright__cli.aws.bedrock.enums.Enum__Bedrock__Check__Status import Enum__Bedrock__Check__Status
from sgraph_ai_service_playwright__cli.aws.bedrock.service.Bedrock__Preflight          import Bedrock__Preflight
from sg_compute.cli.base.Spec__CLI__Errors                                  import spec_cli_errors

_ICON = {                                                                          # Status → display icon
    Enum__Bedrock__Check__Status.PASS: '[✓]',
    Enum__Bedrock__Check__Status.WARN: '[⚠]',
    Enum__Bedrock__Check__Status.FAIL: '[✗]',
}

_STYLE = {                                                                         # Status → Rich colour
    Enum__Bedrock__Check__Status.PASS: 'green'  ,
    Enum__Bedrock__Check__Status.WARN: 'yellow' ,
    Enum__Bedrock__Check__Status.FAIL: 'red'    ,
}


def register_check(app: typer.Typer) -> None:

    @app.command('check')
    @spec_cli_errors
    def bedrock_check(region     : Optional[str] = typer.Option(None , '--region', help='Override active role region.'),
                      json_output: bool          = typer.Option(False, '--json'  , help='Output JSON list of check results.')):
        """Run Bedrock preflight checks — IAM permissions, region support, model access, capture writer."""
        preflight = Bedrock__Preflight()
        results   = preflight.run_all(region=region or '')

        if json_output:
            typer.echo(json.dumps([dict(check_name=r.check_name ,
                                        status    =r.status.value,
                                        message   =r.message     ,
                                        hint      =r.hint        )
                                   for r in results], indent=2))
            any_fail = any(r.status == Enum__Bedrock__Check__Status.FAIL for r in results)
            raise typer.Exit(1 if any_fail else 0)

        c = Console(highlight=False)
        c.print()
        effective = region or preflight.control_client.current_region()
        c.print(f'  Bedrock preflight  ·  region={effective}')
        c.print()

        for r in results:
            icon  = _ICON.get(r.status, '   ')
            style = _STYLE.get(r.status, '')
            c.print(f'  [{style}]{icon}  {r.check_name:<24}[/{style}]  {r.message}')

        c.print()
        any_fail = any(r.status == Enum__Bedrock__Check__Status.FAIL for r in results)
        any_warn = any(r.status == Enum__Bedrock__Check__Status.WARN for r in results)

        if any_fail or any_warn:
            c.print('  [dim]Next step:  sg aws bedrock setup --open-console[/dim]')
            c.print('  [dim]             Or:  sg aws bedrock setup --print-policy[/dim]')
            c.print()

        if any_fail:
            raise typer.Exit(1)
        if any_warn:
            print('Warning: some checks produced warnings', file=sys.stderr)
            raise typer.Exit(0)
