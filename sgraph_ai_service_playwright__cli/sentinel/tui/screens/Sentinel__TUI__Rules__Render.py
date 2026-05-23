# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Sentinel__TUI__Rules__Render
# Rules surface content as Rich-markup strings. PURE — no textual, no rich import —
# so it is unit-testable on 3.11; the Textual screen drops the markup into a Static.
# Shows the six tiny-core rules and a selected rule's detail (schema-shaped metadata).
# ═══════════════════════════════════════════════════════════════════════════════


def _action_style(action: str) -> str:
    return 'green' if action == 'pass' else 'red'


def rules_markup(rules, selected_index: int = 0) -> str:
    lines = ['[bold]SG/Sentinel — Rules[/]  [dim](tiny core; logic in sentinel_l1.js)[/]', '']
    lines.append('  [dim]ID    NAME                ACTION       LAYER  ATTACK[/]')
    for i, rule in enumerate(rules):
        marker = '[reverse]▸[/]' if i == selected_index else ' '
        style  = _action_style(rule.action.value)
        lines.append(f'{marker} [cyan]{str(rule.rule_id):<5}[/] {str(rule.name):<19} '
                     f'[{style}]{rule.action.value:<11}[/] {rule.layer.value:<5}  {str(rule.attack_tag) or "—"}')
    if not rules:
        lines.append('  [dim](no rules)[/]')
    lines += ['', '[dim][↑/↓] select   [enter] detail   [r] refresh   [?] help   [q] quit[/]']
    return '\n'.join(lines)


def rule_detail_markup(rule) -> str:
    if rule is None:
        return '[red]no such rule[/]'
    style = _action_style(rule.action.value)
    return '\n'.join([
        f'[bold]Rule {rule.rule_id} — {rule.name}[/]',
        '',
        f'  layer        {rule.layer.value}',
        f'  action       [{style}]{rule.action.value}[/]',
        f'  confidence   {rule.confidence}',
        f'  attack_tag   {str(rule.attack_tag) or "—"}  [dim](MITRE ATT&CK)[/]',
        '',
        '  [bold]schema in[/]   captured request: { method, path, host, source_ip, … }',
        '  [bold]schema out[/]  { verdict: allow|block, reason, rule_id, action }',
        '',
        f'  [dim]{rule.description}[/]',
        '',
        '[dim][esc] back   [q] quit[/]',
    ])


def rules_plain(rules) -> str:                                                       # no-TTY fallback
    out = ['SG/Sentinel rules:']
    for rule in rules:
        out.append(f'  {rule.rule_id}  {rule.name:<19} {rule.action.value:<11} {rule.layer.value}  {rule.attack_tag}')
    return '\n'.join(out)
