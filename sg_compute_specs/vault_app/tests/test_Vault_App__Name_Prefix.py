# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Vault_App__Service.apply_name_prefix + --name-prefix wiring
# The Name tag is cosmetic; StackName/StackType (used by list/info/delete) must
# never change when a prefix is applied.
# ═══════════════════════════════════════════════════════════════════════════════

from sg_compute.platforms.ec2.helpers.EC2__Tags__Builder                    import EC2__Tags__Builder
from sg_compute_specs.vault_app.cli                       import Cli__Vault_App as cli
from sg_compute_specs.vault_app.schemas.Schema__Vault_App__Create__Request  import Schema__Vault_App__Create__Request
from sg_compute_specs.vault_app.service.Vault_App__Service                  import Vault_App__Service
from sg_compute_specs.vault_app.service.Vault_App__Stack__Mapper            import STACK_TYPE


def _name(tags):    return next(t['Value'] for t in tags if t['Key'] == 'Name')
def _val(tags, k):  return next(t['Value'] for t in tags if t['Key'] == k)


class TestVaultAppNamePrefix:

    def _tags(self, stack_name='warm-bohr'):
        return EC2__Tags__Builder(stack_type=STACK_TYPE).build(stack_name, '1.2.3.4/32', 'tester')

    def test_blank_prefix_is_no_op(self):
        svc    = Vault_App__Service()
        tags   = self._tags()
        result = svc.apply_name_prefix(tags, 'warm-bohr', '')
        assert _name(result) == 'warm-bohr'

    def test_prefix_applied_to_name_tag(self):
        svc    = Vault_App__Service()
        result = svc.apply_name_prefix(self._tags(), 'warm-bohr', 'acme')
        assert _name(result) == 'acme-warm-bohr'

    def test_prefix_leaves_stackname_and_stacktype_untouched(self):
        svc    = Vault_App__Service()
        result = svc.apply_name_prefix(self._tags(), 'warm-bohr', 'acme')
        assert _val(result, 'StackName') == 'warm-bohr'                # list/info/delete key — unchanged
        assert _val(result, 'StackType') == STACK_TYPE                 # filter key — unchanged

    def test_prefix_never_doubled(self):
        svc    = Vault_App__Service()
        result = svc.apply_name_prefix(self._tags('acme-warm-bohr'), 'acme-warm-bohr', 'acme')
        assert _name(result) == 'acme-warm-bohr'                       # already prefixed → not re-prefixed

    def test_whitespace_prefix_is_no_op(self):
        svc    = Vault_App__Service()
        result = svc.apply_name_prefix(self._tags(), 'warm-bohr', '   ')
        assert _name(result) == 'warm-bohr'

    # ── schema + CLI wiring ──────────────────────────────────────────────────

    def test_schema_default_is_empty(self):
        assert str(Schema__Vault_App__Create__Request().name_prefix) == ''

    def test_set_extras_sets_name_prefix(self):
        req = Schema__Vault_App__Create__Request()
        cli._set_extras(req, name_prefix='acme')
        assert str(req.name_prefix) == 'acme'

    def test_set_extras_strips_whitespace(self):
        req = Schema__Vault_App__Create__Request()
        cli._set_extras(req, name_prefix='  acme  ')
        assert str(req.name_prefix) == 'acme'
