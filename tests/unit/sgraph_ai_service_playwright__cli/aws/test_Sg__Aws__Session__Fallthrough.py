# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — integration-pattern tests for Sg__Aws__Session boto3 fallthrough
# When no role is set in Sg__Aws__Context, boto3_client_from_context returns a
# real boto3 client constructed from ambient credentials — identical behaviour
# to the old bare boto3.client() calls.  These tests verify that:
#   1. boto3_client_from_context returns a real boto3 client when no role is set.
#   2. The seam method on a migrated helper class uses the same fallthrough path.
#   3. An in-memory subclass that overrides the seam still works correctly.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                       import TestCase

from sgraph_ai_service_playwright__cli.credentials.service.Sg__Aws__Context        import Sg__Aws__Context
from sgraph_ai_service_playwright__cli.credentials.service.Sg__Aws__Session        import Sg__Aws__Session
from sgraph_ai_service_playwright__cli.credentials.service.Credentials__Store      import Credentials__Store


class test_Sg__Aws__Session__Fallthrough(TestCase):

    def test_no_role_returns_boto3_client(self):                                    # With no role in context, falls through to bare boto3.client
        Sg__Aws__Context.clear_global_role()                                        # ensure clean state
        assert Sg__Aws__Context.get_current_role() == ''                            # confirm no role active
        session = Sg__Aws__Session(store=Credentials__Store())
        client  = session.boto3_client_from_context(service_name='sts', region='us-east-1')
        assert client is not None                                                   # real boto3 client object returned
        assert hasattr(client, 'get_caller_identity')                               # duck-type: STS client has this method

    def test_no_role_ec2_client_has_describe_instances(self):                       # Fallthrough yields a working ec2 client shape
        Sg__Aws__Context.clear_global_role()
        session = Sg__Aws__Session(store=Credentials__Store())
        client  = session.boto3_client_from_context(service_name='ec2', region='us-east-1')
        assert client is not None
        assert hasattr(client, 'describe_instances')                                # duck-type: EC2 client shape confirmed

    def test_migrated_seam_method_returns_boto3_client(self):                       # Elastic__AWS__Client seam uses fallthrough when no role set
        from sgraph_ai_service_playwright__cli.elastic.service.Elastic__AWS__Client import Elastic__AWS__Client
        Sg__Aws__Context.clear_global_role()
        aws_client = Elastic__AWS__Client()
        ec2 = aws_client.ec2_client('us-east-1')
        assert ec2 is not None
        assert hasattr(ec2, 'describe_instances')                                   # real ec2 client shape

    def test_in_memory_subclass_override_still_works(self):                         # Existing in-memory subclass pattern is preserved unchanged
        from sgraph_ai_service_playwright__cli.elastic.service.Elastic__AWS__Client import Elastic__AWS__Client

        class InMemoryClient:                                                        # lightweight stub — no boto3 involved
            calls = []
            def describe_instances(self, **kwargs):
                self.calls.append(kwargs)
                return {'Reservations': []}

        stub = InMemoryClient()

        class InMemoryElasticClient(Elastic__AWS__Client):
            def ec2_client(self, region: str):                                      # override seam — tests keep working unchanged
                return stub

        aws_client = InMemoryElasticClient()
        result     = aws_client.ec2_client('eu-west-1')
        assert result is stub                                                        # override seam returns the stub, not a real boto3 client
        assert hasattr(result, 'describe_instances')
