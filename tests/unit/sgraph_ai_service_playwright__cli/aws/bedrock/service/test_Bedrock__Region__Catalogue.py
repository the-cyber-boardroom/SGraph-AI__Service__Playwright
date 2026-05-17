# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tests for Bedrock__Region__Catalogue
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                    import TestCase

from sgraph_ai_service_playwright__cli.aws.bedrock.service.Bedrock__Region__Catalogue import Bedrock__Region__Catalogue


class test_Bedrock__Region__Catalogue(TestCase):

    def setUp(self):
        self.catalogue = Bedrock__Region__Catalogue()

    def test__is_supported__ga_region_returns_true(self):
        assert self.catalogue.is_supported('us-east-1') is True

    def test__is_supported__non_ga_region_returns_false(self):
        assert self.catalogue.is_supported('ca-west-1') is False

    def test__is_supported__empty_string_returns_false(self):
        assert self.catalogue.is_supported('') is False

    def test__is_supported__eu_west_2_is_supported(self):
        assert self.catalogue.is_supported('eu-west-2') is True

    def test__supported_regions__returns_non_empty_list(self):
        regions = self.catalogue.supported_regions()
        assert isinstance(regions, list)
        assert len(regions) > 0

    def test__supported_regions__contains_us_east_1(self):
        assert 'us-east-1' in self.catalogue.supported_regions()

    def test__supported_regions__does_not_contain_ca_west_1(self):
        assert 'ca-west-1' not in self.catalogue.supported_regions()

    def test__supported_regions__returns_copy_not_reference(self):
        r1 = self.catalogue.supported_regions()
        r2 = self.catalogue.supported_regions()
        assert r1 == r2
        r1.append('fake-region')
        assert 'fake-region' not in self.catalogue.supported_regions()
