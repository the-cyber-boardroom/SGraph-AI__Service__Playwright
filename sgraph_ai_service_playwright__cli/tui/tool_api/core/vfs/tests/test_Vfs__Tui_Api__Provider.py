# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tui/tool_api/core/vfs tests: Vfs__Tui_Api__Provider
# memory_fs requires Python 3.12 — gated via importorskip (skips cleanly on 3.11).
# Run on the 3.12 venv:  /tmp/venv312/bin/pytest <this dir>
# ═══════════════════════════════════════════════════════════════════════════════

import os

import pytest

pytest.importorskip('memory_fs')                                                  # 3.12-only; skips on 3.11

from sgraph_ai_service_playwright__cli.tui.tool_api.core.vfs.Vfs__Tui_Api__Provider import Vfs__Tui_Api__Provider


def _provider():
    return Vfs__Tui_Api__Provider()


def test_write_then_read_roundtrip():
    provider = _provider()
    assert provider.dispatch('vfs.write', {'path': 'docs/a.txt', 'content': 'hello'}).ok is True
    read = provider.dispatch('vfs.read', {'path': 'docs/a.txt'})
    assert read.ok is True and read.data['result'] == 'hello'


def test_list_and_stat():
    provider = _provider()
    provider.dispatch('vfs.write', {'path': 'docs/a.txt', 'content': 'hi'})
    listing = provider.dispatch('vfs.list', {'path': 'docs'})
    assert listing.ok is True and 'docs/a.txt' in listing.data['result']
    stat = provider.dispatch('vfs.stat', {'path': 'docs/a.txt'})
    assert stat.data['result']['exists'] is True and stat.data['result']['size'] == 2


def test_delete_removes_file():
    provider = _provider()
    provider.dispatch('vfs.write', {'path': 'x.txt', 'content': 'y'})
    assert provider.dispatch('vfs.delete', {'path': 'x.txt'}).data['result']['deleted'] is True
    assert provider.dispatch('vfs.stat', {'path': 'x.txt'}).data['result']['exists'] is False


def test_fresh_provider_is_empty_ephemeral():
    assert _provider().state()['files'] == []


def test_unknown_action():
    assert _provider().dispatch('vfs.bogus', {}).ok is False


def test_vfs_provider_satisfies_contract():
    from sgraph_ai_service_playwright__cli.tui.tool_api.testing.Tui_Api__Contract__Asserts import Tui_Api__Contract__Asserts
    Tui_Api__Contract__Asserts().assert_ok(_provider())


def test_manifest_tiers_and_real_schema():
    manifest = _provider().manifest()
    names    = [str(a.name) for a in manifest.actions]
    assert {'vfs.read', 'vfs.write', 'vfs.delete', 'vfs.clear'} <= set(names)
    write = next(a for a in manifest.actions if str(a.name) == 'vfs.write')
    assert write.input_schema['properties']['content']['type'] == 'string'
    assert str(write.tier) == 'write'
    assert str(next(a for a in manifest.actions if str(a.name) == 'vfs.delete').tier) == 'destructive'


def test_destructive_action_gated_by_execution_center(tmp_path):
    from sgraph_ai_service_playwright__cli.aws.creds.service.Creds__Scope__Catalogue        import Creds__Scope__Catalogue
    from sgraph_ai_service_playwright__cli.tui.tool_api.service.Tui_Api__Execution_Center   import Tui_Api__Execution_Center
    from sgraph_ai_service_playwright__cli.tui.tool_api.service.Tui_Api__Privilege__Resolver import Tui_Api__Privilege__Resolver
    from sgraph_ai_service_playwright__cli.tui.tool_api.service.Tui_Api__Registry           import Tui_Api__Registry

    provider = _provider()
    provider.dispatch('vfs.write', {'path': 'z.txt', 'content': 'zz'})
    resolver = Tui_Api__Privilege__Resolver(creds_catalogue=Creds__Scope__Catalogue(catalogue_path=str(tmp_path / 's.json')))
    center   = Tui_Api__Execution_Center(registry=Tui_Api__Registry().register(provider),
                                        resolver=resolver, mutation_env='SG_VFS_TEST_MUT')
    os.environ.pop('SG_VFS_TEST_MUT', None)
    gated = center.execute('core.vfs', 'vfs.delete', {'path': 'z.txt'})           # DESTRUCTIVE, no env, no confirm
    assert gated.ok is False and gated.dry_run is True
    assert provider.dispatch('vfs.stat', {'path': 'z.txt'}).data['result']['exists'] is True   # NOT deleted
