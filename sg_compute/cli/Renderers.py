# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute — CLI Renderers
# Pure Rich renderers for sg-compute typer commands. No service / AWS calls.
# ═══════════════════════════════════════════════════════════════════════════════

from rich.console                                                              import Console
from rich.table                                                                import Table

from sg_compute.core.spec.schemas.Schema__Spec__Catalogue                    import Schema__Spec__Catalogue
from sg_compute.core.spec.schemas.Schema__Spec__Manifest__Entry              import Schema__Spec__Manifest__Entry
from sg_compute.core.node.schemas.Schema__Node__List                         import Schema__Node__List
from sg_compute.core.stack.schemas.Schema__Stack__List                       import Schema__Stack__List
from sg_compute.core.pod.schemas.Schema__Pod__List                           import Schema__Pod__List


def render_spec_catalogue(catalogue: Schema__Spec__Catalogue, c: Console) -> None:
    if not catalogue.specs:
        c.print('  [dim]No specs registered.[/]')
        return
    t = Table(show_header=True, header_style='bold blue', box=None, padding=(0, 2))
    t.add_column('spec-id'     , style='bold')
    t.add_column('icon'        )
    t.add_column('display-name', style='cyan')
    t.add_column('stability'   )
    t.add_column('nav-group'   )
    t.add_column('version'     , style='dim')
    for entry in catalogue.specs:
        t.add_row(str(entry.spec_id)             ,
                  str(entry.icon)                ,
                  str(entry.display_name)        ,
                  str(entry.stability.value)     ,
                  str(entry.nav_group.value)     ,
                  str(entry.version)             )
    c.print(t)


def render_spec_entry(entry: Schema__Spec__Manifest__Entry, c: Console) -> None:
    c.print(f'[bold]{entry.icon}  {entry.display_name}[/]  [dim]({entry.spec_id})[/]')
    c.print(f'  version   : [cyan]{entry.version}[/]')
    c.print(f'  stability : {entry.stability.value}')
    c.print(f'  nav-group : {entry.nav_group.value}')
    c.print(f'  boot-secs : {entry.boot_seconds_typical}')
    if entry.capabilities:
        caps = ', '.join(str(cap.value) for cap in entry.capabilities)
        c.print(f'  caps      : {caps}')
    if entry.create_endpoint_path:
        c.print(f'  create    : [dim]{entry.create_endpoint_path}[/]')


def render_node_list(listing: Schema__Node__List, c: Console) -> None:
    if not listing.nodes:
        c.print('  [dim]No nodes found.[/]')
        return
    t = Table(show_header=True, header_style='bold blue', box=None, padding=(0, 2))
    t.add_column('node-id'      , style='bold')
    t.add_column('spec-id'      , style='cyan')
    t.add_column('state'        )
    t.add_column('instance-type')
    t.add_column('public-ip'    , style='green')
    t.add_column('region'       )
    for n in listing.nodes:
        t.add_row(str(n.node_id)       ,
                  str(n.spec_id)       ,
                  str(n.state.value)   ,
                  str(n.instance_type) ,
                  str(n.public_ip) or '—',
                  str(n.region)        )
    c.print(t)


def render_stack_list(listing: Schema__Stack__List, c: Console) -> None:
    if not listing.stacks:
        c.print('  [dim]No stacks found.[/]')
        return
    t = Table(show_header=True, header_style='bold blue', box=None, padding=(0, 2))
    t.add_column('stack-id', style='bold')
    t.add_column('spec-ids', style='cyan')
    t.add_column('node-ids')
    t.add_column('status'  )
    for s in listing.stacks:
        t.add_row(str(s.stack_id)           ,
                  ', '.join(s.spec_ids)     ,
                  ', '.join(s.node_ids)     ,
                  str(s.status)             )
    c.print(t)


def render_pod_list(listing: Schema__Pod__List, c: Console) -> None:
    if not listing.pods:
        c.print('  [dim]No pods found.[/]')
        return
    t = Table(show_header=True, header_style='bold blue', box=None, padding=(0, 2))
    t.add_column('pod-name', style='bold')
    t.add_column('node-id' , style='cyan')
    t.add_column('image'   )
    t.add_column('state'   )
    t.add_column('ports'   )
    for p in listing.pods:
        t.add_row(str(p.pod_name)     ,
                  str(p.node_id)      ,
                  str(p.image)        ,
                  str(p.state.value)  ,
                  str(p.ports) or '—' )
    c.print(t)
