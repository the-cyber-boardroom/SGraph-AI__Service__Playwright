# ═══════════════════════════════════════════════════════════════════════════════
# tests/unit — test_Phase__Progress__Renderer
# Verifies context-manager lifecycle, on_phase state updates, as_progress_cb
# delegation, and _build_table structure. Uses rich Console with a StringIO
# sink to avoid terminal writes.
# ═══════════════════════════════════════════════════════════════════════════════

import io
from unittest import TestCase

from rich.console import Console
from rich.table  import Table

from sg_compute_specs.vault_app.fargate.enums.Enum__VAF__Phase__Status      import Enum__VAF__Phase__Status
from sg_compute_specs.vault_app.fargate.service.Phase__Progress__Renderer   import Phase__Progress__Renderer


def _silent_renderer(**kwargs):                                         # helper: renderer that writes to a StringIO sink
    phases = kwargs.pop('phases', ['ecr', 'iam', 'cluster'])
    r = Phase__Progress__Renderer(phases=phases, **kwargs)
    r._console_override = Console(file=io.StringIO(), force_terminal=False)
    return r


class test_Phase__Progress__Renderer(TestCase):

    # ── context manager ──────────────────────────────────────────────────────

    def test_enter_does_not_raise(self):
        renderer = Phase__Progress__Renderer(phases=['a', 'b'])
        renderer.__enter__()
        renderer.__exit__(None, None, None)                             # clean exit

    def test_enter_returns_self(self):
        renderer = Phase__Progress__Renderer(phases=['x'])
        returned = renderer.__enter__()
        renderer.__exit__(None, None, None)
        assert returned is renderer

    def test_context_manager_with_statement(self):                      # basic with statement does not raise
        with Phase__Progress__Renderer(phases=['ecr', 'iam']) as renderer:
            assert renderer is not None

    # ── on_phase state updates ───────────────────────────────────────────────

    def test_on_phase_updates_status(self):
        renderer = Phase__Progress__Renderer(phases=['ecr'])
        renderer.__enter__()
        renderer.on_phase('ecr', Enum__VAF__Phase__Status.RUNNING)
        assert renderer._state['ecr']['status'] == Enum__VAF__Phase__Status.RUNNING
        renderer.__exit__(None, None, None)

    def test_on_phase_ok_updates_detail(self):
        renderer = Phase__Progress__Renderer(phases=['ecr'])
        renderer.__enter__()
        renderer.on_phase('ecr', Enum__VAF__Phase__Status.RUNNING)
        renderer.on_phase('ecr', Enum__VAF__Phase__Status.OK, 'repo exists')
        assert renderer._state['ecr']['detail'] == 'repo exists'
        assert renderer._state['ecr']['status'] == Enum__VAF__Phase__Status.OK
        renderer.__exit__(None, None, None)

    def test_on_phase_running_sets_started_at(self):                    # started_at is set to a monotonic time float
        renderer = Phase__Progress__Renderer(phases=['iam'])
        renderer.__enter__()
        renderer.on_phase('iam', Enum__VAF__Phase__Status.RUNNING)
        assert renderer._state['iam']['started_at'] is not None
        renderer.__exit__(None, None, None)

    def test_on_phase_completed_sets_elapsed_ms(self):                  # elapsed_ms calculated after RUNNING → OK
        renderer = Phase__Progress__Renderer(phases=['iam'])
        renderer.__enter__()
        renderer.on_phase('iam', Enum__VAF__Phase__Status.RUNNING)
        renderer.on_phase('iam', Enum__VAF__Phase__Status.OK, 'done')
        assert renderer._state['iam']['elapsed_ms'] >= 0
        renderer.__exit__(None, None, None)

    # ── as_progress_cb ───────────────────────────────────────────────────────

    def test_as_progress_cb_returns_callable(self):
        renderer = Phase__Progress__Renderer(phases=['ecr'])
        renderer.__enter__()
        cb = renderer.as_progress_cb()
        assert callable(cb)
        renderer.__exit__(None, None, None)

    def test_as_progress_cb_delegates_to_on_phase(self):               # calling the closure updates _state
        renderer = Phase__Progress__Renderer(phases=['ecr'])
        renderer.__enter__()
        cb = renderer.as_progress_cb()
        cb('ecr', Enum__VAF__Phase__Status.OK, 'image pushed')
        assert renderer._state['ecr']['status'] == Enum__VAF__Phase__Status.OK
        assert renderer._state['ecr']['detail'] == 'image pushed'
        renderer.__exit__(None, None, None)

    # ── _build_table ─────────────────────────────────────────────────────────

    def test_build_table_returns_rich_Table(self):
        renderer = Phase__Progress__Renderer(phases=['ecr', 'iam'])
        renderer.__enter__()
        table = renderer._build_table()
        assert isinstance(table, Table)
        renderer.__exit__(None, None, None)

    def test_build_table_has_four_columns(self):                        # Status / Phase / Elapsed / Detail
        renderer = Phase__Progress__Renderer(phases=['ecr'])
        renderer.__enter__()
        table = renderer._build_table()
        assert len(table.columns) == 4
        renderer.__exit__(None, None, None)
