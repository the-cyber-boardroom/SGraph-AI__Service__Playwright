# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Cli__Sentinel__Echo
# `sg sentinel echo serve` — run the httpget echo server (the origin / measurement
# tool). Echoes each request as JSON (or HTML on Accept: text/html / ?format=html)
# and records what reached it (GET /__hits). The same Echo__Payload runs on docker
# (see echo/docker/Dockerfile) and Lambda (echo/lambda_handler.py).
# ═══════════════════════════════════════════════════════════════════════════════

import typer
from rich.console import Console

from sg_compute.cli.base.Spec__CLI__Errors import spec_cli_errors

app     = typer.Typer(name='echo', help='httpget echo server (origin / measurement tool).', no_args_is_help=True)
console = Console()


@app.command('serve')
@spec_cli_errors
def cmd_serve(host: str = typer.Option('127.0.0.1', '--host', help='Bind host (0.0.0.0 in docker).'),
              port: int = typer.Option(8080, '--port', '-p', help='Bind port.')):
    """Run the httpget echo server (blocks until Ctrl-C)."""
    from sgraph_ai_service_playwright__cli.sentinel.traffic.echo.Echo__Server import serve
    serve(host=host, port=port)
