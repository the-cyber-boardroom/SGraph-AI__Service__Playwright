# ═══════════════════════════════════════════════════════════════════════════════
# Lambda__Docker__SGraph_AI__Service__Playwright — create/update Lambda from Docker image
#
# Production-tuning values carried forward from OSBot-Playwright:
#   memory       = 5120 MB  (not 2-3 GB — lower values hit OOM on real sequences)
#   architecture = x86_64   (GH Actions builds x86_64 images)
#
# `set_lambda_env_vars()` propagates the SG_PLAYWRIGHT__* secrets from the CI
# environment into the Lambda's environment, pinning DEPLOYMENT_TARGET=lambda
# so the in-process detector sees the correct target.
#
# `create_lambda_function_url()` carries forward the AWS bug workaround from
# OSBot-Playwright: delete the existing Function URL before recreating it, or
# subsequent deploys get stuck with a stale URL config.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.helpers.duration.Duration                                              import Duration
from osbot_utils.utils.Dev                                                              import pprint
from osbot_utils.utils.Env                                                              import get_env

from sgraph_ai_service_playwright.docker.Docker__SGraph_AI__Service__Playwright__Base   import Docker__SGraph_AI__Service__Playwright__Base


LAMBDA_MEMORY_MB    = 5120                                                              # Production-tuned; do not reduce
LAMBDA_ARCHITECTURE = 'x86_64'                                                          # GH Actions builds x86_64 images


class Lambda__Docker__SGraph_AI__Service__Playwright(Docker__SGraph_AI__Service__Playwright__Base):

    def create_lambda(self, delete_existing=False, wait_for_active=False):
        with Duration(prefix='[create_lambda] | delete and create:'):
            try:
                lambda_function              = self.lambda_function()
                lambda_function.image_uri    = self.image_uri()
                lambda_function.architecture = LAMBDA_ARCHITECTURE
                lambda_function.memory       = LAMBDA_MEMORY_MB

                self.set_lambda_env_vars(lambda_function)                               # Propagate CI secrets → Lambda env

                if delete_existing:
                    lambda_function.delete()

                create_result = lambda_function.create()
                pprint(create_result)

                if wait_for_active:
                    with Duration(prefix='[create_lambda] | wait for active:'):
                        lambda_function.wait_for_state_active(max_wait_count=80)

                function_url = self.create_lambda_function_url()
                return dict(create_result=create_result, function_url=function_url)
            except Exception as error:
                return {"status": "error", "error": str(error)}

    def set_lambda_env_vars(self, lambda_function):                                     # Propagate CI secrets → Lambda env vars
        env_vars = {
            'SG_PLAYWRIGHT__ACCESS_TOKEN_HEADER' : get_env('SG_PLAYWRIGHT__ACCESS_TOKEN_HEADER' ),
            'SG_PLAYWRIGHT__ACCESS_TOKEN_VALUE'  : get_env('SG_PLAYWRIGHT__ACCESS_TOKEN_VALUE'  ),
            'SG_PLAYWRIGHT__SG_SEND_BASE_URL'    : get_env('SG_PLAYWRIGHT__SG_SEND_BASE_URL'    ),
            'SG_PLAYWRIGHT__SG_SEND_VAULT_KEY'   : get_env('SG_PLAYWRIGHT__SG_SEND_VAULT_KEY'   ),
            'SG_PLAYWRIGHT__DEFAULT_S3_BUCKET'   : get_env('SG_PLAYWRIGHT__DEFAULT_S3_BUCKET'   ),
            'SG_PLAYWRIGHT__DEPLOYMENT_TARGET'   : 'lambda'                                     ,
        }
        for key, value in env_vars.items():
            if value:
                lambda_function.set_env_variable(key, value)

    def create_lambda_function_url(self):
        lambda_ = self.lambda_function()
        lambda_.function_url_delete()                                                   # AWS bug workaround: delete + recreate
        lambda_.function_url_create_with_public_access()
        return lambda_.function_url_info()

    def update_lambda_function(self):
        return self.lambda_function().update_lambda_image_uri(self.image_uri())

    def function_url(self):
        return self.lambda_function().function_url()
