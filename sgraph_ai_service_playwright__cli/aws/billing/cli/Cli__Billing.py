# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Cli__Billing
# Typer CLI surface for AWS Cost Explorer spend views.
#
# Command tree:
#   sg aws billing last-48h            — 2 daily buckets, by-service breakdown
#   sg aws billing week                — last 7 days, daily, by-service
#   sg aws billing mtd                 — month-to-date, daily, by-service
#   sg aws billing window <S> <E>      — explicit YYYY-MM-DD range
#   sg aws billing summary [verb]      — aggregated view across the window
#   sg aws billing chart   [verb]      — daily-totals ASCII bar chart
#
# Flags (all commands): --json, --top N, --metric, --group-by, --all-charges.
# Rich table output by default; --json for machine-readable output.
# ═══════════════════════════════════════════════════════════════════════════════

import typer
from rich.console import Console
from rich.table   import Table
from rich.panel   import Panel

from sg_compute.cli.base.Spec__CLI__Errors import spec_cli_errors

from sgraph_ai_service_playwright__cli.aws.billing.service.Billing__Window__Resolver import Billing__Window__Resolver
from sgraph_ai_service_playwright__cli.aws.billing.service.Billing__Report__Builder  import Billing__Report__Builder

billing_app = typer.Typer(name='billing', help='AWS Cost Explorer spend view.', no_args_is_help=True)

DEFAULT_TOP_N  = 10
DEFAULT_METRIC = 'UnblendedCost'

# ── Service name normalisation + emoji mapping ────────────────────────────────

SERVICE_DISPLAY = {                                                                    # Raw Cost Explorer name → short readable label
    'Amazon Elastic Compute Cloud - Compute' : 'EC2 Compute'              ,
    'EC2 - Other'                            : 'EC2 Other'                ,
    'Amazon Simple Storage Service'          : 'S3'                       ,
    'Amazon Virtual Private Cloud'           : 'VPC'                      ,
    'Amazon EC2 Container Registry (ECR)'    : 'ECR'                      ,
    'AmazonWorkMail'                         : 'WorkMail'                 ,
    'Amazon Kinesis Firehose'                : 'Kinesis Firehose'         ,
    'Amazon Kinesis'                         : 'Kinesis'                  ,
    'Amazon Route 53'                        : 'Route 53'                 ,
    'Amazon CloudFront'                      : 'CloudFront'               ,
    'AWS CloudTrail'                         : 'CloudTrail'               ,
    'AWS Lambda'                             : 'Lambda'                   ,
    'Amazon CloudWatch'                      : 'CloudWatch'               ,
    'AmazonCloudWatch'                       : 'CloudWatch'               ,
    'Amazon DynamoDB'                        : 'DynamoDB'                 ,
    'Amazon Relational Database Service'     : 'RDS'                      ,
    'Amazon Simple Notification Service'     : 'SNS'                      ,
    'Amazon Simple Queue Service'            : 'SQS'                      ,
    'AWS Identity and Access Management'     : 'IAM'                      ,
    'AWS Key Management Service'             : 'KMS'                      ,
    'AWS Secrets Manager'                    : 'Secrets Manager'          ,
    'AWS Step Functions'                     : 'Step Functions'           ,
    'Amazon API Gateway'                     : 'API Gateway'              ,
    'AWS Elemental MediaStore'               : 'MediaStore'               ,
    'Amazon OpenSearch Service'              : 'OpenSearch'               ,
    'Amazon Managed Grafana'                 : 'Managed Grafana'          ,
    'AWS Backup'                             : 'Backup'                   ,
    'AWS Config'                             : 'Config'                   ,
    'Tax'                                    : 'Tax'                      ,
    'OTHER'                                  : 'OTHER'                    ,
}

SERVICE_EMOJI = {                                                                      # Normalised display name → emoji
    'EC2 Compute'      : '🖥️',
    'EC2 Other'        : '🖧 ',
    'S3'               : '🪣',
    'VPC'              : '🕸️',
    'ECR'              : '📦',
    'WorkMail'         : '✉️',
    'Kinesis'          : '🌊',
    'Kinesis Firehose' : '🚒',
    'Route 53'         : '🧭',
    'CloudFront'       : '☁️',
    'CloudTrail'       : '📜',
    'Lambda'           : 'λ ',
    'CloudWatch'       : '👁️',
    'DynamoDB'         : '⚡',
    'RDS'              : '🗄️',
    'SNS'              : '📢',
    'SQS'              : '📬',
    'IAM'              : '🔐',
    'KMS'              : '🔑',
    'Secrets Manager'  : '🤫',
    'Step Functions'   : '🪜',
    'API Gateway'      : '🚪',
    'OpenSearch'       : '🔍',
    'Managed Grafana'  : '📈',
    'Backup'           : '💾',
    'Config'           : '⚙️',
    'Tax'              : '🏛️',
    'OTHER'            : '🧩',
}


