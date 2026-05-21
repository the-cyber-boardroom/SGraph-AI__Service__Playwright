# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — sg_edge tui: SG_Edge__TUI__Slug_Detail__Render
# Screen 4 (Slug detail) content. PURE (no textual) → testable on 3.11. STATE + DNS
# are real (derived from the snapshot's slug state + backend); INSTANCE / COST /
# ACTIVITY / VAULT-BINDING are labelled pending (Slice 5 / Phase 2 / observability) —
# never fabricated. A `styled` flag yields markup (Textual) or plain (no-TTY).
# ═══════════════════════════════════════════════════════════════════════════════

import datetime

from sg_compute_specs.sg_edge.tui.enums.Enum__SG_Edge__TUI__Slug_State              import Enum__SG_Edge__TUI__Slug_State
from sg_compute_specs.sg_edge.tui.schemas.Schema__SG_Edge__TUI__Snapshot            import Schema__SG_Edge__TUI__Snapshot
from sg_compute_specs.sg_edge.tui.screens.widgets.SG_Edge__TUI__Glyphs              import slug_glyph, yes_no

LIVE    = Enum__SG_Edge__TUI__Slug_State.LIVE
DORMANT = Enum__SG_Edge__TUI__Slug_State.DORMANT
ORPHAN  = Enum__SG_Edge__TUI__Slug_State.ORPHAN_BACKEND


def slug_detail_markup(snapshot : Schema__SG_Edge__TUI__Snapshot, slug_name : str) -> str:
    return _render(snapshot, slug_name, styled=True)


def slug_detail_plain(snapshot : Schema__SG_Edge__TUI__Snapshot, slug_name : str) -> str:
    return _render(snapshot, slug_name, styled=False)


def _render(snapshot, slug_name : str, styled : bool) -> str:
    names = [s.slug for s in snapshot.slugs]
    stamp = datetime.datetime.fromtimestamp(int(snapshot.captured_at), datetime.timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')
    lines = []

    if not snapshot.slugs:
        lines.append(_b('SG/Edge Slug Detail', styled))
        lines.append('')
        lines.append(_dim('no slugs registered — register one with `sg edge local register <slug>`', styled))
        return '\n'.join(lines)

    if slug_name not in names:
        lines.append(_b('SG/Edge Slug Detail', styled))
        lines.append('')
        lines.append(_dim(f'slug not found: {slug_name or "(none)"}  —  known: {", ".join(names)}', styled))
        return '\n'.join(lines)

    slug    = snapshot.slugs[names.index(slug_name)]
    index   = names.index(slug_name)
    glyph, style = slug_glyph(slug.state)
    has_a   = slug.state in (LIVE, DORMANT)
    has_txt = slug.state in (LIVE, ORPHAN)
    backend = f'{slug.backend_ip}:{slug.backend_port}' if has_txt and slug.backend_ip else '—'

    lines.append(f'{_b("SLUG: " + slug.slug, styled)}   {_dim(f"({index + 1} of {len(names)} — ↑/↓ to switch)", styled)}')
    lines.append(_dim(f'{stamp}   target={snapshot.target}  parent={snapshot.parent}', styled))
    lines.append('')

    lines.append(_b('STATE', styled))
    lines.append(f'  {_wrap(glyph, style, styled)} {slug.state}')
    lines.append(f'  fqdn:     {slug.fqdn}')
    lines.append(f'  started:  {_dim("pending Slice 5", styled)}')
    lines.append(f'  cost:     {_dim("pending Slice 5", styled)}')
    lines.append('')

    ag, asy = yes_no(has_a)
    tg, tsy = yes_no(has_txt)
    lines.append(_b('DNS', styled))
    lines.append(f'  {_wrap(ag, asy, styled)} A record      {slug.fqdn}')
    lines.append(f'  {_wrap(tg, tsy, styled)} TXT (backend) {backend}')
    lines.append('')

    lines.append(_b('INSTANCE', styled))
    lines.append(f'  {_dim("pending Slice 5 — id / type / AZ / IP / health (no EC2 launcher wired)", styled)}')
    lines.append('')

    lines.append(_b('VAULT BINDING', styled))
    lines.append(f'  backend:  {backend}')
    lines.append(f'  {_dim("source / article / working vaults: pending Phase 2 (Vault Waker)", styled)}')
    lines.append('')

    lines.append(_b('ACTIVITY (last 5m)', styled))
    lines.append(f'  {_dim("requests / errors / latency: pending observability (Slice 5/6)", styled)}')
    return '\n'.join(lines)


def _wrap(text : str, style : str, styled : bool) -> str:
    return f'[{style}]{text}[/]' if styled else text


def _b(text : str, styled : bool) -> str:
    return f'[bold]{text}[/]' if styled else text


def _dim(text : str, styled : bool) -> str:
    return f'[dim]{text}[/]' if styled else text
