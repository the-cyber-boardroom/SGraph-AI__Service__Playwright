# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — s3 tui: S3_Browser__Render
# Generic S3 browser content as Rich-markup (+ plain variants for no-TTY). PURE — no
# textual, no rich import — testable on 3.11. Renders an entry list (buckets /
# folders / files) and one object's decoded preview. Object text is Rich-escaped so
# arbitrary file content can't open a markup tag.
# ═══════════════════════════════════════════════════════════════════════════════

from sgraph_ai_service_playwright__cli.aws.s3.tui.schemas.Schema__S3_Browser__View import Schema__S3_Browser__View

KIND_STYLE = {'bucket': 'magenta', 'folder': 'blue', 'file': 'default'}


def _esc(text : str) -> str:
    return text.replace('[', r'\[')


def human_size(n : int) -> str:
    if n < 1024:        return f'{n}B'
    if n < 1024 * 1024: return f'{n / 1024:.1f}KB'
    return f'{n / (1024 * 1024):.1f}MB'


def entries_markup(entries, selected_index : int = 0, title : str = '') -> str:
    lines = []
    lines.append(f'[bold]S3 Browser[/]   [cyan]{_esc(title) or "/"}[/]   [dim]({len(entries)})[/]')
    lines.append('[dim]↑/↓ select · Enter open · Esc up · r refresh · q quit[/]')
    lines.append('')
    if not entries:
        lines.append('  [dim](empty)[/]')
        return '\n'.join(lines)
    for i, e in enumerate(entries):
        marker = '[cyan]▸[/]' if i == selected_index else ' '
        style  = 'bold' if i == selected_index else KIND_STYLE.get(e.kind, 'default')
        if e.kind == 'file':
            lines.append(f' {marker} [{style}]{_esc(e.name)[:48].ljust(48)}[/] [dim]{human_size(e.size_bytes).rjust(9)}  {e.last_modified}[/]')
        else:
            lines.append(f' {marker} [{style}]{_esc(e.name)[:48].ljust(48)}[/] [dim]{e.kind}[/]')
    return '\n'.join(lines)


def entries_plain(entries, title : str = '') -> str:
    out = [f'S3 Browser   {title or "/"}   ({len(entries)})']
    if not entries:
        out.append('  (empty)')
        return '\n'.join(out)
    for e in entries:
        if e.kind == 'file':
            out.append(f'  {e.name[:48].ljust(48)} {human_size(e.size_bytes).rjust(9)}  {e.last_modified}')
        else:
            out.append(f'  {e.name[:48].ljust(48)} {e.kind}')
    return '\n'.join(out)


def object_markup(view : Schema__S3_Browser__View) -> str:
    lines = []
    flags = []
    if view.gunzipped: flags.append('gunzipped')
    if view.truncated: flags.append('truncated')
    flag = ('  [' + ', '.join(flags) + ']') if flags else ''
    lines.append(f'[bold]{_esc(view.key)}[/]   [dim]{human_size(view.size_bytes)} · {view.fmt}{flag}[/]')
    lines.append('[dim]Esc back · q quit[/]')
    lines.append('')
    if not view.text.strip():
        lines.append('  [dim](empty)[/]')
        return '\n'.join(lines)
    for line in view.text.split('\n'):
        lines.append(f'[dim]{_esc(line)}[/]')
    return '\n'.join(lines)


def object_plain(view : Schema__S3_Browser__View) -> str:
    head = f'{view.key}   {human_size(view.size_bytes)} · {view.fmt}'
    return head + '\n\n' + view.text
