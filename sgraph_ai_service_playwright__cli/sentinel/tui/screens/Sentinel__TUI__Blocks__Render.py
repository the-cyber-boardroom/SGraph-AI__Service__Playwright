# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Sentinel__TUI__Blocks__Render
# Blocks surface (use case 2): blocked requests grouped by reason/rule with counts,
# plus the block-action breakdown. PURE — no textual/rich import; testable on 3.11.
# ═══════════════════════════════════════════════════════════════════════════════


def blocks_markup(groups, total: int) -> str:
    lines = ['[bold]SG/Sentinel — Blocks[/]  [dim](use case 2: obvious-bad blocking)[/]',
             f'[dim]total blocks: {total}[/]', '']
    lines.append('  [dim]REASON                          COUNT   LAYER  RULE   ACTION[/]')
    for g in groups:
        lines.append(f'  [red]{str(g.reason):<31}[/] {g.count:>5}   {g.layer.value:<5}  '
                     f'[cyan]{str(g.rule_id):<5}[/]  {g.action.value}')
    if not groups:
        lines.append('  [dim](no blocks recorded)[/]')

    drop    = sum(g.count for g in groups if g.action.value == 'drop_403')
    deflect = sum(g.count for g in groups if g.action.value == 'deflect_404')
    lines += ['', '[bold]BLOCK ACTIONS[/]',
              f'  Dropped (403)    {drop}',
              f'  Deflected (404)  {deflect}']
    lines += ['', '[dim][r] refresh   [?] help   [q] quit[/]']
    return '\n'.join(lines)


def blocks_plain(groups, total: int) -> str:                                         # no-TTY fallback
    out = [f'SG/Sentinel blocks (total {total}):']
    for g in groups:
        out.append(f'  {g.reason:<31} {g.count:>5}  {g.layer.value}  {g.rule_id}  {g.action.value}')
    if not groups:
        out.append('  (no blocks)')
    return '\n'.join(out)
