# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI aws/lab — Lab__Tagger
# Extends _shared/Aws__Tagger with five sg:lab:* tags.
# Total per resource: 5 canonical sg:* tags + 5 sg:lab:* tags = 10 tags.
# ═══════════════════════════════════════════════════════════════════════════════

from datetime import datetime, timezone, timedelta

from sgraph_ai_service_playwright__cli.aws._shared.Aws__Tagger                           import Aws__Tagger
from sgraph_ai_service_playwright__cli.aws._shared.collections.List__Schema__AWS__Tag    import List__Schema__AWS__Tag
from sgraph_ai_service_playwright__cli.aws._shared.enums.Enum__AWS__Surface              import Enum__AWS__Surface
from sgraph_ai_service_playwright__cli.aws._shared.primitives.Safe_Str__AWS__Tag_Key     import Safe_Str__AWS__Tag_Key
from sgraph_ai_service_playwright__cli.aws._shared.primitives.Safe_Str__AWS__Tag_Value   import Safe_Str__AWS__Tag_Value
from sgraph_ai_service_playwright__cli.aws._shared.schemas.Schema__AWS__Tag              import Schema__AWS__Tag
from sgraph_ai_service_playwright__cli.aws.lab.enums.Enum__Lab__Resource_Type            import Enum__Lab__Resource_Type


_DEFAULT_TTL_MINUTES = 60                                                          # sweeper hard limit: 60-min default TTL


class Lab__Tagger(Aws__Tagger):

    def lab_tags_for(self,
                     run_id          : str,
                     experiment_name : str,
                     resource_type   : Enum__Lab__Resource_Type,
                     ttl_minutes     : int = _DEFAULT_TTL_MINUTES) -> List__Schema__AWS__Tag:
        base_tags  = self.tags_for(Enum__AWS__Surface.LAB, 'lab-create')
        lab_tags   = self._lab_specific_tags(run_id, experiment_name, resource_type, ttl_minutes)
        combined   = List__Schema__AWS__Tag(items=list(base_tags.items) + list(lab_tags.items))
        return combined

    def as_boto3_lab_tags(self,
                          run_id          : str,
                          experiment_name : str,
                          resource_type   : Enum__Lab__Resource_Type,
                          ttl_minutes     : int = _DEFAULT_TTL_MINUTES) -> list:
        tags = self.lab_tags_for(run_id, experiment_name, resource_type, ttl_minutes)
        return [{'Key': str(t.key), 'Value': str(t.value)} for t in tags.items]

    # ── private ───────────────────────────────────────────────────────────────

    def _lab_specific_tags(self,
                           run_id          : str,
                           experiment_name : str,
                           resource_type   : Enum__Lab__Resource_Type,
                           ttl_minutes     : int) -> List__Schema__AWS__Tag:
        expires_at = (datetime.now(timezone.utc) + timedelta(minutes=ttl_minutes)).strftime('%Y-%m-%dT%H:%M:%SZ')
        items = [
            self._tag('sg:lab',             'true'),
            self._tag('sg:lab:run-id',      run_id),
            self._tag('sg:lab:experiment',  experiment_name),
            self._tag('sg:lab:resource',    resource_type.value if resource_type else ''),
            self._tag('sg:lab:expires-at',  expires_at),
        ]
        return List__Schema__AWS__Tag(items=items)