def _display_name(service: str) -> str:                                                # Map Cost Explorer raw name to a short display label
    s = str(service)
    if s in SERVICE_DISPLAY:
        return SERVICE_DISPLAY[s]
    for prefix in ('Amazon ', 'AWS '):                                                 # Fallback — strip leading vendor prefix
        if s.startswith(prefix):
            return s[len(prefix):]
    return s or 'OTHER'


def _service_emoji(display_name: str) -> str:                                          # Emoji for a display name; falls back to a generic money symbol
    return SERVICE_EMOJI.get(display_name, '💵')


def _service_label(service: str, width: int = 22) -> str:                              # Combined emoji + name, padded to width (handles wide chars roughly)
    name  = _display_name(service)
    emoji = _service_emoji(name)
    return f'{emoji}  {name}'


# ── Bar-chart helpers ─────────────────────────────────────────────────────────

_BAR_FULL = '█'                                                                        # Solid block — used for both proportional and trend bars
_BAR_EIGHTHS = (' ', '▏', '▎', '▍', '▌', '▋', '▊', '▉', '█')                            # Sub-cell precision when a value lands mid-block


def _bar(value: float, max_value: float, width: int = 28) -> str:                      # Build an ASCII bar value/max wide; supports 1/8th-cell precision
    if max_value <= 0 or value <= 0:
        return ''
    ratio  = min(1.0, value / max_value)
    eighths = int(round(ratio * width * 8))
    full    = eighths // 8
    rem     = eighths % 8
    bar     = _BAR_FULL * full
    if rem and full < width:
        bar += _BAR_EIGHTHS[rem]
    return bar


def _amount_style(amount: float) -> str:                                               # Rich style by magnitude — quick visual scan
    if amount < 0     : return 'green'                                                 # Credits / refunds
    if amount == 0    : return 'dim'
    if amount < 0.10  : return 'dim'
    if amount < 1     : return ''
    if amount < 10    : return 'yellow'
    return 'bold red'


def _trend_arrow(curr: float, prev: float) -> str:                                     # Tiny trend indicator between adjacent days
    if prev <= 0:
        return ' '
    delta = (curr - prev) / prev
    if   delta >  0.20 : return '[red]↑[/]'
    elif delta < -0.20 : return '[green]↓[/]'
    else               : return '[dim]→[/]'


# ── Aggregation helpers ───────────────────────────────────────────────────────

def _aggregate_by_service(report) -> list:                                             # Sum every line_item across buckets → [(service, total), …] desc
    totals = {}
    for bucket in report.buckets:
        for item in bucket.line_items:
            svc = str(item.service)
            totals[svc] = totals.get(svc, 0.0) + float(item.amount_usd)
    return sorted(totals.items(), key=lambda kv: kv[1], reverse=True)


def _header_panel(c: Console, title: str, account_id: str, window_start: str,
                  window_end: str, total: float, day_count: int):                      # Rich Panel showing the run context
    avg = total / day_count if day_count else 0.0
    body = (f'💼 Account     : [bold]{account_id}[/]\n'
            f'📅 Window      : [bold]{window_start}[/] → [bold]{window_end}[/]  '
            f'({day_count} day{"" if day_count == 1 else "s"})\n'
            f'💰 Grand total : [bold]${total:,.2f}[/]\n'
            f'📊 Daily avg   : ${avg:,.2f}')
    c.print(Panel(body, title=f'[bold]{title}[/]', expand=False, border_style='cyan'))


# ── Shared report build path ──────────────────────────────────────────────────

def _build_report(keyword: str, start, end, metric: str, group_by: str,
                  top_n: int, all_charges: bool):                                      # Resolve window + call builder; returns (report, granularity)
    if keyword == 'window':
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
    return report, granularity


# ── Default view: daily breakdown with emojis + per-day bars ─────────────────

