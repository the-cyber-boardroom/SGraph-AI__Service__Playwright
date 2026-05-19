# ═══════════════════════════════════════════════════════════════════════════════
# tests/unit — test_Primitives
# Covers: Safe_Str__VAF__Slug and Safe_Str__VAF__Cluster — valid/invalid inputs.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest import TestCase

from sg_compute_specs.vault_app.fargate.primitives.Safe_Str__VAF__Slug    import Safe_Str__VAF__Slug
from sg_compute_specs.vault_app.fargate.primitives.Safe_Str__VAF__Cluster import Safe_Str__VAF__Cluster


class test_Safe_Str__VAF__Slug(TestCase):

    # ── valid slugs ──────────────────────────────────────────────────────────

    def test_slug_simple_name(self):
        s = Safe_Str__VAF__Slug('dinis-tue')
        assert str(s) == 'dinis-tue'

    def test_slug_all_lowercase_alpha(self):
        s = Safe_Str__VAF__Slug('ab')
        assert str(s) == 'ab'

    def test_slug_starts_with_digit(self):
        s = Safe_Str__VAF__Slug('1a')
        assert str(s) == '1a'

    def test_slug_digits_and_hyphens(self):
        s = Safe_Str__VAF__Slug('vault-mouse-1')
        assert str(s) == 'vault-mouse-1'

    def test_slug_empty_allowed(self):
        s = Safe_Str__VAF__Slug('')
        assert str(s) == ''

    def test_slug_max_length_41_chars(self):
        # 1 lead char + 40 chars = 41 total (the maximum)
        value = 'a' + '-' * 40
        s = Safe_Str__VAF__Slug(value)
        assert str(s) == value

    # ── invalid slugs ────────────────────────────────────────────────────────

    def test_slug_uppercase_rejected(self):
        with self.assertRaises(Exception):
            Safe_Str__VAF__Slug('Dinis-Tue')

    def test_slug_space_rejected(self):
        with self.assertRaises(Exception):
            Safe_Str__VAF__Slug('my slug')

    def test_slug_underscore_rejected(self):
        with self.assertRaises(Exception):
            Safe_Str__VAF__Slug('my_slug')

    def test_slug_too_short_single_char_rejected(self):
        with self.assertRaises(Exception):
            Safe_Str__VAF__Slug('a')

    def test_slug_too_long_42_chars_rejected(self):
        # 1 lead char + 41 chars = 42 total (exceeds max)
        value = 'a' + '-' * 41
        with self.assertRaises(Exception):
            Safe_Str__VAF__Slug(value)

    def test_slug_leading_hyphen_rejected(self):
        with self.assertRaises(Exception):
            Safe_Str__VAF__Slug('-my-slug')

    def test_slug_dot_rejected(self):
        with self.assertRaises(Exception):
            Safe_Str__VAF__Slug('my.slug')


class test_Safe_Str__VAF__Cluster(TestCase):

    # ── valid cluster names ──────────────────────────────────────────────────

    def test_cluster_simple_name(self):
        s = Safe_Str__VAF__Cluster('acme-prod')
        assert str(s) == 'acme-prod'

    def test_cluster_starts_with_digit(self):
        s = Safe_Str__VAF__Cluster('1cluster')
        assert str(s) == '1cluster'

    def test_cluster_two_chars_min(self):
        s = Safe_Str__VAF__Cluster('ab')
        assert str(s) == 'ab'

    def test_cluster_max_length_65_chars(self):
        # 1 lead char + 64 chars = 65 total (the maximum)
        value = 'a' + 'b' * 64
        s = Safe_Str__VAF__Cluster(value)
        assert str(s) == value

    def test_cluster_empty_allowed(self):
        s = Safe_Str__VAF__Cluster('')
        assert str(s) == ''

    # ── invalid cluster names ────────────────────────────────────────────────

    def test_cluster_uppercase_rejected(self):
        with self.assertRaises(Exception):
            Safe_Str__VAF__Cluster('Acme-Prod')

    def test_cluster_space_rejected(self):
        with self.assertRaises(Exception):
            Safe_Str__VAF__Cluster('acme prod')

    def test_cluster_leading_hyphen_rejected(self):
        with self.assertRaises(Exception):
            Safe_Str__VAF__Cluster('-cluster')

    def test_cluster_too_short_single_char_rejected(self):
        with self.assertRaises(Exception):
            Safe_Str__VAF__Cluster('a')

    def test_cluster_too_long_66_chars_rejected(self):
        value = 'a' + 'b' * 65
        with self.assertRaises(Exception):
            Safe_Str__VAF__Cluster(value)

    def test_cluster_dot_rejected(self):
        with self.assertRaises(Exception):
            Safe_Str__VAF__Cluster('acme.prod')
