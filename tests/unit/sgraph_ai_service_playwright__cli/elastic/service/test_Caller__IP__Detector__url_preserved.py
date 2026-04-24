# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — regression test for Caller__IP__Detector.url
# Earlier the field was Safe_Str__Text which mangled "https://..." to
# "https:__...". Locking the type to Safe_Str__Url here so the URL survives.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                       import TestCase

from sgraph_ai_service_playwright__cli.elastic.service.Caller__IP__Detector         import Caller__IP__Detector, DEFAULT_URL


class test_Caller__IP__Detector__url_preserved(TestCase):

    def test_default_url_keeps_scheme_and_slashes(self):
        detector = Caller__IP__Detector()
        assert str(detector.url) == DEFAULT_URL                                     # exact 'https://checkip.amazonaws.com'
        assert '://' in str(detector.url)
