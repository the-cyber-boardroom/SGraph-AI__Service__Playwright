# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI (tests) — Enum__CF__Edge__Result__Type
# Pins the nine result types we model.  Wire form uses CamelCase as
# CloudFront emits (Hit / Miss / FunctionGeneratedResponse).
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                       import TestCase

from sgraph_ai_service_playwright__cli.elastic.lets.cf.events.enums.Enum__CF__Edge__Result__Type import Enum__CF__Edge__Result__Type


class test_Enum__CF__Edge__Result__Type(TestCase):

    def test_known_members(self):                                                   # 9 values — locks the surface
        names = {m.name for m in Enum__CF__Edge__Result__Type}
        assert names == {'Hit', 'RefreshHit', 'OriginShieldHit', 'Miss',
                         'LimitExceeded', 'Redirect', 'Error',
                         'FunctionGeneratedResponse', 'Other'}

    def test_camelcase_wire_form(self):                                             # The TSV column emits CamelCase; we must NOT lowercase
        assert str(Enum__CF__Edge__Result__Type.Hit)                       == 'Hit'
        assert str(Enum__CF__Edge__Result__Type.FunctionGeneratedResponse) == 'FunctionGeneratedResponse'

    def test_lookup_by_value(self):
        assert Enum__CF__Edge__Result__Type('Miss') == Enum__CF__Edge__Result__Type.Miss
