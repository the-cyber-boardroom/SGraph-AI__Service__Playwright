# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — S3__Format__Detector
# Detect the render format of an S3 object from its key extension and/or
# content sniffing. Returns one of the known format labels.
# ═══════════════════════════════════════════════════════════════════════════════

import os

from osbot_utils.type_safe.Type_Safe import Type_Safe

from sgraph_ai_service_playwright__cli.aws.s3.enums.Enum__S3__Object__Format import Enum__S3__Object__Format


class S3__Format__Detector(Type_Safe):

    def detect_from_key(self, key: str) -> Enum__S3__Object__Format:             # extension-based detection
        ext = os.path.splitext(key)[-1].lower()
        ext_map = {
            '.json' : Enum__S3__Object__Format.JSON,
            '.yaml' : Enum__S3__Object__Format.YAML,
            '.yml'  : Enum__S3__Object__Format.YAML,
            '.md'   : Enum__S3__Object__Format.MARKDOWN,
            '.csv'  : Enum__S3__Object__Format.CSV,
            '.tsv'  : Enum__S3__Object__Format.CSV,
            '.gz'   : Enum__S3__Object__Format.GZIP,
            '.zip'  : Enum__S3__Object__Format.ZIP,
            '.tar'  : Enum__S3__Object__Format.GZIP,
            '.log'  : Enum__S3__Object__Format.TEXT,
            '.txt'  : Enum__S3__Object__Format.TEXT,
        }
        return ext_map.get(ext, Enum__S3__Object__Format.TEXT)

    def sniff_content(self, header: bytes) -> Enum__S3__Object__Format:          # content-sniff on first 512 bytes
        if not header:
            return Enum__S3__Object__Format.TEXT
        if header[:2] == b'\x1f\x8b':
            return Enum__S3__Object__Format.GZIP
        if header[:4] == b'PK\x03\x04':
            return Enum__S3__Object__Format.ZIP
        try:
            text = header.decode('utf-8', errors='strict')
        except UnicodeDecodeError:
            return Enum__S3__Object__Format.BINARY
        stripped = text.lstrip()
        if stripped.startswith('{') or stripped.startswith('['):
            return Enum__S3__Object__Format.JSON
        if stripped.startswith('---'):
            return Enum__S3__Object__Format.YAML
        first_line = stripped.split('\n')[0] if '\n' in stripped else stripped
        if ',' in first_line or '\t' in first_line:
            return Enum__S3__Object__Format.CSV
        return Enum__S3__Object__Format.TEXT

    def detect(self, key: str, header: bytes = b'',
               raw: bool = False) -> Enum__S3__Object__Format:
        if raw:
            return Enum__S3__Object__Format.TEXT
        fmt = self.detect_from_key(key)
        if fmt == Enum__S3__Object__Format.TEXT and header:
            fmt = self.sniff_content(header)
        return fmt
