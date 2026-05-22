# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — bedrock tui: Bedrock__Chat__Documents
# Loads a file into a Schema__Bedrock__Chat__Document and builds the Converse
# `document` content block Nova reads. Enforces Bedrock's limits (supported formats,
# ≤ ~4.5 MB / doc, ≤ 5 docs / message). Pure — no boto3.
# ═══════════════════════════════════════════════════════════════════════════════

import base64
import os
import re

from osbot_utils.type_safe.Type_Safe import Type_Safe

from sgraph_ai_service_playwright__cli.aws.bedrock.tui.schemas.Schema__Bedrock__Chat__Document import Schema__Bedrock__Chat__Document

_SUPPORTED = {'pdf', 'csv', 'doc', 'docx', 'xls', 'xlsx', 'html', 'txt', 'md'}
_ALIASES   = {'htm': 'html', 'markdown': 'md'}
_MAX_BYTES = 4_500_000                                                            # Bedrock per-document limit (~4.5 MB)
_MAX_DOCS  = 5                                                                    # Bedrock per-message limit


class Bedrock__Chat__Documents(Type_Safe):

    def detect_format(self, path: str) -> str:
        ext = os.path.splitext(path)[1].lstrip('.').lower()
        return _ALIASES.get(ext, ext)

    def safe_name(self, path: str) -> str:                                        # Bedrock document name: letters/digits/space/-()[] only
        return re.sub(r'[^a-zA-Z0-9 \-\(\)\[\]]', '_', os.path.basename(path)) or 'document'

    def load(self, path: str) -> Schema__Bedrock__Chat__Document:
        fmt = self.detect_format(path)
        if fmt not in _SUPPORTED:
            raise ValueError(f'unsupported document format: .{fmt} (supported: {sorted(_SUPPORTED)})')
        with open(path, 'rb') as handle:
            raw = handle.read()
        if len(raw) > _MAX_BYTES:
            raise ValueError(f'document too large: {len(raw)} bytes > {_MAX_BYTES}')
        return Schema__Bedrock__Chat__Document(name     = self.safe_name(path),
                                             format   = fmt,
                                             size     = len(raw),
                                             data_b64 = base64.b64encode(raw).decode('ascii'))

    def validate_attachments(self, documents) -> str:                            # '' if ok, else an actionable message
        if len(documents) > _MAX_DOCS:
            return f'too many documents: {len(documents)} > {_MAX_DOCS} per message'
        return ''

    def content_block(self, document: Schema__Bedrock__Chat__Document) -> dict:
        return {'document': {'format': str(document.format),
                             'name'  : str(document.name),
                             'source': {'bytes': base64.b64decode(document.data_b64)}}}