def _run_report(keyword: str, start, end, json_output: bool,
                top_n: int, metric: str, group_by: str,
                all_charges: bool = False):
    report, granularity = _build_report(keyword, start, end, metric, group_by, top_n, all_charges)

    if json_output:
        typer.echo(report.json())
        return

    c = Console(highlight=False)
    day_count = len(list(report.buckets))
    c.print()
    _header_panel(c, f'AWS Spend — {keyword}', report.account_id,
                  str(report.window.start), str(report.window.end),
                  float(report.total_usd), day_count)
    c.print()

    t = Table(box=None, show_header=True, padding=(0, 2))
    t.add_column('Date',    style='cyan', min_width=12, no_wrap=True)
    t.add_column('Service', style='',     min_width=24)
    t.add_column('USD',     style='',     justify='right', min_width=10)
    t.add_column('',        style='',     min_width=30)                                # Inline bar

    prev_bucket_total = None
    bucket_count      = 0
    for bucket in report.buckets:
        bucket_count += 1
        date_str   = str(bucket.date)
        items      = sorted(list(bucket.line_items),
                            key=lambda x: float(x.amount_usd), reverse=True)

        top_items = items[:top_n]
        other_sum = sum(float(i.amount_usd) for i in items[top_n:])

        bucket_max = max([float(i.amount_usd) for i in top_items] + [other_sum, 0.001])

        first = True
        for item in top_items:
            amount   = float(item.amount_usd)
            style    = _amount_style(amount)
            label    = _service_label(str(item.service))
            row_date = date_str if first else ''
            first    = False
            t.add_row(row_date,
                      label,
                      f'[{style}]{amount:>8,.2f}[/]' if style else f'{amount:>8,.2f}',
                      f'[dim]{_bar(amount, bucket_max)}[/]')

        if other_sum > 0.005:
            t.add_row('' if not first else date_str,
                      _service_label('OTHER'),
                      f'{other_sum:>8,.2f}',
                      f'[dim]{_bar(other_sum, bucket_max)}[/]')
            first = False

        if not top_items and other_sum <= 0.005:
            t.add_row(date_str, '[dim](no spend)[/]', '[dim]0.00[/]', '')

        trend = _trend_arrow(float(bucket.total_usd), prev_bucket_total) if prev_bucket_total is not None else ' '
        t.add_row('',
                  f'[bold]── Subtotal {date_str} {trend}[/]',
                  f'[bold]{float(bucket.total_usd):>8,.2f}[/]',
                  '')
        prev_bucket_total = float(bucket.total_usd)
        t.add_section()

    c.print(t)
    c.print()
    c.print(f'  💡 Tip: try [bold]sg aws billing summary {keyword}[/] for an aggregated view, '
            f'or [bold]sg aws billing chart {keyword}[/] for a daily trend chart.')
    c.print()


# ── summary view: services aggregated across the whole window ────────────────

def _run_summary(keyword: str, start, end, json_output: bool, top_n: int,
                 metric: str, group_by: str, all_charges: bool):
    report, granularity = _build_report(keyword, start, end, metric, group_by, top_n, all_charges)

    aggregated = _aggregate_by_service(report)                                         # [(raw_name, total), …]

    if json_output:                                                                    # Reuse the typed report; just emit it
        typer.echo(report.json())
        return

    c = Console(highlight=False)
    day_count   = len(list(report.buckets))
    grand_total = float(report.total_usd)
    c.print()
    _header_panel(c, f'AWS Spend Summary — {keyword}', report.account_id,
                  str(report.window.start), str(report.window.end),
                  grand_total, day_count)
    c.print()

    top   = aggregated[:top_n]
    other = sum(v for _, v in aggregated[top_n:])
    max_v = max([v for _, v in top] + [other, 0.001])

    t = Table(box=None, show_header=True, padding=(0, 2))
    t.add_column('Service', style='',     min_width=26)
    t.add_column('USD',     style='',     justify='right', min_width=10)
    t.add_column('Share',   style='dim',  justify='right', min_width=7 )
    t.add_column('',        style='',     min_width=34)
    for svc, amount in top:
        share = (amount / grand_total * 100) if grand_total else 0.0
        style = _amount_style(amount)
        t.add_row(_service_label(svc),
                  f'[{style}]{amount:>8,.2f}[/]' if style else f'{amount:>8,.2f}',
                  f'{share:5.1f}%',
                  f'[cyan]{_bar(amount, max_v, width=30)}[/]')
    if other > 0.005:
        share = (other / grand_total * 100) if grand_total else 0.0
        t.add_row(_service_label('OTHER'),
                  f'{other:>8,.2f}',
                  f'{share:5.1f}%',
                  f'[dim]{_bar(other, max_v, width=30)}[/]')
    t.add_section()
    t.add_row('[bold]── Total[/]',
              f'[bold]{grand_total:>8,.2f}[/]',
              '[bold]100.0%[/]', '')
    c.print(t)
    c.print()
    c.print(f'  💡 Tip: try [bold]sg aws billing chart {keyword}[/] for a daily trend chart.')
    c.print()


