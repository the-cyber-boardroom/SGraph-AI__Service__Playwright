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
        # Mirror the real create path: base tags + the vault-app extras (incl. StackEngine).
        return EC2__Tags__Builder(stack_type=STACK_TYPE).build(
            stack_name, '1.2.3.4/32', 'tester',
            extra_tags={'StackEngine': 'docker', 'StackWithPlaywright': 'true', 'AccessToken': 'secret-tok'})

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

    # ── additive Namespace tag ───────────────────────────────────────────────

    def test_prefix_adds_namespace_tag(self):
        svc    = Vault_App__Service()
        result = svc.apply_name_prefix(self._tags(), 'warm-bohr', 'acme')
        assert _val(result, 'Namespace') == 'acme'                    # filterable, additive

    def test_blank_prefix_adds_no_namespace_tag(self):
        svc    = Vault_App__Service()
        result = svc.apply_name_prefix(self._tags(), 'warm-bohr', '')
        assert all(t['Key'] != 'Namespace' for t in result)

    def test_data_and_filter_tags_never_prefixed(self):
        # StackEngine (podman detection), Purpose/StackType/StackName (filters),
        # CallerIP/CreatedBy (data) must keep their raw values.
        svc    = Vault_App__Service()
        result = svc.apply_name_prefix(self._tags(), 'warm-bohr', 'acme')
        assert _val(result, 'StackEngine') == 'docker'                # NOT 'acme-docker' — would break podman detection
        assert _val(result, 'Purpose')     == 'ephemeral-ec2'
        assert _val(result, 'CallerIP')    == '1.2.3.4/32'
        assert _val(result, 'CreatedBy')   == 'tester'

    # ── prefixed-key duplicate tags (operator hack) ──────────────────────────

    def test_prefixed_key_duplicates_created(self):
        svc    = Vault_App__Service()
        result = svc.apply_name_prefix(self._tags(), 'acme', '')  # baseline count w/ no prefix
        base_n = len(result)
        result = svc.apply_name_prefix(self._tags(), 'warm-bohr', 'acme')
        # every base tag (incl. the new Namespace) gets one prefixed-key duplicate
        assert _val(result, 'acme-StackType') == 'vault-app'          # duplicate carries original value
        assert _val(result, 'acme-StackName') == 'warm-bohr'
        assert _val(result, 'acme-Namespace') == 'acme'
        assert len(result) == (base_n + 1) * 2                        # base + Namespace, then doubled

    def test_originals_kept_alongside_duplicates(self):
        svc    = Vault_App__Service()
        result = svc.apply_name_prefix(self._tags(), 'warm-bohr', 'acme')
        keys   = [t['Key'] for t in result]
        assert 'StackType'      in keys and 'acme-StackType' in keys  # both present
        assert 'StackName'      in keys and 'acme-StackName' in keys
        # canonical lookups still resolve to the unprefixed originals (lifecycle safe)
        assert _val(result, 'StackName') == 'warm-bohr'
        assert _val(result, 'StackType') == 'vault-app'

    def test_no_duplicates_when_blank_prefix(self):
        svc    = Vault_App__Service()
        result = svc.apply_name_prefix(self._tags(), 'warm-bohr', '')
        assert not any(t['Key'].startswith('acme-') for t in result)

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
