# ═══════════════════════════════════════════════════════════════════════════════
# Tests — ECR__Prune__Planner
# PURE planner tests — no AWS, no boto3, no in-memory client. The planner
# operates entirely on Schema__ECR__Image lists.
# ═══════════════════════════════════════════════════════════════════════════════

from datetime import datetime, timedelta, timezone

from sgraph_ai_service_playwright__cli.aws.ecr.collections.List__Schema__ECR__Image import List__Schema__ECR__Image
from sgraph_ai_service_playwright__cli.aws.ecr.primitives.Safe_Str__ECR__Image_Digest import Safe_Str__ECR__Image_Digest
from sgraph_ai_service_playwright__cli.aws.ecr.primitives.Safe_Str__ECR__Repo_Name    import Safe_Str__ECR__Repo_Name
from sgraph_ai_service_playwright__cli.aws.ecr.primitives.Safe_Str__ECR__Tag          import Safe_Str__ECR__Tag
from sgraph_ai_service_playwright__cli.aws.ecr.schemas.Schema__ECR__Image             import Schema__ECR__Image
from sgraph_ai_service_playwright__cli.aws.ecr.service.ECR__Prune__Planner            import ECR__Prune__Planner


_NOW = datetime(2026, 5, 18, 12, 0, 0, tzinfo=timezone.utc)


def _img(name: str, tags=None, days_ago: int = 0, size: int = 1024) -> Schema__ECR__Image:
    tags_safe = [Safe_Str__ECR__Tag(t) for t in (tags or []) if t]
    pushed    = (_NOW - timedelta(days=days_ago)).isoformat()
    digest    = f'sha256:{name:0>64}'[:71]                                       # pad to a valid-ish digest length
    return Schema__ECR__Image(
        repo_name           = Safe_Str__ECR__Repo_Name('test-repo'),
        digest              = Safe_Str__ECR__Image_Digest(digest),
        tags                = tags_safe,
        size_bytes          = size,
        pushed_at           = pushed,
        manifest_media_type = '',
    )


def _images(*items) -> List__Schema__ECR__Image:
    lst = List__Schema__ECR__Image()
    for it in items:
        lst.append(it)
    return lst


class Test__ECR__Prune__Planner:

    # ── empty / null ─────────────────────────────────────────────────────────

    def test_1__empty_list(self):
        plan = ECR__Prune__Planner().plan(_images(), now=_NOW)
        assert len(plan.to_delete) == 0
        assert plan.kept_count     == 0
        assert 'untagged=False'    in plan.policy_summary

    def test_2__no_policy_deletes_all(self):
        imgs = _images(_img('a', tags=['v1']), _img('b', tags=['v2']))
        plan = ECR__Prune__Planner().plan(imgs, now=_NOW)
        assert len(plan.to_delete) == 2
        assert plan.kept_count     == 0

    # ── untagged ─────────────────────────────────────────────────────────────

    def test_3__untagged_only(self):
        imgs = _images(_img('a', tags=['v1']),
                       _img('b', tags=[]),
                       _img('c', tags=[]))
        plan = ECR__Prune__Planner().plan(imgs, untagged=True, now=_NOW)
        assert len(plan.to_delete) == 2
        assert all(not list(i.tags) for i in plan.to_delete)
        assert plan.kept_count     == 1

    # ── --older ──────────────────────────────────────────────────────────────

    def test_4__older_filter(self):
        imgs = _images(_img('a', tags=['old'], days_ago=60),
                       _img('b', tags=['new'], days_ago=5))
        plan = ECR__Prune__Planner().plan(imgs, older_than=timedelta(days=30), now=_NOW)
        assert len(plan.to_delete) == 1
        assert 'old' in [str(t) for t in plan.to_delete[0].tags]
        assert plan.kept_count == 1

    def test_5__older_all_too_young(self):
        imgs = _images(_img('a', tags=['v1'], days_ago=5),
                       _img('b', tags=['v2'], days_ago=10))
        plan = ECR__Prune__Planner().plan(imgs, older_than=timedelta(days=30), now=_NOW)
        assert len(plan.to_delete) == 0
        assert plan.kept_count     == 2

    def test_6__older_skips_unparseable_pushed_at(self):
        imgs = _images(_img('a', tags=['v1'], days_ago=60))
        imgs[0].pushed_at = ''                                                   # unparseable → safety, never delete
        plan = ECR__Prune__Planner().plan(imgs, older_than=timedelta(days=30), now=_NOW)
        assert len(plan.to_delete) == 0

    # ── --keep-last ──────────────────────────────────────────────────────────

    def test_7__keep_last_protects_newest_tagged(self):
        imgs = _images(_img('a', tags=['v1'], days_ago=30),
                       _img('b', tags=['v2'], days_ago=20),
                       _img('c', tags=['v3'], days_ago=10))
        plan = ECR__Prune__Planner().plan(imgs, keep_last=1, now=_NOW)
        # newest tagged (v3, days_ago=10) protected → deletes v1, v2
        tags = sorted([str(t) for img in plan.to_delete for t in img.tags])
        assert tags == ['v1', 'v2']
        assert plan.kept_count == 1

    def test_8__keep_last_more_than_total(self):
        imgs = _images(_img('a', tags=['v1'], days_ago=1),
                       _img('b', tags=['v2'], days_ago=2))
        plan = ECR__Prune__Planner().plan(imgs, keep_last=10, now=_NOW)
        assert len(plan.to_delete) == 0
        assert plan.kept_count     == 2

    def test_9__keep_last_does_not_protect_untagged(self):
        imgs = _images(_img('a', tags=[],    days_ago=1),
                       _img('b', tags=['v1'], days_ago=2))
        plan = ECR__Prune__Planner().plan(imgs, untagged=True, keep_last=5, now=_NOW)
        # untagged-only candidate pool; keep_last only protects tagged → untagged still gets deleted
        assert len(plan.to_delete) == 1
        assert not list(plan.to_delete[0].tags)

    # ── combinations ─────────────────────────────────────────────────────────

    def test_10__untagged_and_older(self):
        imgs = _images(_img('a', tags=[],    days_ago=60),
                       _img('b', tags=[],    days_ago=5),
                       _img('c', tags=['v1'], days_ago=60))
        plan = ECR__Prune__Planner().plan(imgs, untagged=True,
                                          older_than=timedelta(days=30), now=_NOW)
        # only untagged AND old → just image 'a'
        assert len(plan.to_delete) == 1
        assert not list(plan.to_delete[0].tags)

    def test_11__keep_last_and_older(self):
        imgs = _images(_img('a', tags=['v1'], days_ago=60),
                       _img('b', tags=['v2'], days_ago=50),
                       _img('c', tags=['v3'], days_ago=10))
        plan = ECR__Prune__Planner().plan(imgs, older_than=timedelta(days=30),
                                          keep_last=1, now=_NOW)
        # v3 (newest) protected; v1+v2 are >30d old → deleted
        tags = sorted([str(t) for img in plan.to_delete for t in img.tags])
        assert tags == ['v1', 'v2']

    # ── policy summary ───────────────────────────────────────────────────────

    def test_12__policy_summary_formatting(self):
        plan = ECR__Prune__Planner().plan(_images(),
                                          untagged   = True,
                                          older_than = timedelta(days=30),
                                          keep_last  = 5,
                                          now        = _NOW)
        assert 'untagged=True' in plan.policy_summary
        assert 'older=30d'     in plan.policy_summary
        assert 'keep_last=5'   in plan.policy_summary
