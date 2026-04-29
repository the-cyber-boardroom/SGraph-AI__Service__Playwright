# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Catalog Renderers
# Tier-2A Rich renderers for the sp catalog typer commands. Pure functions —
# accept a Type_Safe schema and write to a Console. No service / AWS calls.
# ═══════════════════════════════════════════════════════════════════════════════

from rich.console                                                                   import Console
from rich.table                                                                     import Table

from sgraph_ai_service_playwright__cli.catalog.schemas.Schema__Stack__Summary__List import Schema__Stack__Summary__List
from sgraph_ai_service_playwright__cli.catalog.schemas.Schema__Stack__Type__Catalog import Schema__Stack__Type__Catalog


def render_types(catalog: Schema__Stack__Type__Catalog, c: Console) -> None:
    if not catalog.entries:
        c.print('  [dim]No stack types registered.[/]')
        return
    t = Table(show_header=True, header_style='bold blue', box=None, padding=(0, 2))
    t.add_column('type-id'      , style='bold')
    t.add_column('display-name' , style='cyan')
    t.add_column('available'    )
    t.add_column('description'  )
    for entry in catalog.entries:
        t.add_row(str(entry.type_id.value)                        ,
                  str(entry.display_name)                         ,
                  'yes' if entry.available else 'no'              ,
                  str(entry.description)                          )
    c.print(t)


def render_stacks(listing: Schema__Stack__Summary__List, c: Console) -> None:
    if not listing.stacks:
        c.print('  [dim]No live stacks found.[/]')
        return
    t = Table(show_header=True, header_style='bold blue', box=None, padding=(0, 2))
    t.add_column('type'       , style='bold')
    t.add_column('stack-name' , style='bold')
    t.add_column('instance-id', style='dim')
    t.add_column('state')
    t.add_column('public-ip'  , style='green')
    t.add_column('region'     , style='cyan')
    for s in listing.stacks:
        t.add_row(str(s.type_id.value),
                  str(s.stack_name)   ,
                  str(s.instance_id)  ,
                  str(s.state)        ,
                  str(s.public_ip) or '—',
                  str(s.region)       )
    c.print(t)
