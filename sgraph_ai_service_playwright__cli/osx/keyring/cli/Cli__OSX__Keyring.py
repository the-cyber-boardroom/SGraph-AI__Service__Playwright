# ═══════════════════════════════════════════════════════════════════════════════
# SG Credentials — Cli__OSX__Keyring
# Typer subapp for: sg osx keyring.*
#
# Commands
# ────────
#   sg osx keyring get    <service> <account>
#   sg osx keyring set    <service> <account> <value>
#   sg osx keyring delete <service> <account>
#   sg osx keyring list   [--prefix sg.]
#   sg osx keyring search <service>
# ═══════════════════════════════════════════════════════════════════════════════

import typer

from sgraph_ai_service_playwright__cli.osx.keyring.service.Keyring__Mac__OS import Keyring__Mac__OS

app = typer.Typer(no_args_is_help=True,
                  help='Low-level macOS Keychain operations.')


def _keyring() -> Keyring__Mac__OS:
    return Keyring__Mac__OS()


@app.command()
def get(service : str = typer.Argument(..., help='Keychain service name.'),
        account : str = typer.Argument(..., help='Keychain account name.')):
    """Print the stored value for a keychain entry (never use in scripts — stdout only)."""
    value = _keyring().get(service, account)
    if value is None:
        typer.echo(f'[not found] {service}/{account}', err=True)
        raise typer.Exit(1)
    typer.echo(value)


@app.command()
def set(service : str = typer.Argument(..., help='Keychain service name.'),
        account : str = typer.Argument(..., help='Keychain account name.'),
        value   : str = typer.Argument(..., help='Value to store.')):
    """Store or update a keychain entry."""
    ok = _keyring().set(service, account, value)
    if ok:
        typer.echo(f'[ok] set {service}/{account}')
    else:
        typer.echo(f'[error] could not set {service}/{account}', err=True)
        raise typer.Exit(1)


@app.command()
def delete(service : str = typer.Argument(..., help='Keychain service name.'),
           account : str = typer.Argument(..., help='Keychain account name.')):
    """Delete a keychain entry."""
    ok = _keyring().delete(service, account)
    if ok:
        typer.echo(f'[ok] deleted {service}/{account}')
    else:
        typer.echo(f'[not found] {service}/{account}', err=True)
        raise typer.Exit(1)


@app.command(name='list')
def list_cmd(prefix: str = typer.Option('sg.', help='Filter entries whose service name starts with this prefix.')):
    """List all sg.* keychain entries."""
    entries = _keyring().list(prefix=prefix)
    if not entries:
        typer.echo('(no entries found)')
        return
    for entry in entries:
        typer.echo(f'{entry.service_name}/{entry.account}')


@app.command()
def search(service: str = typer.Argument(..., help='Exact service name to search for.')):
    """List all accounts stored under a specific service name."""
    entries = _keyring().search(service)
    if not entries:
        typer.echo(f'(no accounts found for {service!r})')
        return
    for entry in entries:
        typer.echo(f'{entry.account}')
