# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — cf tui: CF_TUI__Arch_Source
# Builds the deployed-architecture snapshot by enumerating live AWS state through the
# existing `sg aws` clients: CloudFront distributions, the CF-logs S3 bucket, and
# CloudWatch log groups. Each read is wrapped so a missing credential/permission
# yields a partial snapshot with an honest error string — never a crash. Firehose is
# NOT enumerated (no sg aws support) and is rendered as an inferred, UNVERIFIED hop.
# The three clients are injected (Type_Safe defaults) — tests pass subclasses that
# override the list methods, so this runs with no AWS and no mocks.
# ═══════════════════════════════════════════════════════════════════════════════

import time

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe

from sgraph_ai_service_playwright__cli.aws.cf.service.CloudFront__AWS__Client        import CloudFront__AWS__Client
from sgraph_ai_service_playwright__cli.aws.firehose.service.Firehose__AWS__Client     import Firehose__AWS__Client
from sgraph_ai_service_playwright__cli.aws.logs.service.Logs__AWS__Client            import Logs__AWS__Client
from sgraph_ai_service_playwright__cli.aws.s3.service.S3__AWS__Client                import S3__AWS__Client
from sgraph_ai_service_playwright__cli.elastic.lets.cf.tui.cf_tui__config            import CF_LOGS_BUCKET, CF_LOGS_PREFIX
from sgraph_ai_service_playwright__cli.elastic.lets.cf.tui.schemas.Schema__CF_TUI__Arch_Distribution import Schema__CF_TUI__Arch_Distribution
from sgraph_ai_service_playwright__cli.elastic.lets.cf.tui.schemas.Schema__CF_TUI__Arch_Log_Group    import Schema__CF_TUI__Arch_Log_Group
from sgraph_ai_service_playwright__cli.elastic.lets.cf.tui.schemas.Schema__CF_TUI__Arch_Snapshot      import Schema__CF_TUI__Arch_Snapshot


def _v(x) -> str:
    return x.value if hasattr(x, 'value') else str(x)


class CF_TUI__Arch_Source(Type_Safe):
    cf_client       : CloudFront__AWS__Client
    logs_client     : Logs__AWS__Client
    s3_client       : S3__AWS__Client
    firehose_client : Firehose__AWS__Client
    bucket          : str = CF_LOGS_BUCKET
    log_prefix      : str                                                            # '' = all log groups

    def label(self) -> str:
        return f's3://{self.bucket}  ·  cloudfront + cloudwatch (sg aws)'

    def snapshot(self) -> Schema__CF_TUI__Arch_Snapshot:
        snap = Schema__CF_TUI__Arch_Snapshot(captured_at=int(time.time()), bucket_name=self.bucket)

        try:
            for d in self.cf_client.list_distributions():
                snap.distributions.append(Schema__CF_TUI__Arch_Distribution(
                    distribution_id = str(d.distribution_id),
                    domain          = str(d.domain_name),
                    aliases         = ', '.join(str(a) for a in d.aliases),
                    status          = _v(d.status),
                    enabled         = bool(d.enabled)))
        except Exception as exc:
            snap.cf_error = str(exc)[:140]

        try:
            for g in self.logs_client.list_log_groups(self.log_prefix):
                snap.log_groups.append(Schema__CF_TUI__Arch_Log_Group(
                    name=str(g.name), retention_days=int(g.retention_days), stored_bytes=int(g.stored_bytes)))
        except Exception as exc:
            snap.logs_error = str(exc)[:140]

        try:
            resp = self.s3_client.list_objects(self.bucket, prefix=CF_LOGS_PREFIX, recursive=False)
            snap.bucket_reachable   = True
            snap.bucket_top_folders = len(resp.prefixes)
        except Exception as exc:
            snap.s3_error = str(exc)[:140]

        try:
            for stream in self.firehose_client.streams():
                snap.firehose_streams.append(stream)
        except Exception as exc:
            snap.firehose_error = str(exc)[:140]

        return snap
