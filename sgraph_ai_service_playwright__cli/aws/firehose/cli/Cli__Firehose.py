# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Cli__Firehose
# `sg aws firehose *` — read-only Amazon Data Firehose surface (no CRUD by design):
#   sg aws firehose ls                    [--region R] [--json]
#   sg aws firehose describe <name>       [--region R] [--json]
# Completes the "retrieve everything relevant to the CF logging solution" picture —
# the delivery stream(s) and the S3 destination they write to. The client seam is a
# factory tests replace (no AWS, no mocks).
# ═══════════════════════════════════════════════════════════════════════════════

import json

import typer

from sgraph_ai_service_playwright__cli.aws.firehose.cli.Firehose__Render import streams_plain, stream_detail_plain

app = typer.Typer(name='firehose', help='Amazon Data Firehose — read-only (delivery streams + S3 destinations).',
                  no_args_is_help=True)

_client_factory = None                                                               # tests assign a callable(region) → Firehose__AWS__Client

REGION = typer.Option('', '--region', '-r', help='AWS region')
JSON   = typer.Option(False, '--json', help='Emit JSON')


def _client(region : str):
    if _client_factory is not None:
        return _client_factory(region)
    from sgraph_ai_service_playwright__cli.aws.firehose.service.Firehose__AWS__Client import Firehose__AWS__Client
    return Firehose__AWS__Client(region=region)


@app.command('ls', help='List delivery streams and their resolved S3 destinations.')
def ls(region : str = REGION, json_out : bool = JSON):
    streams = _client(region).streams()
    if json_out:
        print(json.dumps([s.json() for s in streams], indent=2, default=str))
        return
    print(streams_plain(streams))


@app.command('describe', help='Describe one delivery stream (status, type, S3 destination, ARN).')
def describe(name : str = typer.Argument(..., help='Delivery stream name'),
             region : str = REGION, json_out : bool = JSON):
    stream = _client(region).describe_delivery_stream(name)
    if json_out:
        print(json.dumps(stream.json() if stream is not None else {}, indent=2, default=str))
        return
    print(stream_detail_plain(stream))
