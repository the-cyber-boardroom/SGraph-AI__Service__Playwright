# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tui/tool_api: Cli__Tui_Api
# Builds the generic `tui api` Typer sub-group from a registry. Each host attaches it
# under its `tui` group so `sg <area> tui api list/describe/skills/state/invoke` work.
# The same registry + dispatch the chat and the explorer use — one source of truth.
# ═══════════════════════════════════════════════════════════════════════════════

import json

import typer

from sgraph_ai_service_playwright__cli.tui.tool_api.enums.Enum__Tui_Api__Exec_Mode      import Enum__Tui_Api__Exec_Mode
from sgraph_ai_service_playwright__cli.tui.tool_api.service.Tui_Api__Execution_Center   import Tui_Api__Execution_Center
from sgraph_ai_service_playwright__cli.tui.tool_api.service.Tui_Api__Registry           import Tui_Api__Registry


def make_tui_api_app(registry: Tui_Api__Registry) -> typer.Typer:
    app    = typer.Typer(name='api', help='TUI API: discover + invoke this area\'s actions.', no_args_is_help=True)
    center = Tui_Api__Execution_Center(registry=registry)                         # every invoke is gated + audited here

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
               params: str = typer.Option('{}', '--params', help='JSON object of action params.'),
               dry_run: bool = typer.Option(False, '--dry-run', help='Preview a mutation without committing.')):
        """Invoke an action through the execution center (sequencing → params → mutation gate → audit)."""
        if registry.get(slug) is None:
            typer.echo(f'no such API: {slug}'); raise typer.Exit(code=1)
        center.mode = Enum__Tui_Api__Exec_Mode.DRY_RUN if dry_run else Enum__Tui_Api__Exec_Mode.AUTO
        result = center.execute(slug, action, json.loads(params),
                                on_confirm=lambda a, p, preview: typer.confirm(f'Run {a.name} [{a.tier}]?', default=False))
        typer.echo(json.dumps(result.json(), indent=2, default=str))
        if not result.ok:
            raise typer.Exit(code=1)

    @app.command('status')
    def status(slug: str = typer.Argument(..., help='API slug')):
        """Orientation: 'now what?' — health, currently-available actions, recent changes."""
        provider = registry.get(slug)
        if provider is None:
            typer.echo(f'no such API: {slug}'); raise typer.Exit(code=1)
        orientation = provider.orientation()
        out = {'tool'             : orientation.tool,
               'status'           : orientation.status,
               'available_actions': [str(action.name) for action in center.available_actions(slug)],
               'recent_changes'   : [change.json() for change in orientation.recent_changes]}
        typer.echo(json.dumps(out, indent=2, default=str))

    @app.command('whatsnew')
    def whatsnew(slug: str = typer.Argument(..., help='API slug')):
        """Highlights since last visit (rendered from the provider's change log)."""
        provider = registry.get(slug)
        if provider is None:
            typer.echo(f'no such API: {slug}'); raise typer.Exit(code=1)
        from sgraph_ai_service_playwright__cli.tui.tool_api.service.Tui_Api__Change_Log import Tui_Api__Change_Log
        typer.echo(Tui_Api__Change_Log(changes=provider.orientation().recent_changes).whatsnew_markdown())

    @app.command('changelog')
    def changelog(slug: str = typer.Argument(..., help='API slug')):
        """Full structured change history for an API."""
        provider = registry.get(slug)
        if provider is None:
            typer.echo(f'no such API: {slug}'); raise typer.Exit(code=1)
        from sgraph_ai_service_playwright__cli.tui.tool_api.service.Tui_Api__Change_Log import Tui_Api__Change_Log
        typer.echo(Tui_Api__Change_Log(changes=provider.orientation().recent_changes).changelog_markdown())

    @app.command('explore')
    def explore():
        """Launch the Swagger-style TUI API explorer (Textual)."""
        from sgraph_ai_service_playwright__cli.tui.tool_api.screens.Tui_Api__Explorer import Tui_Api__Explorer
        Tui_Api__Explorer(registry=registry).run()

    return app
