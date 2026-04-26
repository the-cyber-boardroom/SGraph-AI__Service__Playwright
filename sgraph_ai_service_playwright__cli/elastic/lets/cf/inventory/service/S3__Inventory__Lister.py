# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — S3__Inventory__Lister
# Single boto3 boundary for `s3:ListObjectsV2`. Two responsibilities:
#   1. paginate(bucket, prefix, max_keys, region) → (objects, pages_listed)
#      Returns every object under the prefix as a list of dicts (Key,
#      LastModified, Size, ETag, StorageClass) plus the page count we
#      consumed. No content fetches; we never call get_object in slice 1.
#   2. parse_firehose_filename(key) → dict[year/month/day/hour/minute/second/iso]
#      Module-level helper that extracts the timestamp Firehose embeds in the
#      filename (".../{stream-name}-{stream-version}-YYYY-MM-DD-HH-MM-SS-{uuid}.gz").
#      Returns parsed=False with zeros + empty iso on a non-matching key —
#      callers choose whether to skip or include with delivery_at='' .
#
# CLAUDE.md mandates osbot-aws over boto3, but the existing Elastic__AWS__Client
# wraps boto3 directly for EC2/IAM/SSM. Mirroring that precedent here for S3
# is intentional — adding osbot-aws S3 helpers would be a cross-cutting refactor
# orthogonal to the LETS slice.
#
# Tests subclass and override paginate(); no boto3, no AWS round-trips, no mocks.
# ═══════════════════════════════════════════════════════════════════════════════

import re
from typing                                                                         import List, Tuple

import boto3                                                                        # EXCEPTION — see module header (mirrors Elastic__AWS__Client)

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe
from osbot_utils.type_safe.type_safe_core.decorators.type_safe                      import type_safe


# Firehose embeds a timestamp into every object name.  Pattern (within the key
# basename):  ...-YYYY-MM-DD-HH-MM-SS-<uuid>.<ext>
# The leading "..." absorbs the delivery-stream name + version, which can
# contain hyphens.  Anchored to the basename so a date-shaped substring
# elsewhere in the key path can't false-positive.
FIREHOSE_TIMESTAMP_REGEX = re.compile(r'-(\d{4})-(\d{2})-(\d{2})-(\d{2})-(\d{2})-(\d{2})-[a-f0-9-]+\.[A-Za-z0-9]+$')


def parse_firehose_filename(key: str) -> dict:                                      # Returns {year, month, day, hour, minute, second, iso, parsed}; parsed=False on no-match
    if not key:
        return {'year'  : 0, 'month' : 0, 'day'    : 0,
                'hour'  : 0, 'minute': 0, 'second' : 0,
                'iso'   : '', 'parsed': False}
    basename = key.rsplit('/', 1)[-1]                                               # Anchor on the filename, not the whole key path
    match    = FIREHOSE_TIMESTAMP_REGEX.search(basename)
    if not match:
        return {'year'  : 0, 'month' : 0, 'day'    : 0,
                'hour'  : 0, 'minute': 0, 'second' : 0,
                'iso'   : '', 'parsed': False}
    year, month, day, hour, minute, second = (int(g) for g in match.groups())
    iso = f'{year:04d}-{month:02d}-{day:02d}T{hour:02d}:{minute:02d}:{second:02d}Z'
    return {'year'  : year , 'month' : month , 'day'    : day    ,
            'hour'  : hour , 'minute': minute, 'second' : second ,
            'iso'   : iso  , 'parsed': True  }


def normalise_etag(raw: str) -> str:                                                # AWS returns ETag wrapped in double-quotes; strip them so the value matches Safe_Str__S3__ETag's regex
    if not raw:
        return ''
    return raw.strip().strip('"').lower()


class S3__Inventory__Lister(Type_Safe):

    def s3_client(self, region: str):                                               # Single seam — tests can override; per-call instantiation matches Elastic__AWS__Client.ec2_client. Empty region falls through to boto3's standard resolution chain (AWS_DEFAULT_REGION → profile → IMDS) — passing region_name='' would produce a malformed "https://s3..amazonaws.com" endpoint.
        if region:
            return boto3.client('s3', region_name=region)
        return boto3.client('s3')

    @type_safe
    def paginate(self, bucket   : str ,
                       prefix   : str = ''  ,
                       max_keys : int = 0   ,                                       # 0 = unlimited; otherwise stop after N
                       region   : str = ''
                  ) -> Tuple[List[dict], int]:
        client    = self.s3_client(region)
        paginator = client.get_paginator('list_objects_v2')
        kwargs    = {'Bucket': bucket}
        if prefix:
            kwargs['Prefix'] = prefix
        if max_keys and max_keys < 1000:                                            # AWS caps PageSize at 1000; only override when caller wants smaller pages
            kwargs['PaginationConfig'] = {'PageSize': max_keys}

        objects: List[dict] = []
        pages_listed        = 0
        for page in paginator.paginate(**kwargs):
            pages_listed += 1
            for obj in page.get('Contents', []) or []:                              # ListObjectsV2 omits "Contents" entirely on an empty page
                objects.append(obj)
                if max_keys and len(objects) >= max_keys:                           # Stop mid-page when we've satisfied the cap
                    return objects, pages_listed
        return objects, pages_listed
