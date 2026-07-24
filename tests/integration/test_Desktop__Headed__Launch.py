# ═══════════════════════════════════════════════════════════════════════════════
# Integration — Desktop__Browser__Manager real headed launch (sg-playwright-vnc P2)
#
# Gated (skips cleanly when absent):
#   • SG_PLAYWRIGHT__CHROMIUM_EXECUTABLE — real Chromium (repo testing rule §3)
#   • Xvfb binary — the test starts its own :97 display (the vnc image supplies
#     :99 via supervisord; here we own the display lifecycle)
#
# No mocks: a REAL headed Chromium launches on a REAL X display through the same
# session machinery /desktop/browser uses, then the session closes. This is the
# laptop/CI-runner twin of the CI integration-test-vnc-image job (which exercises
# the same path over HTTP against the built image).
# ═══════════════════════════════════════════════════════════════════════════════

import os
import shutil
import subprocess
import time
from unittest                                                                          import TestCase, skipUnless

from sg_compute_specs.playwright.core.consts.env_vars                                  import (ENV_VAR__CHROMIUM_EXECUTABLE,
                                                                                               ENV_VAR__DISPLAY_MODE)
from sg_compute_specs.playwright.core.schemas.desktop.Schema__Desktop__Browser__Request import Schema__Desktop__Browser__Request
from sg_compute_specs.playwright.core.schemas.enums.Enum__Browser__Name                 import Enum__Browser__Name
from sg_compute_specs.playwright.core.service.Desktop__Browser__Manager                 import Desktop__Browser__Manager
from sg_compute_specs.playwright.core.service.Playwright__Service                       import Playwright__Service


HAS_CHROMIUM = bool(os.environ.get(ENV_VAR__CHROMIUM_EXECUTABLE))
HAS_XVFB     = shutil.which('Xvfb') is not None
DISPLAY      = ':97'                                                                   # own display — never collide with a real :99


@skipUnless(HAS_CHROMIUM and HAS_XVFB, 'needs SG_PLAYWRIGHT__CHROMIUM_EXECUTABLE + Xvfb')
class test_Desktop__Headed__Launch(TestCase):

    @classmethod
    def setUpClass(cls):
        cls.xvfb = subprocess.Popen(['Xvfb', DISPLAY, '-screen', '0', '1280x800x24', '-nolisten', 'tcp'],
                                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(1.0)                                                                # X socket up
        cls.prior_display = os.environ.get('DISPLAY')
        cls.prior_mode    = os.environ.get(ENV_VAR__DISPLAY_MODE)
        os.environ['DISPLAY']              = DISPLAY
        os.environ[ENV_VAR__DISPLAY_MODE]  = 'vnc'

    @classmethod
    def tearDownClass(cls):
        for key, prior in (('DISPLAY', cls.prior_display), (ENV_VAR__DISPLAY_MODE, cls.prior_mode)):
            os.environ.pop(key, None)
            if prior is not None:
                os.environ[key] = prior
        cls.xvfb.terminate()
        cls.xvfb.wait(timeout=10)

    def test_headed_chromium_opens_as_a_session_and_closes(self):
        service = Playwright__Service().setup()
        manager = Desktop__Browser__Manager(service=service)
        response = manager.open_browser(Schema__Desktop__Browser__Request(engine=Enum__Browser__Name.CHROMIUM))
        try:
            assert str(response.session_id)                                            # a real session id
            assert response.engine    == Enum__Browser__Name.CHROMIUM
            assert response.navigated is False                                         # no start_url given
            assert str(response.session_id) in service.session_registry.session_ids()  # held by the registry → /session/{id}/* works on it
        finally:
            closed = service.session_close(str(response.session_id))
            assert closed.get('closed') is True
