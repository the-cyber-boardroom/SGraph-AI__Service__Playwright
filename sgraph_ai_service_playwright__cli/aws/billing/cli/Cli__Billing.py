# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Cli__Billing
# Typer CLI surface for AWS Cost Explorer spend views.
#
# Command tree:
#   sg aws billing last-48h            — 2 daily buckets, by-service breakdown
#   sg aws billing week                — last 7 days, daily, by-service
#   sg aws billing mtd                 — month-to-date, daily, by-service
#   sg aws billing window <S> <E>      — explicit YYYY-MM-DD range
#
# Flags (all commands): --json, --top N, --metric, --group-by.
# Rich table output by default; --json for machine-readable output.
# ═══════════════════════════════════════════════════════════════════════════════

import json
import sys

import typer
from rich.console import Console
from rich.table   import Table

from sg_compute.cli.base.Spec__CLI__Errors import spec_cli_errors

from sgraph_ai_service_playwright__cli.aws.billing.enums.Enum__Billing__Granularity  import Enum__Billing__Granularity
from sgraph_ai_service_playwright__cli.aws.billing.enums.Enum__Billing__Metric        import Enum__Billing__Metric
from sgraph_ai_service_playwright__cli.aws.billing.enums.Enum__Billing__Group_By      import Enum__Billing__Group_By
from sgraph_ai_service_playwright__cli.aws.billing.service.Billing__Window__Resolver  import Billing__Window__Resolver
from sgraph_ai_service_playwright__cli.aws.billing.service.Billing__Report__Builder   import Billing__Report__Builder

billing_app = typer.Typer(name='billing', help='AWS Cost Explorer spend view.', no_args_is_help=True)

DEFAULT_TOP_N  = 10
DEFAULT_METRIC = 'UnblendedCost'


def _run_report(keyword: str, start, end, json_output: bool,
                top_n: int, metric: str, group_by: str,
                all_charges: bool = False):                                           # Shared body: resolve window, call builder, emit table or JSON
    if keyword == 'window':                                                            # Explicit range — use the caller's start/end, daily granularity
        granularity = 'DAILY'
    else:
        start, end, granularity = Billing__Window__Resolver().resolve(keyword)

    try:
        report = Billing__Report__Builder().build(
            start        = start       ,
            end          = end         ,
            granularity  = granularity ,
            keyword      = keyword     ,
            metric       = metric      ,
            group_by_key = group_by    ,
            top_n        = top_n       ,
            all_charges  = all_charges ,
        )
    except RuntimeError as e:
        typer.echo(str(e), err=True)
        raise typer.Exit(2)

    if json_output:
        typer.echo(report.json())
        return

    c = Console(highlight=False)
    c.print()
    c.print(f'  AWS Spend — {keyword}  ·  account {report.account_id}  ·  metric: {metric}')
    c.print()

    t = Table(box=None, show_header=True, padding=(0, 2))
    t.add_column('Date',    style='cyan', min_width=12, no_wrap=True)
    t.add_column('Service', style='',     min_width=30)
    t.add_column('USD',     style='',     min_width=10)

    for bucket in report.buckets:
        date_str   = str(bucket.date)
        items      = list(bucket.line_items)                                          # list of Schema__Billing__Line_Item
        items_sorted = sorted(items, key=lambda x: float(x.amount_usd), reverse=True)

        top_items  = items_sorted[:top_n]
        other_sum  = sum(float(i.amount_usd) for i in items_sorted[top_n:])

        first = True
        for item in top_items:
            row_date = date_str if first else ''
            first    = False
            t.add_row(row_date, str(item.service), f'{float(item.amount_usd):.2f}')

        if other_sum > 0:
            row_date = date_str if first else ''
            t.add_row(row_date, 'OTHER', f'{other_sum:.2f}')
            first = False

        if not top_items and other_sum == 0:                                          # Empty day — Cost Explorer returned no groups (e.g. zero spend)
            t.add_row(date_str, '(no spend)', '0.00')

        subtotal_label = date_str if first else ''                                    # Subtotal row for the bucket
        t.add_row(subtotal_label, f'[bold]Subtotal {date_str}[/]',
                  f'[bold]{float(bucket.total_usd):.2f}[/]')

    c.print(t)
    c.print()
    c.print(f'  [bold]Grand total: USD {float(report.total_usd):.2f}[/]  '
            f'[dim]({report.window.start} – {report.window.end}, {granularity})[/]')
    c.print()


