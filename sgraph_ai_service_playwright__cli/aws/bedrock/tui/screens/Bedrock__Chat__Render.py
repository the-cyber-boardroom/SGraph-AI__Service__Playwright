# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — bedrock tui: Bedrock__Chat__Render
# PURE content for the chat view — no textual, no rich import — testable on 3.11.
# Builds the per-turn cost footer, the session cost-meter markup (with a budget bar),
# and the Nova model-picker rows. Colour names are Rich style tokens the widgets pass
# through; cost colour is semantic (green/amber/red against the budget).
# ═══════════════════════════════════════════════════════════════════════════════

from sgraph_ai_service_playwright__cli.aws.bedrock.tui.bedrock_chat_tui__config import (BUDGET_WARN_FRACTION,
                                                                                        BUDGET_OVER_FRACTION)


def budget_fraction(total_cost_usd: float, budget_usd: float) -> float:
    if budget_usd <= 0:
        return 0.0
    return total_cost_usd / budget_usd


def cost_colour(fraction: float) -> str:
    if fraction >= BUDGET_OVER_FRACTION:
        return 'red'
    if fraction >= BUDGET_WARN_FRACTION:
        return 'yellow'
    return 'green'


def turn_footer(input_tokens: int, output_tokens: int, cost_usd: float, latency_ms: int) -> str:
    return (f'[dim]in {input_tokens} · out {output_tokens} · '
            f'[/][green]${cost_usd:.6f}[/][dim] · {latency_ms}ms[/]')


def streaming_footer() -> str:
    return '[dim]⟳ streaming…[/]'


def _bar(fraction: float, width: int = 16) -> str:
    fraction = max(0.0, min(1.0, fraction))
    filled   = int(round(fraction * width))
    return '▓' * filled + '░' * (width - filled)


def cost_meter_markup(session) -> str:
    frac   = budget_fraction(session.total_cost_usd, session.budget_usd)
    colour = cost_colour(frac)
    lines  = [f'[bold]session[/]',
              f'[dim]model[/]  {session.model_alias}',
              f'[dim]region[/] {session.region or "—"}',
              f'[dim]turns[/]  {session.turn_count}',
              '']

    # last request — exact tokens/cost of the most recent turn
    if session.turns:
        t   = session.turns[-1]
        tot = t.input_tokens + t.output_tokens
        lines += [f'[bold]last request[/]',
                  f'[dim]  in [/] {t.input_tokens}',
                  f'[dim]  out[/] {t.output_tokens}',
                  f'[dim]  tot[/] {tot}',
                  f'[dim]  $  [/] [green]${t.cost_usd:.6f}[/] [dim]· {t.latency_ms}ms[/]',
                  '']

    # session totals
    sess_tot = session.total_input_tokens + session.total_output_tokens
    lines += [f'[bold]session Σ[/]',
              f'[dim]  in [/] {session.total_input_tokens}',
              f'[dim]  out[/] {session.total_output_tokens}',
              f'[dim]  tot[/] {sess_tot}',
              f'[dim]  $  [/] [{colour}]${session.total_cost_usd:.6f}[/]',
              '',
              f'[dim]budget[/] ${session.budget_usd:.2f}',
              f'  [{colour}]{_bar(frac)}[/] {frac * 100:.1f}%']
    if session.context_label:
        lines += ['', f'[dim]context[/]', f'  {session.context_label}', '  [dim][SEEDED][/]']
    return '\n'.join(lines)


def model_picker_rows(aliases: list, pricing_for, resolve) -> list:
    # → list of (alias, model_id, in_price, out_price) ; aliases includes 'default' first
    rows = []
    for alias in aliases:
        model_id        = resolve(alias)
        in_price, out_p = pricing_for(model_id)
        rows.append((alias, model_id, in_price, out_p))
    return rows
