# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — aws/s3/tui_api: S3__Tui_Api__Provider
# The first real TUI API provider: read-only S3 over the existing S3__AWS__Client.
# Inject S3__AWS__Client__In_Memory (or a fake subclass) for no-mock tests. Mutating
# actions are out of scope here (READ_ONLY tier only); WRITE+ arrive with the gate (B3).
# ═══════════════════════════════════════════════════════════════════════════════

import os

from sgraph_ai_service_playwright__cli.aws.s3.service.S3__AWS__Client                       import S3__AWS__Client
from sgraph_ai_service_playwright__cli.aws.s3.tui_api.schemas.Schema__S3__Params__Head_Object import Schema__S3__Params__Head_Object
from sgraph_ai_service_playwright__cli.aws.s3.tui_api.schemas.Schema__S3__Params__List_Objects import Schema__S3__Params__List_Objects
from sgraph_ai_service_playwright__cli.tui.tool_api.enums.Enum__Tui_Api__Change_Kind        import Enum__Tui_Api__Change_Kind
from sgraph_ai_service_playwright__cli.tui.tool_api.enums.Enum__Tui_Api__Tier               import Enum__Tui_Api__Tier
from sgraph_ai_service_playwright__cli.tui.tool_api.schemas.Schema__Tui_Api__Orientation    import Schema__Tui_Api__Orientation
from sgraph_ai_service_playwright__cli.tui.tool_api.service.Tui_Api__Change_Log             import Tui_Api__Change_Log
from sgraph_ai_service_playwright__cli.tui.tool_api.schemas.List__Tui_Api__Action            import List__Tui_Api__Action
from sgraph_ai_service_playwright__cli.tui.tool_api.schemas.List__Tui_Api__Tier              import List__Tui_Api__Tier
from sgraph_ai_service_playwright__cli.tui.tool_api.schemas.Schema__Tui_Api__Action          import Schema__Tui_Api__Action
from sgraph_ai_service_playwright__cli.tui.tool_api.schemas.Schema__Tui_Api__Manifest        import Schema__Tui_Api__Manifest
from sgraph_ai_service_playwright__cli.tui.tool_api.schemas.Schema__Tui_Api__Scope           import Schema__Tui_Api__Scope
from sgraph_ai_service_playwright__cli.tui.tool_api.schemas.Schema__Tui_Api__Skills          import Schema__Tui_Api__Skills
from sgraph_ai_service_playwright__cli.tui.tool_api.schemas.Schema__Tui_Api__Result          import Schema__Tui_Api__Result
from sgraph_ai_service_playwright__cli.tui.tool_api.service.Tui_Api__Provider               import Tui_Api__Provider
from sgraph_ai_service_playwright__cli.tui.tool_api.service.Tui_Api__Schema__Builder         import Tui_Api__Schema__Builder


class S3__Tui_Api__Provider(Tui_Api__Provider):
    client  : S3__AWS__Client                                                     # inject an in-memory/fake subclass in tests
    builder : Tui_Api__Schema__Builder

    def manifest(self) -> Schema__Tui_Api__Manifest:
        scope_read = Schema__Tui_Api__Scope(api='sg-aws.s3', capability='read')

        actions = List__Tui_Api__Action()
        actions.append(Schema__Tui_Api__Action(name='list_buckets', tier=Enum__Tui_Api__Tier.READ_ONLY,
                                               description='List all S3 buckets in the account.',
                                               scope=scope_read, input_schema={'type': 'object', 'properties': {}}))
        actions.append(Schema__Tui_Api__Action(name='list_objects', tier=Enum__Tui_Api__Tier.READ_ONLY,
                                               description='List objects under a bucket (optionally a prefix).',
                                               scope=scope_read,
                                               input_schema=self.builder.input_schema(Schema__S3__Params__List_Objects)))
        actions.append(Schema__Tui_Api__Action(name='head_object', tier=Enum__Tui_Api__Tier.READ_ONLY,
                                               description='Stat one object: size, etag, content-type, storage class.',
                                               scope=scope_read,
                                               input_schema=self.builder.input_schema(Schema__S3__Params__Head_Object)))

        tiers = List__Tui_Api__Tier()
        tiers.append(Enum__Tui_Api__Tier.READ_ONLY)

        return Schema__Tui_Api__Manifest(slug        = 'sg-aws.s3',
                                        tool        = 'sg-aws',
                                        name        = 'S3 (read-only)',
                                        version     = '0.1.0',
                                        description = 'Read-only Amazon S3: list buckets, list objects, stat an object.',
                                        tiers       = tiers,
                                        actions     = actions,
                                        skills      = Schema__Tui_Api__Skills())

    def orientation(self) -> Schema__Tui_Api__Orientation:
        change_log = Tui_Api__Change_Log()
        change_log.add(Enum__Tui_Api__Change_Kind.FEATURE,
                       'Read-only S3 TUI API: list_buckets, list_objects, head_object.', '0.1.0')
        return Schema__Tui_Api__Orientation(tool='sg-aws',
                                          status={'healthy': True, 'note': 'read-only; credentials from the active sg context'},
                                          recent_changes=change_log.changes)

    def skills(self) -> dict:
        here = os.path.join(os.path.dirname(__file__), 'skills')
        out  = {}
        for audience, filename in (('human', 'SKILL-human.md'), ('api', 'SKILL-api.md'), ('driver', 'SKILL-driver.md')):
            path = os.path.join(here, filename)
            if os.path.exists(path):
                with open(path, encoding='utf-8') as handle:
                    out[audience] = handle.read()
        return out

    def dispatch(self, action: str, params: dict) -> Schema__Tui_Api__Result:
        try:
            if   action == 'list_buckets':
                data = [bucket.json() for bucket in self.client.list_buckets()]
            elif action == 'list_objects':
                p    = Schema__S3__Params__List_Objects(**params)
                data = self.client.list_objects(bucket=str(p.bucket), prefix=str(p.prefix),
                                                recursive=bool(p.recursive)).json()
            elif action == 'head_object':
                p    = Schema__S3__Params__Head_Object(**params)
                stat = self.client.head_object(bucket=str(p.bucket), key=str(p.key))
                data = stat.json() if stat is not None else {}
            else:
                return Schema__Tui_Api__Result(ok=False, error=f'unknown action: {action}')
        except Exception as exc:
            return Schema__Tui_Api__Result(ok=False, error=f'{type(exc).__name__}: {exc}')
        return Schema__Tui_Api__Result(ok=True, data={'result': data})
