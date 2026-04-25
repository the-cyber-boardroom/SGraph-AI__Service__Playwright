# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI (tests) — Enum__LETS__Source__Slug
# Slice 1 ships exactly one source plus UNKNOWN; future slices will add more.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                       import TestCase

from sgraph_ai_service_playwright__cli.elastic.lets.cf.inventory.enums.Enum__LETS__Source__Slug import Enum__LETS__Source__Slug


class test_Enum__LETS__Source__Slug(TestCase):

    def test_known_members(self):
        names = {m.name for m in Enum__LETS__Source__Slug}
        assert names == {'CF_REALTIME', 'UNKNOWN'}                                  # Locked at slice 1; updates require a deliberate change here

    def test_str_returns_kebab_value(self):                                         # Wire format is kebab-case to match the source registry convention
        assert str(Enum__LETS__Source__Slug.CF_REALTIME) == 'cf-realtime'
        assert str(Enum__LETS__Source__Slug.UNKNOWN)     == 'unknown'

    def test_lookup_by_value(self):
        assert Enum__LETS__Source__Slug('cf-realtime') == Enum__LETS__Source__Slug.CF_REALTIME