# ── chart view: ASCII bar chart of daily totals ──────────────────────────────

def _run_chart(keyword: str, start, end, json_output: bool, top_n: int,
               metric: str, group_by: str, all_charges: bool):
    report, granularity = _build_report(keyword, start, end, metric, group_by, top_n, all_charges)

    daily = [(str(b.date), float(b.total_usd)) for b in report.buckets]

    if json_output:
        typer.echo(report.json())
        return

    c = Console(highlight=False)
    day_count   = len(daily)
    grand_total = float(report.total_usd)
    c.print()
    _header_panel(c, f'AWS Daily Spend Chart — {keyword}', report.account_id,
                  str(report.window.start), str(report.window.end),
                  grand_total, day_count)
    c.print()

    if not daily:
        c.print('  [dim](no daily buckets returned)[/]\n')
        return

    max_v = max(v for _, v in daily) or 0.001
    avg_v = grand_total / day_count if day_count else 0.0
    peak_date, peak_val = max(daily, key=lambda kv: kv[1])
    low_date,  low_val  = min(daily, key=lambda kv: kv[1])

    t = Table(box=None, show_header=True, padding=(0, 2))
    t.add_column('Date',  style='cyan', min_width=12, no_wrap=True)
    t.add_column('USD',   style='',     justify='right', min_width=10)
    t.add_column('',      style='',     min_width=50)
    t.add_column('Mark',  style='dim',  min_width=12)

    prev = None
    for date_str, value in daily:
        style = _amount_style(value)
        bar   = _bar(value, max_v, width=46)
        marks = []
        if   date_str == peak_date : marks.append('[red]▲ peak[/]')
        elif date_str == low_date  : marks.append('[green]▼ low[/]')
        if prev is not None:
            marks.append(_trend_arrow(value, prev))
        prev = value
        t.add_row(date_str,
                  f'[{style}]{value:>8,.2f}[/]' if style else f'{value:>8,.2f}',
                  f'[cyan]{bar}[/]',
                  ' '.join(marks))

    c.print(t)
    c.print()

    # Stats footer
    stats = Table(box=None, show_header=False, padding=(0, 2))
    stats.add_column(style='dim',  no_wrap=True)
    stats.add_column(style='bold')
    stats.add_row('💰 Total          ', f'${grand_total:,.2f}')
    stats.add_row('📊 Daily average  ', f'${avg_v:,.2f}')
    stats.add_row('▲ Peak            ', f'${peak_val:,.2f}  on {peak_date}')
    stats.add_row('▼ Low             ', f'${low_val:,.2f}  on {low_date}')
    c.print(stats)
    c.print()


# ── Shared option blocks (kept inline for Typer signature compatibility) ─────
# Typer requires options to be declared at function signature time. Each
# command repeats the option list rather than sharing a helper, matching the
# DNS sub-package precedent.

def _common_options():
    """Documentation marker — see each command's signature for the real options."""
    pass


# ── Daily views ───────────────────────────────────────────────────────────────

@billing_app.command('last-48h')
@spec_cli_errors
def last_48h(json_output:  bool = typer.Option(False, '--json',         help='Output JSON instead of a table.'),
             top_n:        int  = typer.Option(DEFAULT_TOP_N, '--top',  help='Top N services per bucket (rest rolled into OTHER).'),
             metric:       str  = typer.Option(DEFAULT_METRIC, '--metric', help='Cost Explorer metric (UnblendedCost, BlendedCost, …).'),
             group_by:     str  = typer.Option('SERVICE', '--group-by', help='Dimension to group by.'),
             all_charges:  bool = typer.Option(False, '--all-charges',  help='Include credits, refunds and taxes (default: Usage only).')):
    """Last 48 hours of AWS spend (two daily buckets)."""
    _run_report('last-48h', None, None, json_output, top_n, metric, group_by, all_charges)


