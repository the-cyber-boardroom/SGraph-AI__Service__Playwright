# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — firehose: Firehose__Render
# Pure text rendering for the firehose read commands and for reuse by the CF
# architecture view. No rich, no textual — testable plainly. Renders a stream list
# and one stream's detail, both keyed on the resolved S3 destination.
# ═══════════════════════════════════════════════════════════════════════════════

from sgraph_ai_service_playwright__cli.aws.firehose.schemas.Schema__Firehose__Stream import Schema__Firehose__Stream


def streams_plain(streams) -> str:
    if not streams:
        return 'No delivery streams (or no read access).'
    out = ['NAME                                STATUS    TYPE         DESTINATION']
    for s in streams:
        dest = f's3://{s.destination_bucket}/{s.destination_prefix}' if s.destination_bucket else '-'
        out.append(f'{s.name[:34].ljust(34)}  {s.status[:8].ljust(8)}  {s.stream_type[:11].ljust(11)}  {dest}')
    return '\n'.join(out)


def stream_detail_plain(stream : Schema__Firehose__Stream) -> str:
    if stream is None:
        return 'Stream not found (or no read access).'
    return '\n'.join([f'name        : {stream.name}',
                      f'status      : {stream.status}',
                      f'type        : {stream.stream_type}',
                      f'created     : {stream.created}',
                      f'destination : s3://{stream.destination_bucket}/{stream.destination_prefix}',
                      f'arn         : {stream.arn}'])
