# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI aws/lab — Render__Table
# Rich-based generic renderer for Schema__Lab__Run__Result.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe

from sgraph_ai_service_playwright__cli.aws.lab.schemas.Schema__Lab__Run__Result import Schema__Lab__Run__Result


class Render__Table(Type_Safe):

    def render(self, result: Schema__Lab__Run__Result) -> None:
        from rich.console import Console
        from rich.table   import Table

        console = Console()
        table   = Table(title=f'Lab Run: {result.run_id}', show_header=True, header_style='bold cyan')
        table.add_column('Status',      style='bold')
        table.add_column('Duration ms', justify='right')
        table.add_column('Started')
        table.add_column('Error')

        status_color = 'green' if str(result.status) == 'ok' else 'red'
        table.add_row(
            f'[{status_color}]{str(result.status)}[/{status_color}]',
            str(int(result.duration_ms)),
            result.started_at[:19] if result.started_at else '',
            result.error or '',
        )
        console.print(table)

        if result.samples:
            s_table = Table(title='Timing Samples', show_header=True, header_style='bold blue')
            s_table.add_column('Label')
            s_table.add_column('ms', justify='right')
            s_table.add_column('OK', justify='center')
            s_table.add_column('Detail')
            for s in result.samples:
                ok_str = '[green]✓[/green]' if s.success else '[red]✗[/red]'
                s_table.add_row(s.label, str(int(s.elapsed_ms)), ok_str, s.detail or '')
            console.print(s_table)
