# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tests for Stack__Naming
# Section-aware naming helpers shared by every sister stack section
# (sp el, sp os, sp prom, sp vnc).
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                       import TestCase

from sgraph_ai_service_playwright__cli.aws.Stack__Naming                            import Stack__Naming


class test_Stack__Naming(TestCase):

    def test_aws_name_for_stack__adds_prefix_when_missing(self):
        naming = Stack__Naming(section_prefix='elastic')
        assert naming.aws_name_for_stack('quiet-fermi') == 'elastic-quiet-fermi'

    def test_aws_name_for_stack__skips_prefix_when_already_present(self):                # Avoid cosmetic "elastic-elastic-..." doubles
        naming = Stack__Naming(section_prefix='elastic')
        assert naming.aws_name_for_stack('elastic-quiet-fermi') == 'elastic-quiet-fermi'

    def test_aws_name_for_stack__partial_match_does_not_count(self):                     # "elastic" alone is not enough — needs the trailing "-"
        naming = Stack__Naming(section_prefix='elastic')
        assert naming.aws_name_for_stack('elasticfoo') == 'elastic-elasticfoo'

    def test_aws_name_for_stack__empty_string_gets_bare_prefix(self):
        naming = Stack__Naming(section_prefix='elastic')
        assert naming.aws_name_for_stack('') == 'elastic-'

    def test_aws_name_for_stack__per_section_prefix_isolated(self):                      # Different sections produce different names from the same logical name
        elastic_naming = Stack__Naming(section_prefix='elastic')
        os_naming      = Stack__Naming(section_prefix='opensearch')
        prom_naming    = Stack__Naming(section_prefix='prometheus')
        vnc_naming     = Stack__Naming(section_prefix='vnc')
        assert elastic_naming.aws_name_for_stack('foo') == 'elastic-foo'
        assert os_naming     .aws_name_for_stack('foo') == 'opensearch-foo'
        assert prom_naming   .aws_name_for_stack('foo') == 'prometheus-foo'
        assert vnc_naming    .aws_name_for_stack('foo') == 'vnc-foo'

    def test_sg_name_for_stack__appends_sg_suffix(self):                                 # Per CLAUDE.md AWS Resource Naming rule: GroupName must NOT start with "sg-"
        naming = Stack__Naming(section_prefix='elastic')
        assert naming.sg_name_for_stack('quiet-fermi') == 'quiet-fermi-sg'

    def test_sg_name_for_stack__never_starts_with_sg_prefix(self):                       # Same regardless of section
        for prefix in ['elastic', 'opensearch', 'prometheus', 'vnc']:
            naming = Stack__Naming(section_prefix=prefix)
            sg_name = naming.sg_name_for_stack('foo')
            assert not sg_name.startswith('sg-'), f'GroupName must not start with sg- (got {sg_name})'

    def test_sg_name_for_stack__ignores_section_prefix(self):                            # SG suffix is universal across sections
        elastic_naming = Stack__Naming(section_prefix='elastic')
        vnc_naming     = Stack__Naming(section_prefix='vnc')
        assert elastic_naming.sg_name_for_stack('quiet-fermi') == 'quiet-fermi-sg'
        assert vnc_naming    .sg_name_for_stack('quiet-fermi') == 'quiet-fermi-sg'

    def test_default_section_prefix_is_empty(self):                                      # Defensive: explicit section_prefix is required for aws_name_for_stack to be useful
        naming = Stack__Naming()
        assert naming.section_prefix == ''
        assert naming.aws_name_for_stack('foo') == '-foo'                                # Bare prefix yields a leading hyphen — caller-error indicator, not a silent bug
