# ═══════════════════════════════════════════════════════════════════════════════
# Host Control Plane — Image__Runtime__Docker
# Docker CLI adapter for image management. All operations shell out to the
# `docker` binary — no docker-py SDK, matching the Pod__Runtime__Docker pattern.
# ═══════════════════════════════════════════════════════════════════════════════

from __future__ import annotations   # defer annotation eval — class defines a method named 'list' which would shadow the builtin at annotation evaluation time

import json
import subprocess

from sg_compute.host_plane.images.schemas.Schema__Image__Info          import Schema__Image__Info
from sg_compute.host_plane.images.schemas.Schema__Image__List          import Schema__Image__List, List__Schema__Image__Info
from sg_compute.host_plane.images.schemas.Schema__Image__Load__Response import Schema__Image__Load__Response
from sg_compute.host_plane.images.schemas.Schema__Image__Remove__Response import Schema__Image__Remove__Response

FORMAT = '{{json .}}'


def _bytes_to_mb(raw: int | float) -> float:
    try:
        return round(float(raw) / (1024 * 1024), 1)
    except (TypeError, ValueError):
        return 0.0


class Image__Runtime__Docker:

    def _run(self, args: list[str], timeout: int = 300) -> tuple[str, str, int]:
        result = subprocess.run(['docker'] + args, capture_output=True, text=True, timeout=timeout)
        return result.stdout, result.stderr, result.returncode

    def list(self) -> Schema__Image__List:
        stdout, _, _ = self._run(['images', '--no-trunc', '--format', FORMAT])
        items = List__Schema__Image__Info()
        seen  = set()
        for line in stdout.strip().splitlines():
            if not line:
                continue
            try:
                d = json.loads(line)
            except json.JSONDecodeError:
                continue
            img_id = (d.get('ID') or '')[:12]
            tag    = f'{d.get("Repository", "<none>")}:{d.get("Tag", "<none>")}'
            if img_id in seen:
                for item in items:
                    if item.id == img_id:
                        item.tags.append(tag)
                        break
            else:
                seen.add(img_id)
                size_raw = d.get('Size', 0)
                try:
                    size_bytes = int(size_raw)
                except (TypeError, ValueError):
                    size_bytes = 0
                items.append(Schema__Image__Info(
                    id         = img_id,
                    tags       = [tag],
                    size_mb    = _bytes_to_mb(size_bytes),
                    created_at = d.get('CreatedAt', '') or '',
                ))
        return Schema__Image__List(images=items, count=len(items))

    def inspect(self, name: str) -> Schema__Image__Info | None:
        stdout, _, rc = self._run(['inspect', '--format', '{{json .}}', name])
        if rc != 0 or not stdout.strip():
            return None
        try:
            d = json.loads(stdout.strip())
        except json.JSONDecodeError:
            return None
        if isinstance(d, list):
            if not d:
                return None
            d = d[0]
        tags = d.get('RepoTags') or []
        return Schema__Image__Info(
            id         = (d.get('Id', '') or '')[:12].replace('sha256:', ''),
            tags       = tags,
            size_mb    = _bytes_to_mb(d.get('Size', 0)),
            created_at = d.get('Created', '') or '',
        )

    def load(self, path: str) -> Schema__Image__Load__Response:
        stdout, stderr, rc = self._run(['load', '-i', path], timeout=600)
        return Schema__Image__Load__Response(
            loaded = rc == 0,
            output = stdout.strip(),
            error  = stderr.strip() if rc != 0 else '',
        )

    def load_from_s3(self, bucket: str, key: str, tmp_path: str) -> Schema__Image__Load__Response:
        s3_uri = f's3://{bucket}/{key}'
        dl_out, dl_err, dl_rc = self._run_aws(['s3', 'cp', s3_uri, tmp_path], timeout=600)
        if dl_rc != 0:
            return Schema__Image__Load__Response(
                loaded = False,
                output = dl_out.strip(),
                error  = dl_err.strip() or f'failed to download {s3_uri}',
            )
        return self.load(tmp_path)

    def _run_aws(self, args: list[str], timeout: int = 600) -> tuple[str, str, int]:
        result = subprocess.run(['aws'] + args, capture_output=True, text=True, timeout=timeout)
        return result.stdout, result.stderr, result.returncode

    def remove(self, name: str) -> Schema__Image__Remove__Response:
        _, stderr, rc = self._run(['rmi', name])
        return Schema__Image__Remove__Response(
            name    = name,
            removed = rc == 0,
            error   = stderr.strip() if rc != 0 else '',
        )
