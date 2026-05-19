# ═══════════════════════════════════════════════════════════════════════════════
# tests/unit — test_Phase__Timer
# Covers: phase() context manager, error recording, duration, cumulative sums,
# result lookup, progress_cb protocol, multi-phase accumulation, detail
# preservation, and nested-timer independence.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest import TestCase

from sg_compute_specs.vault_app.fargate.enums.Enum__VAF__Phase__Status         import Enum__VAF__Phase__Status
from sg_compute_specs.vault_app.fargate.collections.List__Schema__Phase__Result import List__Schema__Phase__Result
from sg_compute_specs.vault_app.fargate.service.Phase__Timer                    import Phase__Timer


class test_Phase__Timer(TestCase):

    # ── basic phase context manager ──────────────────────────────────────────

    def test_phase_records_name(self):
        timer = Phase__Timer()
        with timer.phase('ecr'):
            pass
        assert timer.results[0].name == 'ecr'

    def test_phase_records_status_ok_on_success(self):
        timer = Phase__Timer()
        with timer.phase('iam'):
            pass
        assert timer.results[0].status == Enum__VAF__Phase__Status.OK

    def test_phase_records_duration_ms(self):                           # duration is non-negative (may be 0 in fast CI)
        timer = Phase__Timer()
        with timer.phase('cluster'):
            pass
        assert timer.results[0].duration_ms >= 0

    def test_phase_records_started_at_iso8601(self):                    # started_at is a non-empty ISO-8601 string
        timer = Phase__Timer()
        with timer.phase('task-def'):
            pass
        started_at = timer.results[0].started_at
        assert isinstance(started_at, str) and len(started_at) > 0
        assert 'T' in started_at                                        # ISO-8601 includes T separator

    # ── error recording ──────────────────────────────────────────────────────

    def test_phase_records_status_error_on_exception(self):
        timer = Phase__Timer()
        try:
            with timer.phase('run-task'):
                raise RuntimeError('network timeout')
        except RuntimeError:
            pass
        assert timer.results[0].status == Enum__VAF__Phase__Status.ERROR

    def test_phase_records_error_string_on_exception(self):
        timer = Phase__Timer()
        try:
            with timer.phase('run-task'):
                raise ValueError('bad region')
        except ValueError:
            pass
        assert timer.results[0].error == 'bad region'

    def test_phase_propagates_exception(self):                          # __exit__ must return False — never swallow
        timer = Phase__Timer()
        with self.assertRaises(RuntimeError):
            with timer.phase('run-task'):
                raise RuntimeError('should propagate')

    def test_phase_records_duration_on_exception(self):                 # duration captured even when exception raised
        timer = Phase__Timer()
        try:
            with timer.phase('run-task'):
                raise RuntimeError('fail')
        except RuntimeError:
            pass
        assert timer.results[0].duration_ms >= 0

    # ── total_ms ─────────────────────────────────────────────────────────────

    def test_total_ms_sums_all_phases(self):
        timer = Phase__Timer()
        with timer.phase('a'):
            pass
        with timer.phase('b'):
            pass
        assert timer.total_ms() == timer.results[0].duration_ms + timer.results[1].duration_ms

    def test_total_ms_empty_results_is_zero(self):
        timer = Phase__Timer()
        assert timer.total_ms() == 0

    # ── cumulative_through ───────────────────────────────────────────────────

    def test_cumulative_through_returns_partial_sum(self):
        timer = Phase__Timer()
        with timer.phase('p1'):
            pass
        with timer.phase('p2'):
            pass
        with timer.phase('p3'):
            pass
        expected_p2 = timer.results[0].duration_ms + timer.results[1].duration_ms
        assert timer.cumulative_through('p2') == expected_p2

    def test_cumulative_through_last_phase_equals_total_ms(self):
        timer = Phase__Timer()
        with timer.phase('x'):
            pass
        with timer.phase('y'):
            pass
        assert timer.cumulative_through('y') == timer.total_ms()

    def test_cumulative_through_unknown_returns_zero(self):
        timer = Phase__Timer()
        with timer.phase('known'):
            pass
        assert timer.cumulative_through('does-not-exist') == 0

    # ── result_for ───────────────────────────────────────────────────────────

    def test_result_for_returns_correct_result(self):
        timer = Phase__Timer()
        with timer.phase('ecr'):
            pass
        with timer.phase('iam'):
            pass
        r = timer.result_for('iam')
        assert r is not None
        assert r.name == 'iam'

    def test_result_for_unknown_returns_none(self):
        timer = Phase__Timer()
        with timer.phase('ecr'):
            pass
        assert timer.result_for('missing') is None

    # ── progress_cb ──────────────────────────────────────────────────────────

    def test_progress_cb_called_with_running_on_enter(self):
        calls = []
        def cb(name, status, detail=''):
            calls.append((name, status))

        timer = Phase__Timer(progress_cb=cb)
        with timer.phase('probe'):
            pass
        assert calls[0] == ('probe', Enum__VAF__Phase__Status.RUNNING)

    def test_progress_cb_called_with_ok_on_exit(self):
        calls = []
        def cb(name, status, detail=''):
            calls.append((name, status))

        timer = Phase__Timer(progress_cb=cb)
        with timer.phase('probe'):
            pass
        assert calls[1] == ('probe', Enum__VAF__Phase__Status.OK)

    def test_progress_cb_called_with_error_on_exception(self):
        calls = []
        def cb(name, status, detail=''):
            calls.append((name, status))

        timer = Phase__Timer(progress_cb=cb)
        try:
            with timer.phase('probe'):
                raise RuntimeError('oops')
        except RuntimeError:
            pass
        assert calls[1] == ('probe', Enum__VAF__Phase__Status.ERROR)

    def test_progress_cb_receives_detail_on_exit(self):
        calls = []
        def cb(name, status, detail=''):
            calls.append((name, status, detail))

        timer = Phase__Timer(progress_cb=cb)
        with timer.phase('probe') as r:
            r.detail = 'state: STOPPED → RUNNING'
        assert calls[1][2] == 'state: STOPPED → RUNNING'

    # ── detail preservation ──────────────────────────────────────────────────

    def test_detail_set_inside_with_block_is_preserved(self):           # result is same object — mutation visible after exit
        timer = Phase__Timer()
        with timer.phase('wait-http') as r:
            r.detail = 'HTTP 200 after 3 attempts'
        assert timer.results[0].detail == 'HTTP 200 after 3 attempts'

    # ── multi-phase accumulation ─────────────────────────────────────────────

    def test_multiple_phases_accumulate_in_results(self):
        timer = Phase__Timer()
        names = ['ecr', 'iam', 'logs', 'cluster', 'task-def']
        for name in names:
            with timer.phase(name):
                pass
        assert len(timer.results) == len(names)
        assert [r.name for r in timer.results] == names

    # ── nested timers ────────────────────────────────────────────────────────

    def test_nested_timers_are_independent(self):                       # each timer has its own results list
        timer_a = Phase__Timer()
        timer_b = Phase__Timer()
        with timer_a.phase('a1'):
            with timer_b.phase('b1'):
                pass
        with timer_a.phase('a2'):
            pass

        assert len(timer_a.results) == 2
        assert len(timer_b.results) == 1
        assert timer_a.result_for('b1') is None
        assert timer_b.result_for('a1') is None

    # ── results is List__Schema__Phase__Result ───────────────────────────────

    def test_results_is_typed_list(self):                               # after first phase results is the correct collection type
        timer = Phase__Timer()
        with timer.phase('init'):
            pass
        assert isinstance(timer.results, List__Schema__Phase__Result)
