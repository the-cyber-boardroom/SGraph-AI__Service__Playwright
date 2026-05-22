# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tui/tool_api/screens: Tui_Api__Explorer__Render
# Pure markup helpers for the explorer (no textual import) — testable on any runtime.
# The Textual screen (Tui_Api__Explorer) is a thin shell over these.
# ═══════════════════════════════════════════════════════════════════════════════

import json

from osbot_utils.type_safe.Type_Safe import Type_Safe


class Tui_Api__Explorer__Render(Type_Safe):

    def action_rows(self, registry) -> list:                                      # [(slug, action_name, tier, description)]
        rows = []
        for slug in registry.list_slugs():
            for action in registry.get(slug).manifest().actions:
                rows.append((slug, str(action.name), str(action.tier), action.description))
        return rows

    def action_detail_markup(self, slug: str, action) -> str:
        return '\n'.join([f'[b]{slug} · {action.name}[/b]',
                          f'tier  {action.tier}    scope  {action.scope.api}:{action.scope.capability}',
                          '',
                          '[dim]input schema[/dim]',
                          json.dumps(action.input_schema, indent=2)])

    def result_markup(self, result) -> str:
        if result.ok:
            return '[green]ok[/green]\n' + json.dumps(result.json().get('data', {}), indent=2, default=str)
        if result.dry_run:
            return '[yellow]dry-run / gated[/yellow]\n' + (result.error or '') + '\n' + json.dumps(result.preview, indent=2, default=str)
        return '[red]error[/red]\n' + (result.error or '')
