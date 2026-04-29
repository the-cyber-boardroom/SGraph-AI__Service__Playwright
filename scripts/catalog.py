# ═══════════════════════════════════════════════════════════════════════════════
# SG Playwright — catalog.py
# CLI entry-point: sp catalog
# Cross-section enumeration. Mirrors GET /catalog/types + GET /catalog/stacks.
#
# Two commands:
#   sp catalog types                 — list all known stack types + metadata
#   sp catalog stacks [--type X]     — list live stacks (across all sections)
#
# Direct AWS access — no FastAPI server required (per Q5 default in
# team/comms/briefs/v0.1.97__clean-top-level-commands/04__open-questions.md).
# ═══════════════════════════════════════════════════════════════════════════════

from typing                                                                         import Optional

import typer
from rich.console                                                                   import Console

from sgraph_ai_service_playwright__cli.catalog.cli.Renderers                        import render_stacks, render_types
from sgraph_ai_service_playwright__cli.catalog.enums.Enum__Stack__Type              import Enum__Stack__Type
from sgraph_ai_service_playwright__cli.catalog.service.Stack__Catalog__Service      import Stack__Catalog__Service


app = typer.Typer(no_args_is_help=True,
                    help='Cross-section enumeration — list known stack types or live stacks across all sections.')


def _service() -> Stack__Catalog__Service:                                          # Single seam — tests override to inject an in-memory fake
    s = Stack__Catalog__Service()
    s.linux_service  .setup()
    s.docker_service .setup()
    return s


@app.command()
def types():
    """List all registered stack types (linux / docker / elastic / opensearch / vnc / …)."""
    catalog = _service().get_catalog()
    render_types(catalog, Console(highlight=False, width=200))


@app.command()
def stacks(type_filter: Optional[str] = typer.Option(None, '--type', '-t',
                                                       help='Filter to one stack type id (linux / docker / elastic / opensearch / vnc).')):
    """List live stacks across every section. Pass --type to filter by stack type."""
    enum_filter = None
    if type_filter:
        try:
            enum_filter = Enum__Stack__Type(type_filter)
        except ValueError:
            valid = ', '.join(t.value for t in Enum__Stack__Type)
            raise typer.BadParameter(f'unknown type {type_filter!r}; valid: {valid}')
    listing = _service().list_all_stacks(type_filter=enum_filter)
    render_stacks(listing, Console(highlight=False, width=200))
