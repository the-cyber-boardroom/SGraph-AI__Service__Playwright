# ═══════════════════════════════════════════════════════════════════════════════
# sg_edge edge-waker — Fast_API__Edge_Waker
# Serverless__Fast_API app for the Edge Waker (Mangum-backed; handler() from the
# base; Swagger at /docs; root-mounted Routes__Edge_Waker).
#
# config.enable_api_key = False — the cold-cold catch-all is reached by anonymous
# CloudFront origin-failover requests, so the surface is public. The control-plane
# routes (/__edge__/reconcile, /__edge__/idle-check) are triggered by EventBridge /
# admin inside the account; gating them is a Slice-5 concern (IAM on the Fn URL).
#
# The default reconciler is built with the real SG_Edge__DNS__Helper and the edge
# parent from config; its launcher/terminator seams are left unwired here and are
# injected by the deploy wiring in Slice 5 (the EC2-backed proxy launcher).
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_fast_api_serverless.fast_api.Serverless__Fast_API import Serverless__Fast_API

from sg_compute_specs.sg_edge.lambdas.edge_waker.edge_waker__config import (
    EDGE_WAKER__FAST_API__TITLE, EDGE_WAKER__FAST_API__DESC,
    edge_parent, edge_proxy_target_count, edge_idle_teardown_threshold)
from sg_compute_specs.sg_edge.lambdas.edge_waker.routes.Routes__Edge_Waker import Routes__Edge_Waker
from sg_compute_specs.sg_edge.service.SG_Edge__DNS__Helper                 import SG_Edge__DNS__Helper
from sg_compute_specs.sg_edge.service.SG_Edge__Fleet__Reconciler           import SG_Edge__Fleet__Reconciler


class Fast_API__Edge_Waker(Serverless__Fast_API):
    reconciler : SG_Edge__Fleet__Reconciler = None

    def setup(self):
        with self.config as _:
            _.name           = EDGE_WAKER__FAST_API__TITLE
            _.description    = EDGE_WAKER__FAST_API__DESC
            _.enable_api_key = False                                                 # public — CloudFront failover is anonymous
        if self.reconciler is None:
            self.reconciler = SG_Edge__Fleet__Reconciler(dns            = SG_Edge__DNS__Helper()      ,
                                                         parent         = edge_parent()              ,
                                                         target_count   = edge_proxy_target_count()  ,
                                                         idle_threshold = edge_idle_teardown_threshold())
        return super().setup()

    def setup_routes(self):
        self.add_routes(Routes__Edge_Waker, reconciler=self.reconciler)
