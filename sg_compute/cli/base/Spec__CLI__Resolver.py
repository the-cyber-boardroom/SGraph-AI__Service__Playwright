# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute — Spec__CLI__Resolver
# Implements the "auto-pick / prompt / error" rule for optional name args.
# ═══════════════════════════════════════════════════════════════════════════════

from typing import Optional

import typer
from rich.console import Console

from osbot_utils.type_safe.Type_Safe import Type_Safe


class Spec__CLI__Resolver(Type_Safe):

    def resolve(self, service, provided: Optional[str], region: str, spec_id: str) -> str:
        if provided:
            return provided
        listing      = service.list_stacks(region)
        names        = [str(s.stack_name) for s in listing.stacks if str(s.stack_name)]
        region_label = str(getattr(listing, 'region', '') or region)

        if len(names) == 0:
            Console(highlight=False, stderr=True).print(
                f'\n  [yellow]No {spec_id} stacks in {region_label}.[/]'
                f'  Run: [bold]sg-compute spec {spec_id} create[/]\n')
            raise typer.Exit(1)

        if len(names) == 1:
            Console(highlight=False).print(
                f'\n  [dim]One stack found — using [bold]{names[0]}[/][/]')
            return names[0]

        c = Console(highlight=False)
        c.print(f'\n  [bold]Multiple {spec_id} stacks in {region_label}:[/]')
        for idx, name in enumerate(names, start=1):
            c.print(f'    {idx}. {name}')
        raw = typer.prompt('\n  Pick a stack number', type=int)
        try:
            choice = int(raw)
        except (TypeError, ValueError):
            choice = -1
        if choice < 1 or choice > len(names):
            Console(highlight=False, stderr=True).print(f'\n  [red]Invalid selection: {raw}[/]\n')
            raise typer.Exit(1)
        return names[choice - 1]
