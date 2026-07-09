# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Desktop__Browser__Manager (sg-playwright-vnc, P2)
#
# In-memory, no mocks: display_mode() env parsing, the headless-instance 400
# guard (no browser is launched on that path), and the headed default-args seam
# in Browser__Launcher (pure kwargs building). The real headed launch under Xvfb
# is covered by tests/integration/test_Desktop__Headed__Launch.py (gated) and by
# the CI integration-test-vnc-image job against the built image.
# ═══════════════════════════════════════════════════════════════════════════════

import os
from unittest                                                                          import TestCase

from fastapi                                                                           import HTTPException

from sg_compute_specs.playwright.core.consts.env_vars                                  import ENV_VAR__DISPLAY_MODE
from sg_compute_specs.playwright.core.schemas.browser.Schema__Browser__Config          import Schema__Browser__Config
from sg_compute_specs.playwright.core.schemas.desktop.Schema__Desktop__Browser__Request import Schema__Desktop__Browser__Request
from sg_compute_specs.playwright.core.schemas.enums.Enum__Display__Mode                import Enum__Display__Mode
from sg_compute_specs.playwright.core.service.Browser__Launcher                        import (Browser__Launcher, DEFAULT_LAUNCH_ARGS,
                                                                                               DEFAULT_LAUNCH_ARGS__HEADED)
from sg_compute_specs.playwright.core.service.Desktop__Browser__Manager                import Desktop__Browser__Manager, display_mode


class _DisplayModeEnv:                                                                 # set/clear SG_PLAYWRIGHT__DISPLAY_MODE around a block
    def __init__(self, value):
        self.value = value
    def __enter__(self):
        self.prior = os.environ.pop(ENV_VAR__DISPLAY_MODE, None)
        if self.value is not None:
            os.environ[ENV_VAR__DISPLAY_MODE] = self.value
    def __exit__(self, *exc):
        os.environ.pop(ENV_VAR__DISPLAY_MODE, None)
        if self.prior is not None:
            os.environ[ENV_VAR__DISPLAY_MODE] = self.prior


class test_display_mode(TestCase):

    def test_unset_is_headless(self):                                                  # base image default — no X server
        with _DisplayModeEnv(None):
            assert display_mode() == Enum__Display__Mode.HEADLESS

    def test_vnc(self):
        with _DisplayModeEnv('vnc'):
            assert display_mode() == Enum__Display__Mode.VNC

    def test_case_and_whitespace_tolerant(self):
        with _DisplayModeEnv('  VNC '):
            assert display_mode() == Enum__Display__Mode.VNC

    def test_unknown_value_is_headless(self):                                          # unknown → the safe default, never an exception
        with _DisplayModeEnv('desktop'):
            assert display_mode() == Enum__Display__Mode.HEADLESS


class test_open_browser_guard(TestCase):

    def test_headless_instance_rejects_400_naming_the_env_var(self):                   # no display → clear 400, no launch attempted
        with _DisplayModeEnv(None):
            manager = Desktop__Browser__Manager()
            try:
                manager.open_browser(Schema__Desktop__Browser__Request())
                assert False, 'expected HTTPException'
            except HTTPException as exc:
                assert exc.status_code == 400
                assert ENV_VAR__DISPLAY_MODE in str(exc.detail)                        # actionable: tells the operator which env var to set


class test_headed_launch_args_seam(TestCase):

    def test_headless_default_args_keep_single_process(self):                          # lambda-tuned set unchanged
        kwargs = Browser__Launcher().build_launch_kwargs(Schema__Browser__Config(headless=True))
        assert kwargs['headless'] is True
        assert kwargs['args'] == DEFAULT_LAUNCH_ARGS
        assert '--single-process' in kwargs['args']

    def test_headed_default_args_drop_single_process(self):                            # crash-prone with a real window
        kwargs = Browser__Launcher().build_launch_kwargs(Schema__Browser__Config(headless=False))
        assert kwargs['headless'] is False
        assert kwargs['args'] == DEFAULT_LAUNCH_ARGS__HEADED
        assert '--single-process' not in kwargs['args']
        assert '--no-sandbox'     in kwargs['args']                                    # container-safety args stay
        assert '--start-maximized' in kwargs['args']

    def test_caller_args_still_replace_defaults_when_headed(self):                     # spec §5.2 contract survives the seam
        config = Schema__Browser__Config(headless=False, launch_args=['--foo'])
        kwargs = Browser__Launcher().build_launch_kwargs(config)
        assert kwargs['args'] == ['--foo']
