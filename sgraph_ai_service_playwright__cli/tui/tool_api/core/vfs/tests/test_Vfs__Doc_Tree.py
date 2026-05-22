# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tui/tool_api/core/vfs tests: Vfs__Doc_Tree
# The standard /tools/<tool>/ convention tree round-trips over a Storage_FS__Memory.
# 3.12-gated. Run: /tmp/venv312/bin/pytest <this dir>
# ═══════════════════════════════════════════════════════════════════════════════

import pytest

pytest.importorskip('memory_fs')

from memory_fs.storage_fs.providers.Storage_FS__Memory import Storage_FS__Memory

from sgraph_ai_service_playwright__cli.tui.tool_api.core.vfs.Vfs__Doc_Tree import Vfs__Doc_Tree


def test_doc_tree_roundtrip():
    storage = Storage_FS__Memory()
    tree    = Vfs__Doc_Tree(tool='bedrock-chat')
    assert tree.root() == 'tools/bedrock-chat/'
    assert tree.put_skills(storage, '# how to use this tool') is True
    assert tree.read(storage, 'skills.md') == '# how to use this tool'
    tree.put_manifest(storage, 'sg-aws.s3', '{"slug":"sg-aws.s3"}')
    assert tree.read(storage, 'api/sg-aws.s3.json') == '{"slug":"sg-aws.s3"}'
    tree.put_state(storage, '{"count":1}')
    assert tree.read(storage, 'current-state.json') == '{"count":1}'
