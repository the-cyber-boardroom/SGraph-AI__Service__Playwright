# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Session__Worker (Φ7-proper)
#
# The worker is a per-session dedicated thread that owns the Playwright
# runtime + browser + page. These tests verify the queue / lifecycle
# semantics in isolation (no Playwright needed — launch_fn is just a
# regular Python function).
# ═══════════════════════════════════════════════════════════════════════════════

import threading
from unittest import TestCase

from sg_compute_specs.playwright.core.service.Session__Worker import Session__Worker


class test_start(TestCase):

    def test__launch_fn_runs_on_worker_thread_not_caller(self):
        caller_thread_id  = threading.get_ident()
        worker_thread_ids = []

        def _launch():
            worker_thread_ids.append(threading.get_ident())
            return {'k': 'v'}

        w     = Session__Worker()
        state = w.start(_launch)
        try:
            assert state          == {'k': 'v'}
            assert worker_thread_ids[0] != caller_thread_id                          # launch_fn ran on the worker, not the caller
        finally:
            w.stop()

    def test__launch_fn_exception_is_re_raised_to_caller(self):
        def _launch():
            raise ValueError('boom')

        w = Session__Worker()
        with self.assertRaises(ValueError) as cm:
            w.start(_launch)
        assert 'boom' in str(cm.exception)
        # Note: stop() not needed — start() failure means the worker exited

    def test__start_returns_a_shallow_copy_so_mutations_dont_leak(self):
        def _launch():
            return {'list': [1, 2, 3]}
        w = Session__Worker()
        s = w.start(_launch)
        try:
            s.pop('list')
            # Internal state is unaffected (shallow copy of the outer dict)
            assert 'list' in w._state
        finally:
            w.stop()


class test_submit(TestCase):

    def test__submit_runs_fn_on_worker_thread_and_returns_value(self):
        ids = []
        def _launch(): return {}
        w = Session__Worker()
        w.start(_launch)
        try:
            def _work(a, b, c=0):
                ids.append(threading.get_ident())
                return a + b + c
            result = w.submit(_work, 1, 2, c=10)
            assert result   == 13
            assert ids[0]   != threading.get_ident()                                 # ran on worker
        finally:
            w.stop()

    def test__submit_re_raises_fn_exceptions(self):
        w = Session__Worker()
        w.start(lambda: {})
        try:
            def _boom():
                raise RuntimeError('something went wrong')
            with self.assertRaises(RuntimeError) as cm:
                w.submit(_boom)
            assert 'something went wrong' in str(cm.exception)
        finally:
            w.stop()

    def test__submit_after_stop_raises(self):
        w = Session__Worker()
        w.start(lambda: {})
        w.stop()
        with self.assertRaises(RuntimeError):
            w.submit(lambda: 'unreachable')

    def test__multiple_submits_run_sequentially_on_the_same_thread(self):            # The thread-affinity guarantee — all calls hit the same OS thread
        ids = []
        w = Session__Worker()
        w.start(lambda: {})
        try:
            for _ in range(10):
                w.submit(lambda: ids.append(threading.get_ident()))
            assert len(set(ids)) == 1                                                # all 10 ran on the same thread
        finally:
            w.stop()


class test_teardown(TestCase):

    def test__teardown_fn_runs_on_worker_thread_during_stop(self):
        teardown_ids = []
        teardown_state = []

        def _launch():
            return {'session': 'abc'}

        def _teardown(state):
            teardown_ids.append(threading.get_ident())
            teardown_state.append(state)

        w = Session__Worker()
        w.start(_launch, teardown_fn=_teardown)
        worker_id_during_submit = []
        w.submit(lambda: worker_id_during_submit.append(threading.get_ident()))
        w.stop()
        assert teardown_ids                                                          # teardown ran
        assert teardown_ids[0] == worker_id_during_submit[0]                         # ...on the same thread that handled submits
        assert teardown_state[0] == {'session': 'abc'}

    def test__stop_is_idempotent(self):
        w = Session__Worker()
        w.start(lambda: {})
        w.stop()
        w.stop()                                                                     # No exception
        assert not w.is_alive()

    def test__teardown_exception_is_swallowed_not_raised(self):                      # Close must never raise — daemon-thread-dying-on-process-exit also OK
        def _teardown(state):
            raise RuntimeError('teardown blew up')
        w = Session__Worker()
        w.start(lambda: {}, teardown_fn=_teardown)
        w.stop()                                                                     # No exception propagated to caller
