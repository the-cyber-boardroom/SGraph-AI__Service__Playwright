# S3 TUI API — driving it from Python / CLI

## From the CLI
```
sg aws s3 tui api list
sg aws s3 tui api describe sg-aws.s3 --json
sg aws s3 tui api skills sg-aws.s3 api
sg aws s3 tui api invoke sg-aws.s3 list_buckets
sg aws s3 tui api invoke sg-aws.s3 list_objects --params '{"bucket":"my-bucket","prefix":"logs/"}'
sg aws s3 tui api invoke sg-aws.s3 head_object  --params '{"bucket":"my-bucket","key":"logs/a.txt"}'
```

## From Python (no AWS — inject a fake)
```python
from sgraph_ai_service_playwright__cli.aws.s3.tui_api.S3__Tui_Api__Provider import S3__Tui_Api__Provider
from sgraph_ai_service_playwright__cli.aws.s3.service.S3__AWS__Client       import S3__AWS__Client

class FakeS3(S3__AWS__Client):
    def list_buckets(self): ...      # return [Schema__S3__Bucket(...)]
    def list_objects(self, bucket, prefix='', recursive=False): ...

provider = S3__Tui_Api__Provider(client=FakeS3())
result   = provider.dispatch('list_objects', {'bucket': 'b', 'prefix': 'logs/'})
assert result.ok
```

## Notes for an automated driver
- `provider.manifest()` is the contract; `provider.manifest().actions[*].input_schema` is
  real JSON Schema you can validate params against.
- `dispatch()` is mode-free and never prompts — safe to call from pytest/CI.
- The same provider instance is what the CLI and (later) the chat tool-loop use.
