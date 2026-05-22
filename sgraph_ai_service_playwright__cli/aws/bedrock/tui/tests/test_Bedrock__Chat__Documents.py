# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI (tests) — bedrock tui: Bedrock__Chat__Documents (C-D1)
# Format detection, size/format/count limits, and the Converse document content block.
# Pure — 3.11.
# ═══════════════════════════════════════════════════════════════════════════════

import base64

import pytest

from sgraph_ai_service_playwright__cli.aws.bedrock.tui.schemas.Schema__Bedrock__Chat__Document import Schema__Bedrock__Chat__Document
from sgraph_ai_service_playwright__cli.aws.bedrock.tui.service.Bedrock__Chat__Documents        import Bedrock__Chat__Documents


def test_load_detects_format_and_reads_bytes(tmp_path):
    path = tmp_path / 'notes.md'
    path.write_text('the answer is 42')
    document = Bedrock__Chat__Documents().load(str(path))
    assert document.format == 'md'
    assert document.name   == 'notes_md'                                          # sanitised for Bedrock (dot → _)
    assert document.size   == len('the answer is 42')
    assert base64.b64decode(document.data_b64) == b'the answer is 42'


def test_unsupported_format_rejected(tmp_path):
    path = tmp_path / 'image.png'
    path.write_bytes(b'\x89PNG')
    with pytest.raises(ValueError, match='unsupported document format'):
        Bedrock__Chat__Documents().load(str(path))


def test_oversize_rejected(tmp_path):
    path = tmp_path / 'big.txt'
    path.write_bytes(b'x' * 4_500_001)
    with pytest.raises(ValueError, match='too large'):
        Bedrock__Chat__Documents().load(str(path))


def test_validate_attachments_limit():
    docs = [Schema__Bedrock__Chat__Document(name=f'd{i}', format='txt') for i in range(6)]
    assert 'too many documents' in Bedrock__Chat__Documents().validate_attachments(docs)
    assert Bedrock__Chat__Documents().validate_attachments(docs[:5]) == ''


def test_content_block_shape():
    document = Schema__Bedrock__Chat__Document(name='notes_md', format='md', size=3,
                                             data_b64=base64.b64encode(b'hey').decode('ascii'))
    block = Bedrock__Chat__Documents().content_block(document)
    assert block['document']['format']         == 'md'
    assert block['document']['name']           == 'notes_md'
    assert block['document']['source']['bytes'] == b'hey'
