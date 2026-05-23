# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Sentinel__Deployer__In_Memory
# Sentinel__Deployer wired to the existing *__In_Memory client doubles so the whole
# create/destroy/teardown lifecycle is unit-tested with no AWS and no network.
# No mocks, no patches — real subclasses with dict-backed fakes.
# ═══════════════════════════════════════════════════════════════════════════════

from tests.unit.sgraph_ai_service_playwright__cli.aws.cf.service.CloudFront__AWS__Client__In_Memory          import CloudFront__AWS__Client__In_Memory
from tests.unit.sgraph_ai_service_playwright__cli.aws.cf.service.CloudFront__Function__AWS__Client__In_Memory import CloudFront__Function__AWS__Client__In_Memory
from tests.unit.sgraph_ai_service_playwright__cli.aws.lambda_.service.Lambda__AWS__Client__In_Memory          import Lambda__AWS__Client__In_Memory, Lambda__Deployer__In_Memory
from tests.unit.sgraph_ai_service_playwright__cli.aws.s3.service.S3__AWS__Client__In_Memory                   import S3__AWS__Client__In_Memory
from sgraph_ai_service_playwright__cli.sentinel.service.Sentinel__Deployer                                    import Sentinel__Deployer


def new_in_memory_deployer(account_id: str = '123456789012') -> Sentinel__Deployer:
    cf_store   = {}
    fn_store   = {}
    lam_store  = {}
    obj_store  = {}
    buck_store = {}
    lambda_client = Lambda__AWS__Client__In_Memory(store=lam_store)
    deployer = Sentinel__Deployer(cf_client       = CloudFront__AWS__Client__In_Memory(store=cf_store),
                                  cf_fn_client    = CloudFront__Function__AWS__Client__In_Memory(store=fn_store),
                                  lambda_deployer = Lambda__Deployer__In_Memory(lambda_client),
                                  s3_client       = S3__AWS__Client__In_Memory(object_store=obj_store, bucket_store=buck_store),
                                  account_id      = account_id)
    return deployer
