# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — cf tui: CF_TUI__Inspector__Render
# Field Lineage Inspector content as Rich-markup (and a plain variant for no-TTY).
# PURE — no textual, no rich import — so it is testable on 3.11. Shows one record's
# fields grouped RAW / DERIVED / LINEAGE / PIPELINE; RAW rows that the transform
# changed show "raw → value" with the value highlighted, so the parse/derive/classify
# steps are visible at a glance. Everything traces to the parsed record.
# ═══════════════════════════════════════════════════════════════════════════════

from sgraph_ai_service_playwright__cli.elastic.lets.cf.tui.schemas.Schema__CF_TUI__Record_View import Schema__CF_TUI__Record_View

GROUPS = ('RAW', 'DERIVED', 'LINEAGE', 'PIPELINE')
CHAIN  = 'parse → url-decode UA/referer → status_class → cache_hit → Bot__Classifier → stamp lineage'


def _esc(text : str) -> str:
    return text.replace('[', r'\[')


def _cap(text : str, n : int) -> str:
    return text if len(text) <= n else text[:n - 1] + '…'


def inspector_markup(view : Schema__CF_TUI__Record_View) -> str:
    lines    = []
    basename = view.key.rsplit('/', 1)[-1] or '(record)'
    lines.append(f'[bold]Field Lineage[/]   [cyan]{_esc(basename)}[/]  [dim]line {view.line_index} · {view.doc_id}[/]')
    if not view.valid:
        lines.append(f'[yellow]could not parse[/] — {view.column_count} TSV columns (expected 26)')
        if view.raw_line:
            lines.append(f'[dim]{_esc(_cap(view.raw_line, 240))}[/]')
        return '\n'.join(lines)
    lines.append('[dim]raw → transformed · changed values highlighted · Esc back · q quit[/]')

    for group in GROUPS:
        rows = [f for f in view.fields if f.group == group]
        if not rows:
            continue
        lines.append('')
        lines.append(f'[bold]{group}[/]  ({len(rows)})')
        for f in rows:
            name = _esc(f.name[:20]).ljust(20)
            if f.group == 'RAW' and f.changed:
                raw = _esc(_cap(f.raw, 30)) or '[dim]-[/]'
                lines.append(f'  {name} [dim]{raw}[/] [cyan]→[/] [green]{_esc(_cap(f.value, 40))}[/]')
            elif f.group == 'RAW':
                lines.append(f'  {name} {_esc(_cap(f.value, 40))}')
            else:
                value = _esc(_cap(f.value, 40)) or '[dim](empty)[/]'
                lines.append(f'  {name} [green]{value}[/]')

    lines.append('')
    lines.append(f'[dim]transform: {CHAIN}[/]')
    return '\n'.join(lines)


def inspector_plain(view : Schema__CF_TUI__Record_View) -> str:
    out      = []
    basename = view.key.rsplit('/', 1)[-1] or '(record)'
    out.append(f'Field Lineage   {basename}  line {view.line_index} · {view.doc_id}')
    if not view.valid:
        out.append(f'could not parse — {view.column_count} TSV columns (expected 26)')
        return '\n'.join(out)
    for group in GROUPS:
        rows = [f for f in view.fields if f.group == group]
        if not rows:
            continue
        out.append(f'{group} ({len(rows)})')
        for f in rows:
            if f.group == 'RAW' and f.changed:
                out.append(f'  {f.name[:20].ljust(20)} {_cap(f.raw, 30)} -> {_cap(f.value, 40)}')
            elif f.group == 'RAW':
                out.append(f'  {f.name[:20].ljust(20)} {_cap(f.value, 40)}')
            else:
                out.append(f'  {f.name[:20].ljust(20)} {_cap(f.value, 40)}')
    out.append(f'transform: {CHAIN}')
    return '\n'.join(out)
