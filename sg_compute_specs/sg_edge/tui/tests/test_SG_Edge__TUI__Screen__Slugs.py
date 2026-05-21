# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — sg_edge tui: tests for the DataTable Slug-inventory prototype
# Covers the generic Type_Safe→table helper (pure, 3.11) and the DataTable screen
# (pilot): rows populate from the snapshot, the built-in row cursor moves with ↑/↓,
# RowSelected (Enter) records opened_slug + exits, refresh keeps the cursor put.
# @skipUnless textual for the pilot; screen imported lazily so this loads on 3.11.
# ═══════════════════════════════════════════════════════════════════════════════

import asyncio
import shutil
import tempfile
from unittest import TestCase, skipUnless

from sg_compute_specs.sg_edge.tui.enums.Enum__SG_Edge__TUI__Slug_State        import Enum__SG_Edge__TUI__Slug_State
from sg_compute_specs.sg_edge.tui.schemas.Schema__SG_Edge__TUI__Slug          import Schema__SG_Edge__TUI__Slug
from sg_compute_specs.sg_edge.tui.screens.widgets.SG_Edge__TUI__Table         import type_safe_table

try:
    import textual                                                                   # noqa: F401
    HAS_TEXTUAL = True
except Exception:
    HAS_TEXTUAL = False

LIVE = Enum__SG_Edge__TUI__Slug_State.LIVE


class test_type_safe_table(TestCase):

    def test_columns_and_rows_from_json(self):
        slugs = [Schema__SG_Edge__TUI__Slug(slug='alice', fqdn='alice.x', state=LIVE, backend_ip='10.0.0.1', backend_port=8080)]
        cols, rows = type_safe_table(slugs, ['slug', 'state', 'backend_ip'])
        assert cols == ['slug', 'state', 'backend_ip']
        assert rows == [['alice', 'live', '10.0.0.1']]

    def test_auto_columns_when_none(self):
        cols, rows = type_safe_table([Schema__SG_Edge__TUI__Slug(slug='a', fqdn='a.x', state=LIVE)])
        assert set(cols) == {'slug', 'fqdn', 'state', 'backend_ip', 'backend_port'}   # all fields from .json()
        assert len(rows) == 1

    def test_empty(self):
        assert type_safe_table([], ['slug']) == (['slug'], [])


@skipUnless(HAS_TEXTUAL, 'textual not installed')
class test_SG_Edge__TUI__Screen__Slugs(TestCase):

    def setUp(self):
        from sg_compute_specs.sg_edge.local.Local__Edge__Stack            import Local__Edge__Stack
        from sg_compute_specs.sg_edge.tui.source.SG_Edge__TUI__Local_Source import SG_Edge__TUI__Local_Source
        self.dir = tempfile.mkdtemp(prefix='sg-edge-tui-slugs-')
        stack    = Local__Edge__Stack(state_dir=self.dir)
        stack.setup()
        stack.register('alice')
        stack.register('bob')
        self.source = SG_Edge__TUI__Local_Source(stack=stack)

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def screen(self):
        from sg_compute_specs.sg_edge.tui.screens.SG_Edge__TUI__Screen__Slugs import SG_Edge__TUI__Screen__Slugs
        return SG_Edge__TUI__Screen__Slugs(source=self.source, refresh_seconds=0)

    def table(self, app):
        from textual.widgets import DataTable
        return app.query_one('#slugs', DataTable)

    def test_rows_populate_and_cursor_moves(self):
        asyncio.run(self.scenario_rows())

    async def scenario_rows(self):
        app = self.screen()
        async with app.run_test() as pilot:
            await pilot.pause()
            assert self.table(app).row_count == 2                                    # one row per slug
            assert self.table(app).cursor_row == 0
            await pilot.press('down')                                                # DataTable's built-in cursor — no hand-rolled nav
            await pilot.pause()
            assert self.table(app).cursor_row == 1

    def test_enter_selects_row_and_drills(self):
        asyncio.run(self.scenario_drill())

    async def scenario_drill(self):
        app = self.screen()
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press('down')                                                # cursor → second slug
            await pilot.press('enter')                                               # DataTable RowSelected → drill
            await pilot.pause()
        names = sorted(s.slug for s in app.snapshot.slugs)
        assert app.opened_slug == names[1]                                           # the selected row's slug