@billing_app.command('last-48h')
@spec_cli_errors
def last_48h(json_output:  bool = typer.Option(False, '--json',         help='Output JSON instead of a table.'),
             top_n:        int  = typer.Option(DEFAULT_TOP_N, '--top',  help='Top N services per bucket (rest rolled into OTHER).'),
             metric:       str  = typer.Option(DEFAULT_METRIC, '--metric', help='Cost Explorer metric (UnblendedCost, BlendedCost, …).'),
             group_by:     str  = typer.Option('SERVICE', '--group-by', help='Dimension to group by (SERVICE, USAGE_TYPE, REGION, …).'),
             all_charges:  bool = typer.Option(False, '--all-charges',  help='Include credits, refunds and taxes (default: Usage only).')):
    """Last 48 hours of AWS spend (two daily buckets)."""
    _run_report('last-48h', None, None, json_output, top_n, metric, group_by, all_charges)


@billing_app.command('week')
@spec_cli_errors
def week(json_output:  bool = typer.Option(False, '--json',         help='Output JSON instead of a table.'),
         top_n:        int  = typer.Option(DEFAULT_TOP_N, '--top',  help='Top N services per bucket (rest rolled into OTHER).'),
         metric:       str  = typer.Option(DEFAULT_METRIC, '--metric', help='Cost Explorer metric (UnblendedCost, BlendedCost, …).'),
         group_by:     str  = typer.Option('SERVICE', '--group-by', help='Dimension to group by (SERVICE, USAGE_TYPE, REGION, …).'),
         all_charges:  bool = typer.Option(False, '--all-charges',  help='Include credits, refunds and taxes (default: Usage only).')):
    """Last 7 days of AWS spend."""
    _run_report('week', None, None, json_output, top_n, metric, group_by, all_charges)


@billing_app.command('mtd')
@spec_cli_errors
def mtd(json_output:  bool = typer.Option(False, '--json',         help='Output JSON instead of a table.'),
        top_n:        int  = typer.Option(DEFAULT_TOP_N, '--top',  help='Top N services per bucket (rest rolled into OTHER).'),
        metric:       str  = typer.Option(DEFAULT_METRIC, '--metric', help='Cost Explorer metric (UnblendedCost, BlendedCost, …).'),
        group_by:     str  = typer.Option('SERVICE', '--group-by', help='Dimension to group by (SERVICE, USAGE_TYPE, REGION, …).'),
        all_charges:  bool = typer.Option(False, '--all-charges',  help='Include credits, refunds and taxes (default: Usage only).')):
    """Month-to-date AWS spend."""
    _run_report('mtd', None, None, json_output, top_n, metric, group_by, all_charges)


@billing_app.command('window')
@spec_cli_errors
def window(start:        str  = typer.Argument(..., help='Start date YYYY-MM-DD (inclusive).'),
           end:          str  = typer.Argument(..., help='End date YYYY-MM-DD (exclusive).'),
           json_output:  bool = typer.Option(False, '--json',         help='Output JSON instead of a table.'),
           top_n:        int  = typer.Option(DEFAULT_TOP_N, '--top',  help='Top N services per bucket (rest rolled into OTHER).'),
           metric:       str  = typer.Option(DEFAULT_METRIC, '--metric', help='Cost Explorer metric (UnblendedCost, BlendedCost, …).'),
           group_by:     str  = typer.Option('SERVICE', '--group-by', help='Dimension to group by (SERVICE, USAGE_TYPE, REGION, …).'),
           all_charges:  bool = typer.Option(False, '--all-charges',  help='Include credits, refunds and taxes (default: Usage only).')):
    """Explicit date-range AWS spend."""
    _run_report('window', start, end, json_output, top_n, metric, group_by, all_charges)
