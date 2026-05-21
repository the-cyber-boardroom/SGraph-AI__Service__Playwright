# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tui/tool_api: Cli__Tui_Api
# Builds the generic `tui api` Typer sub-group from a registry. Each host attaches it
# under its `tui` group so `sg <area> tui api list/describe/skills/state/invoke` work.
# The same registry + dispatch the chat and the explorer use — one source of truth.
# ═══════════════════════════════════════════════════════════════════════════════

import json

import typer

from sgraph_ai_service_playwright__cli.tui.tool_api.service.Tui_Api__Registry import Tui_Api__Registry


def make_tui_api_app(registry: Tui_Api__Registry) -> typer.Typer:
    app = typer.Typer(name='api', help='TUI API: discover + invoke this area\'s actions.', no_args_is_help=True)

    @app.command('list')
    def list_():
        """List the TUI APIs (and their actions) registered for this area."""
        for slug in registry.list_slugs():
            manifest = registry.get(slug).manifest()
            typer.echo(f'{slug}  ({manifest.name})')
            for action in manifest.actions:
                typer.echo(f'    {str(action.name):20} [{str(action.tier)}]  {action.description}')

    @app.command('describe')
    def describe(slug: str = typer.Argument(..., help='API slug, e.g. sg-aws.s3'),
                 as_json: bool = typer.Option(False, '--json', help='Emit the raw manifest JSON.')):
        """Show one API's manifest (actions, tiers, scopes, JSON Schemas)."""
        provider = registry.get(slug)
        if provider is None:
            typer.echo(f'no such API: {slug}'); raise typer.Exit(code=1)
        typer.echo(json.dumps(provider.manifest().json(), indent=2))

    @app.command('skills')
    def skills(slug: str = typer.Argument(..., help='API slug'),
               audience: str = typer.Argument('api', help='human | api | driver')):
        """Print a SKILL document for an API (what the model reads)."""
        provider = registry.get(slug)
        if provider is None:
            typer.echo(f'no such API: {slug}'); raise typer.Exit(code=1)
        typer.echo(provider.skills().get(audience, f'(no {audience} skill)'))

    @app.command('state')
    def state(slug: str = typer.Argument(..., help='API slug')):
        """Show an API's current state (the outbound 'state' surface)."""
        provider = registry.get(slug)
        if provider is None:
            typer.echo(f'no such API: {slug}'); raise typer.Exit(code=1)
        typer.echo(json.dumps(provider.state(), indent=2, default=str))

    @app.command('invoke')
    def invoke(slug: str = typer.Argument(..., help='API slug'),
               action: str = typer.Argument(..., help='action name, e.g. list_objects'),
               params: str = typer.Option('{}', '--params', help='JSON object of action params.')):
        """Invoke an action and print its result. (B3 will route this via the execution center.)"""
        provider = registry.get(slug)
        if provider is None:
            typer.echo(f'no such API: {slug}'); raise typer.Exit(code=1)
        result = provider.dispatch(action, json.loads(params))
        typer.echo(json.dumps(result.json(), indent=2, default=str))
        if not result.ok:
            raise typer.Exit(code=1)

    return app
