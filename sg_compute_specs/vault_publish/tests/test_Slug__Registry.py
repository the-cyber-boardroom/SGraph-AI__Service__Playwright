# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Slug__Registry (EC2-tag backed)
# In-memory EC2 client fake injected via _ec2_factory seam.
# No mocks, no patches, no AWS calls, no SSM.
# ═══════════════════════════════════════════════════════════════════════════════

from datetime import datetime, timezone

from sg_compute_specs.vault_publish.service.Slug__Registry import (
    Slug__Registry, TAG_SLUG, TAG_FQDN, TAG_ZONE, TAG_STYPE, STYPE_VAL,
)


# ── In-memory EC2 client fake ─────────────────────────────────────────────────

class _Fake_EC2:
    """Minimal in-memory EC2 client.

    Supports create_tags + describe_instances + start_instances, scoped to a
    shared `_store` dict keyed by instance_id. The store carries each fake
    instance's tag dict, state-name, public IP, and launch time.
    """

    def __init__(self, store: dict):
        self._store = store

    def create_tags(self, Resources, Tags):
        for iid in Resources:
            inst = self._store.setdefault(iid, _new_instance())
            for t in Tags:
                inst['tags'][t['Key']] = t['Value']
        return {}

    def describe_instances(self, Filters=None):
        wanted_tag_key = None
        wanted_tags    = {}
        wanted_states  = None
        for f in Filters or []:
            name = f.get('Name', '')
            vals = f.get('Values', []) or []
            if not vals:
                continue
            if name == 'instance-state-name':
                wanted_states = vals
            elif name == 'tag-key':
                wanted_tag_key = vals[0]
            elif name.startswith('tag:'):
                wanted_tags[name[4:]] = vals[0]

        instances = []
        for iid, inst in self._store.items():
            tags = inst.get('tags', {})
            if wanted_tag_key and wanted_tag_key not in tags:
                continue
            if not all(tags.get(k) == v for k, v in wanted_tags.items()):
                continue
            if wanted_states and inst.get('state') not in wanted_states:
                continue
            instances.append({
                'InstanceId'     : iid,
                'State'          : {'Name': inst.get('state', 'running')},
                'PublicIpAddress': inst.get('public_ip', ''),
                'Tags'           : [{'Key': k, 'Value': v} for k, v in tags.items()],
                'LaunchTime'     : inst.get('launch_time'),
            })
        if instances:
            return {'Reservations': [{'Instances': instances}]}
        return {'Reservations': []}

    def start_instances(self, InstanceIds=None):
        for iid in InstanceIds or []:
            if iid in self._store:
                self._store[iid]['state'] = 'pending'
        return {}


def _new_instance(state='running', public_ip='10.0.0.1') -> dict:
    return {
        'tags'       : {TAG_STYPE: STYPE_VAL},
        'state'      : state,
        'public_ip'  : public_ip,
        'launch_time': datetime(2026, 5, 18, 12, 0, 0, tzinfo=timezone.utc),
    }


def _make_registry(store: dict = None, region: str = 'eu-west-2'):
    if store is None:
        store = {}
    reg = Slug__Registry(region=region)
    reg._ec2_factory = lambda r: _Fake_EC2(store)
    return reg, store


def _seed_instance(store: dict, instance_id: str = 'i-test01',
                   state: str = 'running', public_ip: str = '10.0.0.1') -> None:
    store[instance_id] = _new_instance(state=state, public_ip=public_ip)


# ── Tests ─────────────────────────────────────────────────────────────────────

class TestSlugRegistry:
    def test_put_and_get(self):
        reg, store = _make_registry()
        _seed_instance(store)
        ok = reg.put(slug='sara-cv', fqdn='sara-cv.aws.sg-labs.app',
                     region='eu-west-2', instance_id='i-test01')
        assert ok is True

        entry = reg.get('sara-cv')
        assert entry is not None
        assert str(entry.slug)   == 'sara-cv'
        assert str(entry.fqdn)   == 'sara-cv.aws.sg-labs.app'
        assert str(entry.region) == 'eu-west-2'

        # Tags actually landed on the instance
        inst_tags = store['i-test01']['tags']
        assert inst_tags[TAG_SLUG] == 'sara-cv'
        assert inst_tags[TAG_FQDN] == 'sara-cv.aws.sg-labs.app'
        assert inst_tags[TAG_ZONE] == 'aws.sg-labs.app'

    def test_get_missing_returns_none(self):
        reg, _ = _make_registry()
        assert reg.get('nonexistent') is None

    def test_get_instance_returns_raw_dict(self):
        reg, store = _make_registry()
        _seed_instance(store, public_ip='198.51.100.1')
        reg.put(slug='sara-cv', fqdn='sara-cv.aws.sg-labs.app',
                region='eu-west-2', instance_id='i-test01')
        inst = reg.get_instance('sara-cv')
        assert inst is not None
        assert inst.get('PublicIpAddress') == '198.51.100.1'
        assert inst.get('InstanceId')      == 'i-test01'

    def test_delete_returns_true_when_slug_present(self):
        # delete() is now a no-op for the SSM-era contract — terminating the
        # EC2 instance removes its tags. The method returns True iff a slug
        # was found at the moment of the call, so callers can confirm action.
        reg, store = _make_registry()
        _seed_instance(store)
        reg.put(slug='sara-cv', fqdn='sara-cv.aws.sg-labs.app',
                region='eu-west-2', instance_id='i-test01')
        assert reg.delete('sara-cv') is True

    def test_delete_missing_returns_false(self):
        reg, _ = _make_registry()
        assert reg.delete('nonexistent') is False

    def test_list_all_empty(self):
        reg, _ = _make_registry()
        assert reg.list_all() == []

    def test_list_all_with_entries(self):
        reg, store = _make_registry()
        _seed_instance(store, instance_id='i-a')
        _seed_instance(store, instance_id='i-b')
        reg.put(slug='slug-a', fqdn='slug-a.aws.sg-labs.app',
                region='eu-west-2', instance_id='i-a')
        reg.put(slug='slug-b', fqdn='slug-b.aws.sg-labs.app',
                region='eu-west-2', instance_id='i-b')
        slugs = sorted(reg.list_all())
        assert slugs == ['slug-a', 'slug-b']

    def test_list_all_excludes_terminated(self):
        reg, store = _make_registry()
        _seed_instance(store, instance_id='i-live', state='running')
        _seed_instance(store, instance_id='i-dead', state='terminated')
        reg.put(slug='live', fqdn='live.aws.sg-labs.app',
                region='eu-west-2', instance_id='i-live')
        reg.put(slug='dead', fqdn='dead.aws.sg-labs.app',
                region='eu-west-2', instance_id='i-dead')
        assert reg.list_all() == ['live']

    def test_no_vault_key_anywhere(self):
        # SECURITY: vault_key must NEVER appear in tags or anywhere we control.
        reg, store = _make_registry()
        _seed_instance(store)
        reg.put(slug='sara-cv', fqdn='sara-cv.aws.sg-labs.app',
                region='eu-west-2', instance_id='i-test01')
        for k, v in store['i-test01']['tags'].items():
            assert 'vault_key' not in k.lower()
            assert 'vault_key' not in str(v).lower()
