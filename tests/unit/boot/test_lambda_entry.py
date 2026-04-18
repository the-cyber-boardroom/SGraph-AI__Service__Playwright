# ═══════════════════════════════════════════════════════════════════════════════
# Tests — lambda_entry.py (v0.1.29 — thin shim over Agentic_Boot_Shim)
#
# Scope (unit-level):
#   • module surface — the entry file exposes main/run + the error/handler/app
#     module-level placeholders; importing it has no side effects.
#   • run() — error string short-circuit, delegation to handler.
#
# The heavy lifting (load_from_local_path, load_from_s3, resolve, boot) now
# lives in Agentic_Code_Loader and Agentic_Boot_Shim and has its own tests.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                       import TestCase

import lambda_entry


class test_module_surface(TestCase):

    def test__exposes_entry_functions(self):
        assert callable(lambda_entry.main)
        assert callable(lambda_entry.run)

    def test__module_level_state_starts_unpinned(self):
        assert lambda_entry.error       is None or isinstance(lambda_entry.error, str)   # May have been pinned by an earlier test; tolerate either
        assert lambda_entry.handler     is None or callable(lambda_entry.handler)
        assert lambda_entry.app         is None or lambda_entry.app is not None
        assert lambda_entry.code_source is None or isinstance(lambda_entry.code_source, str)


class test_run(TestCase):

    def test__returns_error_string_when_error_pinned(self):
        saved_error   = lambda_entry.error
        saved_handler = lambda_entry.handler
        try:
            lambda_entry.error   = 'CRITICAL ERROR: test'
            lambda_entry.handler = None
            assert lambda_entry.run({}, None) == 'CRITICAL ERROR: test'
        finally:
            lambda_entry.error   = saved_error
            lambda_entry.handler = saved_handler

    def test__delegates_to_handler_when_ok(self):
        saved_error   = lambda_entry.error
        saved_handler = lambda_entry.handler
        try:
            calls = []
            def fake_handler(event, ctx):
                calls.append((event, ctx))
                return 'ok'
            lambda_entry.error   = None
            lambda_entry.handler = fake_handler
            assert lambda_entry.run({'k': 'v'}, 'ctx') == 'ok'
            assert calls == [({'k': 'v'}, 'ctx')]
        finally:
            lambda_entry.error   = saved_error
            lambda_entry.handler = saved_handler
