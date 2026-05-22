# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI (tests) — bedrock tui: send_turn with an attached document (C-D1)
# The engine attaches a Converse document block to the user message; the in-memory
# source receives it, and the Inspector's request_json renders the doc bytes as a
# summary (not raw bytes). No AWS, no mocks. Pure — 3.11.
# ═══════════════════════════════════════════════════════════════════════════════

from sgraph_ai_service_playwright__cli.aws.bedrock.tui.service.Bedrock__Chat__Engine    import Bedrock__Chat__Engine
from sgraph_ai_service_playwright__cli.aws.bedrock.tui.service.Bedrock__Chat__Documents import Bedrock__Chat__Documents
from sgraph_ai_service_playwright__cli.aws.bedrock.tui.source.Bedrock__Chat__In_Memory  import Bedrock__Chat__In_Memory


def _engine(reply='I read your document.'):
    source = Bedrock__Chat__In_Memory()
    source.scripted = [(reply, 200, 30, 400)]                                     # the doc inflates input tokens (the model counts it)
    return Bedrock__Chat__Engine(source=source), source


def test_send_turn_attaches_document_block(tmp_path):
    path = tmp_path / 'notes.md'
    path.write_text('the answer is 42')
    document = Bedrock__Chat__Documents().load(str(path))

    engine, source = _engine()
    session = engine.new_session(region='us-east-1', model_alias='lite')
    turn    = engine.send_turn(session, 'summarise my note', documents=[document])

    sent_messages = source.calls[-1][1]                                           # (model_id, messages, system)
    user_content  = sent_messages[-1]['content']
    assert user_content[0]['text'] == 'summarise my note'
    document_block = next(block for block in user_content if 'document' in block)
    assert document_block['document']['format']          == 'md'
    assert document_block['document']['source']['bytes'] == b'the answer is 42'

    assert turn.input_tokens == 200                                              # the model's usage reflects the document
    assert '<16 bytes>' in turn.request_json                                     # Inspector shows a byte summary, not raw bytes
    assert len(session.messages[0].documents) == 1                               # the doc is stored on the user message


def test_session_without_documents_unchanged():
    engine, source = _engine('plain reply')
    session = engine.new_session(region='us-east-1', model_alias='lite')
    engine.send_turn(session, 'hi')
    user_content = source.calls[-1][1][-1]['content']
    assert user_content == [{'text': 'hi'}]                                       # no document blocks when none attached
