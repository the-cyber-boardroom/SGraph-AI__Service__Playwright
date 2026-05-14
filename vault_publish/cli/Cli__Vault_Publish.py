# ═══════════════════════════════════════════════════════════════════════════════
# vault-publish — Cli__Vault_Publish
# CLI verb tree: sg vp { register | unpublish | status | wake | resolve | list |
# health }. A thin Typer wrapper over Publish__Service — same shape as the other
# sg CLI subgroups.
#
# In this Python-package build the CLI composes Publish__Service with the
# in-memory SG/Send-boundary stand-ins, so each invocation is self-contained
# (state does not persist between invocations). In production the CLI is pointed
# at the deployed vault-publish API instead — the verb surface is unchanged.
# ═══════════════════════════════════════════════════════════════════════════════

import typer
from rich.console                                            import Console

from vault_publish.service.Manifest__Verifier__In_Memory     import Manifest__Verifier__In_Memory
from vault_publish.service.Publish__Service                  import Publish__Service
from vault_publish.service.Slug__Resolver__In_Memory         import Slug__Resolver__In_Memory
from vault_publish.service.Vault__Fetcher__In_Memory         import Vault__Fetcher__In_Memory

app = typer.Typer(no_args_is_help=True,
                  help='Publish a vault as a website at <slug>.sgraph.app.')


def _service() -> Publish__Service:
    return Publish__Service(slug_resolver     = Slug__Resolver__In_Memory()    ,
                            vault_fetcher     = Vault__Fetcher__In_Memory()    ,
                            manifest_verifier = Manifest__Verifier__In_Memory())


def _console() -> Console:
    return Console(highlight=False, width=200)


@app.command()
def register(slug     : str = typer.Argument(..., help='Slug to register (3-40 chars, lowercase/digits/hyphens).'),
             owner    : str = typer.Option('', '--owner'  , help='Owner id the slug is bound to.'),
             key_ref  : str = typer.Option('', '--key-ref', help='Signing public key reference.')):
    response, error = _service().register(slug, owner, key_ref)
    console = _console()
    if error:
        console.print(f'[red]register failed:[/red] {error.value}')
        raise typer.Exit(code=1)
    console.print(f'[green]registered[/green] {response.slug} -> {response.url}')


@app.command()
def unpublish(slug: str = typer.Argument(..., help='Slug to unpublish.')):
    response, error = _service().unpublish(slug)
    console = _console()
    if error:
        console.print(f'[red]unpublish failed:[/red] {error.value}')
        raise typer.Exit(code=1)
    console.print(f'unpublished={response.unpublished} slug={response.slug}')


@app.command()
def status(slug: str = typer.Argument(..., help='Slug to query.')):
    response, error = _service().status(slug)
    console = _console()
    if error:
        console.print(f'[red]status failed:[/red] {error.value}')
        raise typer.Exit(code=1)
    console.print(f'slug={response.slug} registered={response.registered} '
                  f'instance_state={response.instance_state.value} url={response.url}')


@app.command()
def wake(slug: str = typer.Argument(..., help='Slug to wake.')):
    response = _service().wake(slug)
    _console().print(f'outcome={response.outcome.value} warming={response.warming} '
                     f'instance_state={response.instance_state.value} detail={response.detail}')


@app.command()
def resolve(slug: str = typer.Argument(..., help='Slug to resolve (no side effects).')):
    response, error = _service().resolve(slug)
    console = _console()
    if error:
        console.print(f'[red]resolve failed:[/red] {error.value}')
        raise typer.Exit(code=1)
    console.print(f'slug={response.slug} transfer_id={response.transfer_id} '
                  f'app_type={response.app_type} runtime={response.runtime}')


@app.command()
def list():
    response = _service().list()
    console  = _console()
    if not response.slugs:
        console.print('no registered slugs')
        return
    for slug in response.slugs:
        console.print(slug)


@app.command()
def health():
    response = _service().health()
    _console().print(f'dns_ok={response.dns_ok} cert_ok={response.cert_ok} '
                      f'distribution_ok={response.distribution_ok} waker_ok={response.waker_ok}\n'
                      f'{response.detail}')
