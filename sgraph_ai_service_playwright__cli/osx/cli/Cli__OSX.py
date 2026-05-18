# ═══════════════════════════════════════════════════════════════════════════════
# SG Credentials — Cli__OSX
# Typer subapp root for: sg osx
# Currently mounts only the keyring subapp.
# ═══════════════════════════════════════════════════════════════════════════════

import typer

from sgraph_ai_service_playwright__cli.osx.keyring.cli.Cli__OSX__Keyring import app as keyring_app

app = typer.Typer(no_args_is_help=True,
                  help='macOS-specific helpers (Keychain, etc.).')

app.add_typer(keyring_app, name='keyring', help='Low-level macOS Keychain operations.')
