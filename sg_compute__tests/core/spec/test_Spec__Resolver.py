# ═══════════════════════════════════════════════════════════════════════════════
# sg_compute tests — Spec__Resolver
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                 import TestCase

from sg_compute.core.spec.Spec__Resolver                                     import Spec__Resolver
from sg_compute.core.spec.schemas.Schema__Spec__Manifest__Entry              import Schema__Spec__Manifest__Entry


def _make(spec_id: str, extends: list = None) -> Schema__Spec__Manifest__Entry:
    return Schema__Spec__Manifest__Entry(spec_id=spec_id, extends=extends or [])


class test_Spec__Resolver(TestCase):

    def setUp(self):
        self.resolver = Spec__Resolver()

    def test_valid_dag_passes(self):
        specs = {
            'linux' : _make('linux')                         ,
            'docker': _make('docker', extends=['linux'])     ,
            'firefox': _make('firefox', extends=['docker'])  ,
        }
        self.resolver.validate(specs)                        # must not raise

    def test_unknown_parent_raises(self):
        specs = {'firefox': _make('firefox', extends=['nonexistent'])}
        with self.assertRaises(ValueError) as ctx:
            self.resolver.validate(specs)
        assert 'nonexistent' in str(ctx.exception)

    def test_direct_cycle_raises(self):
        specs = {'a': _make('a', extends=['a'])}
        with self.assertRaises(ValueError) as ctx:
            self.resolver.validate(specs)
        assert 'cycle' in str(ctx.exception)

    def test_two_node_cycle_raises(self):
        specs = {
            'a': _make('a', extends=['b']),
            'b': _make('b', extends=['a']),
        }
        with self.assertRaises(ValueError) as ctx:
            self.resolver.validate(specs)
        assert 'cycle' in str(ctx.exception)

    def test_three_node_cycle_raises(self):
        specs = {
            'a': _make('a', extends=['b']),
            'b': _make('b', extends=['c']),
            'c': _make('c', extends=['a']),
        }
        with self.assertRaises(ValueError) as ctx:
            self.resolver.validate(specs)
        assert 'cycle' in str(ctx.exception)

    def test_topological_order_linear(self):
        specs = {
            'linux' : _make('linux')                        ,
            'docker': _make('docker', extends=['linux'])    ,
            'firefox': _make('firefox', extends=['docker']) ,
        }
        order = self.resolver.topological_order('firefox', specs)
        assert order.index('linux')  < order.index('docker')
        assert order.index('docker') < order.index('firefox')

    def test_topological_order_no_parents(self):
        specs = {'standalone': _make('standalone')}
        order = self.resolver.topological_order('standalone', specs)
        assert order == ['standalone']
