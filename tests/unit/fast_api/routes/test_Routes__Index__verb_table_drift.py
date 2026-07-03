# ═══════════════════════════════════════════════════════════════════════════════
# Tests — In-app verb table cannot drift from the real step surface
#
# v0.2.64 dev pack — brief 06 §5 ("verb-table drift check"). The console's docs
# tab + sequence builder are generated from `const VERBS = {...}` embedded in
# INDEX_HTML. This is the structural defence against a future D2/D4: if a verb is
# added to / removed from Enum__Step__Action (and STEP_SCHEMAS) but the UI verb
# table is not updated, this test fails — the in-app docs can never silently rot.
#
# Cheap, no browser, no mocks: it diffs the VERBS keys parsed out of the live
# INDEX_HTML against Enum__Step__Action and the dispatcher STEP_SCHEMAS registry.
# ═══════════════════════════════════════════════════════════════════════════════

import re
from unittest                                                                   import TestCase

from sg_compute_specs.playwright.core.dispatcher.step_schema_registry           import STEP_SCHEMAS
from sg_compute_specs.playwright.core.fast_api.routes.Routes__Index             import INDEX_HTML
from sg_compute_specs.playwright.core.schemas.enums.Enum__Step__Action          import Enum__Step__Action


def _verb_table_keys():                                                          # parse the top-level keys of `const VERBS = {...}` in INDEX_HTML
    m = re.search(r'const VERBS\s*=\s*\{(.*?)\n\};', INDEX_HTML, re.DOTALL)
    assert m is not None, 'const VERBS = {...} block not found in INDEX_HTML'
    body = m.group(1)
    return set(re.findall(r'^\s{2}([a-z_][a-z0-9_]*)\s*:', body, re.MULTILINE))   # two-space-indented keys are the verb entries


class test_Routes__Index__verb_table_drift(TestCase):

    @classmethod
    def setUpClass(cls):
        cls.ui_verbs   = _verb_table_keys()
        cls.enum_verbs = {a.value for a in Enum__Step__Action}

    def test__ui_verb_table_has_24_verbs(self):
        assert len(self.ui_verbs) == 24, f'Expected 24 UI verbs, got {len(self.ui_verbs)}: {sorted(self.ui_verbs)}'

    def test__ui_verb_table_matches_enum_exactly(self):                          # no verb in the enum is missing from the UI, and the UI invents none
        missing = self.enum_verbs - self.ui_verbs
        extra   = self.ui_verbs   - self.enum_verbs
        assert not missing, f'Verbs in Enum__Step__Action missing from the UI verb table: {sorted(missing)}'
        assert not extra,   f'Verbs in the UI verb table not in Enum__Step__Action: {sorted(extra)}'

    def test__ui_verb_table_matches_step_schemas_registry(self):                 # the UI verbs == the verbs the dispatcher can actually parse
        registry_verbs = {action.value for action in STEP_SCHEMAS.keys()}
        assert self.ui_verbs == registry_verbs, \
            f'UI verb table and STEP_SCHEMAS disagree — UI-only: {sorted(self.ui_verbs - registry_verbs)}, registry-only: {sorted(registry_verbs - self.ui_verbs)}'
