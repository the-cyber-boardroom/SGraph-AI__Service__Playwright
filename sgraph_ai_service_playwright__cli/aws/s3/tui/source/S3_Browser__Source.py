# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — s3 tui: S3_Browser__Source
# The seam the generic S3 browser reads through. Wraps the existing S3__AWS__Client
# (the sole boto3 boundary) + S3__Format__Detector: list buckets, list a prefix
# (folders + files via Delimiter), and read one object into a decoded preview
# (gunzipping .gz, hex-dumping binary, capping size). Read-only. The client is
# injected — tests subclass S3__AWS__Client to return fixtures, so this runs with no
# AWS and no mocks.
# ═══════════════════════════════════════════════════════════════════════════════

import gzip

from osbot_utils.type_safe.Type_Safe                                              import Type_Safe

from sgraph_ai_service_playwright__cli.aws.s3.enums.Enum__S3__Object__Format       import Enum__S3__Object__Format
from sgraph_ai_service_playwright__cli.aws.s3.service.S3__AWS__Client              import S3__AWS__Client
from sgraph_ai_service_playwright__cli.aws.s3.service.S3__Format__Detector         import S3__Format__Detector
from sgraph_ai_service_playwright__cli.aws.s3.tui.schemas.List__S3_Browser__Entry  import List__S3_Browser__Entry
from sgraph_ai_service_playwright__cli.aws.s3.tui.schemas.Schema__S3_Browser__Entry import Schema__S3_Browser__Entry
from sgraph_ai_service_playwright__cli.aws.s3.tui.schemas.Schema__S3_Browser__View  import Schema__S3_Browser__View


def _label(fmt) -> str:
    return (fmt.value if hasattr(fmt, 'value') else str(fmt)).lower()


class S3_Browser__Source(Type_Safe):
    client            : S3__AWS__Client
    detector          : S3__Format__Detector
    max_preview_bytes : int = 262144                                                 # 256 KB preview cap

    def list_buckets(self) -> List__S3_Browser__Entry:
        entries = List__S3_Browser__Entry()
        for b in self.client.list_buckets():
            name = str(b.name)
            entries.append(Schema__S3_Browser__Entry(name=name, kind='bucket', bucket=name, path=name))
        return entries

    def list_dir(self, bucket : str, prefix : str = '') -> List__S3_Browser__Entry:
        resp    = self.client.list_objects(bucket, prefix=prefix, recursive=False)
        entries = List__S3_Browser__Entry()
        for pfx in resp.prefixes:
            pfx_str = str(pfx)
            name    = pfx_str[len(prefix):].rstrip('/')
            entries.append(Schema__S3_Browser__Entry(name=name + '/', kind='folder', bucket=bucket, path=pfx_str))
        for obj in resp.objects:
            key = str(obj.key)
            if key == prefix:                                                        # the folder-marker object itself
                continue
            entries.append(Schema__S3_Browser__Entry(name=key[len(prefix):], kind='file', bucket=bucket, path=key,
                                                     size_bytes=int(obj.size), last_modified=str(obj.last_modified)))
        return entries

    def read_object(self, bucket : str, key : str) -> Schema__S3_Browser__View:
        raw  = self.client.get_object_body(bucket, key)
        view = Schema__S3_Browser__View(bucket=bucket, key=key, size_bytes=len(raw))
        fmt  = self.detector.detect(key, header=raw[:512])
        data = raw

        if fmt == Enum__S3__Object__Format.GZIP:
            try:
                data          = gzip.decompress(raw)
                view.gunzipped = True
                inner_key      = key[:-3] if key.endswith('.gz') else key
                fmt            = self.detector.detect(inner_key, header=data[:512])
            except Exception:
                data = raw

        view.truncated = len(data) > self.max_preview_bytes
        clipped        = data[:self.max_preview_bytes]
        try:
            view.text = clipped.decode('utf-8')
            view.fmt  = _label(fmt)
        except UnicodeDecodeError:
            view.is_binary = True
            view.fmt       = 'binary'
            view.text      = self.hexdump(clipped[:1024])
        return view

    def hexdump(self, data : bytes) -> str:
        lines = []
        for offset in range(0, len(data), 16):
            chunk = data[offset:offset + 16]
            hexs  = ' '.join(f'{b:02x}' for b in chunk)
            text  = ''.join(chr(b) if 32 <= b < 127 else '.' for b in chunk)
            lines.append(f'{offset:08x}  {hexs.ljust(47)}  {text}')
        return '\n'.join(lines)
