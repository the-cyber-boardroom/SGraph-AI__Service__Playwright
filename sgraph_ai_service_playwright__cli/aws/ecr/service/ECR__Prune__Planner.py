# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI aws/ecr — ECR__Prune__Planner
# PURE planner — no boto3, no AWS calls. Decides which images would be deleted
# under the given prune policy. Used by `sg aws ecr prune`.
#
# Policy semantics:
#   - untagged=True   → candidate pool = images with empty `tags`
#   - untagged=False  → candidate pool = ALL images
#   - keep_last       → from the TAGGED-image pool (sorted pushed_at DESC),
#                       protect the first N. Untagged images are NEVER
#                       protected by keep_last — when untagged=True they are
#                       always fair game.
#   - older_than      → candidate must satisfy now - pushed_at >= older_than.
#                       Images with empty / unparseable pushed_at are NEVER
#                       deleted by --older (safety).
# ═══════════════════════════════════════════════════════════════════════════════

from datetime import datetime, timedelta, timezone
from typing   import Optional

from osbot_utils.type_safe.Type_Safe import Type_Safe

from sgraph_ai_service_playwright__cli.aws.ecr.collections.List__Schema__ECR__Image import List__Schema__ECR__Image
from sgraph_ai_service_playwright__cli.aws.ecr.primitives.Safe_Str__ECR__Repo_Name  import Safe_Str__ECR__Repo_Name
from sgraph_ai_service_playwright__cli.aws.ecr.schemas.Schema__ECR__Image            import Schema__ECR__Image
from sgraph_ai_service_playwright__cli.aws.ecr.schemas.Schema__ECR__Prune__Plan      import Schema__ECR__Prune__Plan


class ECR__Prune__Planner(Type_Safe):

    def plan(self, images          : List__Schema__ECR__Image,
                   untagged        : bool                = False,
                   older_than      : Optional[timedelta] = None,
                   keep_last       : int                 = 0,
                   now             : Optional[datetime]  = None,
                   repo_name       : str                 = '',
             ) -> Schema__ECR__Prune__Plan:
        # ── normalise inputs ─────────────────────────────────────────────────
        now           = now or datetime.now(timezone.utc)
        all_images    = list(images or [])
        total         = len(all_images)
        repo_name_str = repo_name or (str(all_images[0].repo_name) if all_images else '')

        # ── candidate selection ──────────────────────────────────────────────
        if untagged:
            candidates = [img for img in all_images if not list(img.tags)]
        else:
            candidates = list(all_images)

        # ── protect the most-recent keep_last TAGGED images ──────────────────
        protected_digests = set()
        if keep_last and keep_last > 0:
            tagged    = [img for img in all_images if list(img.tags)]
            tagged.sort(key=lambda i: self._sort_key(i), reverse=True)
            protected = tagged[:keep_last]
            protected_digests = {str(img.digest) for img in protected if str(img.digest)}

        candidates = [img for img in candidates if str(img.digest) not in protected_digests]

        # ── --older filter (safety: skip images with no parseable pushed_at) ─
        if older_than is not None:
            kept_after_age = []
            for img in candidates:
                pushed_dt = self._parse_pushed_at(str(img.pushed_at))
                if pushed_dt is None:
                    continue                                                     # safety — never delete unknown-age images
                if pushed_dt.tzinfo is None:
                    pushed_dt = pushed_dt.replace(tzinfo=timezone.utc)
                if (now - pushed_dt) >= older_than:
                    kept_after_age.append(img)
            candidates = kept_after_age

        # ── build result ─────────────────────────────────────────────────────
        to_delete = List__Schema__ECR__Image()
        for img in candidates:
            to_delete.append(img)
        kept_count     = total - len(to_delete)
        policy_summary = self._summarise(untagged=untagged, older_than=older_than, keep_last=keep_last)
        return Schema__ECR__Prune__Plan(
            repo_name      = Safe_Str__ECR__Repo_Name(repo_name_str) if repo_name_str else Safe_Str__ECR__Repo_Name(''),
            to_delete      = to_delete,
            kept_count     = kept_count,
            policy_summary = policy_summary,
        )

    # ── internal ─────────────────────────────────────────────────────────────

    def _parse_pushed_at(self, s: str) -> Optional[datetime]:
        if not s:
            return None
        try:
            return datetime.fromisoformat(s)
        except ValueError:
            return None

    def _sort_key(self, img: Schema__ECR__Image):                                # tuple sort: (has_parseable_date, datetime, raw string)
        dt = self._parse_pushed_at(str(img.pushed_at))
        if dt is None:
            return (0, datetime.min.replace(tzinfo=timezone.utc), str(img.pushed_at))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return (1, dt, str(img.pushed_at))

    def _summarise(self, untagged: bool, older_than: Optional[timedelta], keep_last: int) -> str:
        parts = [f'untagged={untagged}']
        if older_than is not None:
            parts.append(f'older={self._fmt_delta(older_than)}')
        if keep_last:
            parts.append(f'keep_last={keep_last}')
        return ', '.join(parts)

    def _fmt_delta(self, td: timedelta) -> str:
        total = int(td.total_seconds())
        if total % 86400 == 0:
            return f'{total // 86400}d'
        if total % 3600 == 0:
            return f'{total // 3600}h'
        if total % 60 == 0:
            return f'{total // 60}m'
        return f'{total}s'