@billing_app.command('week')
@spec_cli_errors
def week(json_output:  bool = typer.Option(False, '--json',         help='Output JSON instead of a table.'),
         top_n:        int  = typer.Option(DEFAULT_TOP_N, '--top',  help='Top N services per bucket (rest rolled into OTHER).'),
         metric:       str  = typer.Option(DEFAULT_METRIC, '--metric', help='Cost Explorer metric.'),
         group_by:     str  = typer.Option('SERVICE', '--group-by', help='Dimension to group by.'),
         all_charges:  bool = typer.Option(False, '--all-charges',  help='Include credits, refunds and taxes.')):
    """Last 7 days of AWS spend."""
    _run_report('week', None, None, json_output, top_n, metric, group_by, all_charges)


@billing_app.command('mtd')
@spec_cli_errors
def mtd(json_output:  bool = typer.Option(False, '--json',         help='Output JSON instead of a table.'),
        top_n:        int  = typer.Option(DEFAULT_TOP_N, '--top',  help='Top N services per bucket.'),
        metric:       str  = typer.Option(DEFAULT_METRIC, '--metric', help='Cost Explorer metric.'),
        group_by:     str  = typer.Option('SERVICE', '--group-by', help='Dimension to group by.'),
        all_charges:  bool = typer.Option(False, '--all-charges',  help='Include credits, refunds and taxes.')):
    """Month-to-date AWS spend."""
    _run_report('mtd', None, None, json_output, top_n, metric, group_by, all_charges)


@billing_app.command('window')
@spec_cli_errors
def window(start:        str  = typer.Argument(..., help='Start date YYYY-MM-DD (inclusive).'),
           end:          str  = typer.Argument(..., help='End date YYYY-MM-DD (exclusive).'),
           json_output:  bool = typer.Option(False, '--json',         help='Output JSON instead of a table.'),
           top_n:        int  = typer.Option(DEFAULT_TOP_N, '--top',  help='Top N services per bucket.'),
           metric:       str  = typer.Option(DEFAULT_METRIC, '--metric', help='Cost Explorer metric.'),
           group_by:     str  = typer.Option('SERVICE', '--group-by', help='Dimension to group by.'),
           all_charges:  bool = typer.Option(False, '--all-charges',  help='Include credits, refunds and taxes.')):
    """Explicit date-range AWS spend."""
    _run_report('window', start, end, json_output, top_n, metric, group_by, all_charges)


# ── summary view (aggregated across the whole window) ────────────────────────

@billing_app.command('summary')
@spec_cli_errors
def summary(verb:         str  = typer.Argument('week', help='Window verb: last-48h | week | mtd.'),
            json_output:  bool = typer.Option(False, '--json',         help='Output JSON instead of a table.'),
            top_n:        int  = typer.Option(DEFAULT_TOP_N, '--top',  help='Top N services (rest rolled into OTHER).'),
            metric:       str  = typer.Option(DEFAULT_METRIC, '--metric', help='Cost Explorer metric.'),
            group_by:     str  = typer.Option('SERVICE', '--group-by', help='Dimension to group by.'),
            all_charges:  bool = typer.Option(False, '--all-charges',  help='Include credits, refunds and taxes.')):
    """Aggregated spend across the window — services sorted by total, with share % and bars."""
    _run_summary(verb, None, None, json_output, top_n, metric, group_by, all_charges)


# ── chart view (daily-totals ASCII bar chart) ────────────────────────────────

@billing_app.command('chart')
@spec_cli_errors
def chart(verb:         str  = typer.Argument('week', help='Window verb: last-48h | week | mtd.'),
          json_output:  bool = typer.Option(False, '--json',         help='Output JSON instead of a table.'),
          top_n:        int  = typer.Option(DEFAULT_TOP_N, '--top',  help='Top N services per bucket (unused in chart but kept for builder symmetry).'),
          metric:       str  = typer.Option(DEFAULT_METRIC, '--metric', help='Cost Explorer metric.'),
          group_by:     str  = typer.Option('SERVICE', '--group-by', help='Dimension to group by.'),
          all_charges:  bool = typer.Option(False, '--all-charges',  help='Include credits, refunds and taxes.')):
    """Daily-totals ASCII bar chart across the window — quick visual trend."""
    _run_chart(verb, None, None, json_output, top_n, metric, group_by, all_charges)
