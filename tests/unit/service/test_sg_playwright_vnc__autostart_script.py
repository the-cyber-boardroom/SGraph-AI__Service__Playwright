# ═══════════════════════════════════════════════════════════════════════════════
# Tests — sg-playwright-vnc autostart-browser.sh (static guard)
# The oneshot POSTs /desktop/browser at boot (the content_proxy fleet path). A
# start_url the API's Safe_Str__Url__Permissive schema rejects (about:blank,
# chrome://…) 500s the POST → no browser → black noVNC screen. This guards the
# regression without needing docker: the script must NOT hardcode about:blank and
# must omit start_url when unset.
# ═══════════════════════════════════════════════════════════════════════════════

from pathlib   import Path
from unittest  import TestCase

import sg_compute_specs.playwright as _pw_pkg


SCRIPT = Path(_pw_pkg.__file__).parent / 'vnc' / 'autostart-browser.sh'


class test_autostart_browser_script(TestCase):

    def setUp(self):
        self.body = SCRIPT.read_text()

    def test_script_exists(self):
        assert SCRIPT.is_file()

    def test_no_about_blank_default(self):                                           # the exact default that 500'd the boot POST
        assert ':-about:blank' not in self.body                                      # guard the bad default (the comment may still name it)

    def test_start_url_defaults_empty_and_is_conditional(self):
        assert '${SG_PLAYWRIGHT__AUTOSTART_START_URL:-}' in self.body                # default empty, not a bogus URL
        assert 'if [ -n "$START_URL" ]' in self.body                                 # send start_url only when a real URL is set…
        assert 'start_url' in self.body                                              # …still supported when provided
        assert 'BODY="{\\"engine\\": \\"${ENGINE}\\", \\"window_mode\\": \\"${WINDOW_MODE}\\"}"' in self.body   # …else the body omits start_url (blank browser opens)

    def test_window_mode_defaults_to_maximised(self):                                # a 1280x720 window on a 1920x1080 Xvfb looks broken
        assert 'SG_PLAYWRIGHT__AUTOSTART_WINDOW_MODE:-maximised' in self.body

    def test_engine_gates_the_whole_script(self):
        assert '[ -z "$ENGINE" ] && exit 0' in self.body                             # no AUTOSTART env → no-op (plain vnc image)
