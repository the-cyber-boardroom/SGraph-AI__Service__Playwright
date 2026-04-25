# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Kibana__Saved_Objects__Client
# Talks to Kibana's saved-objects API to list, export, and import dashboards
# and data views (= "index-pattern" objects in 8.x). Three endpoints:
#
#   GET  /api/saved_objects/_find  — paged list per type
#   POST /api/saved_objects/_export — ndjson download (deep references opt-in)
#   POST /api/saved_objects/_import — ndjson upload (overwrite opt-in)
#
# All non-GET endpoints require the `kbn-xsrf` header (Kibana's CSRF guard).
# verify=False is inherited from Elastic__HTTP__Client (self-signed cert).
#
# Shares the same `request()` seam as Elastic__HTTP__Client so tests can
# subclass and intercept without mocks.
# ═══════════════════════════════════════════════════════════════════════════════

import base64
import json
from typing                                                                         import Tuple

from osbot_utils.type_safe.type_safe_core.decorators.type_safe                      import type_safe

from sgraph_ai_service_playwright__cli.elastic.collections.List__Schema__Kibana__Saved_Object import List__Schema__Kibana__Saved_Object
from sgraph_ai_service_playwright__cli.elastic.enums.Enum__Saved_Object__Type       import Enum__Saved_Object__Type
from sgraph_ai_service_playwright__cli.elastic.schemas.Schema__Kibana__Dashboard__Result import Schema__Kibana__Dashboard__Result
from sgraph_ai_service_playwright__cli.elastic.schemas.Schema__Kibana__Data_View__Result import Schema__Kibana__Data_View__Result
from sgraph_ai_service_playwright__cli.elastic.schemas.Schema__Kibana__Find__Response   import Schema__Kibana__Find__Response
from sgraph_ai_service_playwright__cli.elastic.schemas.Schema__Kibana__Import__Result   import Schema__Kibana__Import__Result
from sgraph_ai_service_playwright__cli.elastic.schemas.Schema__Kibana__Saved_Object  import Schema__Kibana__Saved_Object
from sgraph_ai_service_playwright__cli.elastic.service.Default__Dashboard__Generator import Default__Dashboard__Generator
from sgraph_ai_service_playwright__cli.elastic.service.Elastic__HTTP__Client        import Elastic__HTTP__Client
from sgraph_ai_service_playwright__cli.elastic.service.Kibana__Disabled_Features    import DEFAULT_DISABLED_FEATURES


KBN_XSRF_HEADER = {'kbn-xsrf': 'true'}                                              # Required for every non-GET Kibana API call (CSRF guard)


def basic_auth_header(username: str, password: str) -> dict:                        # Module-level helper so the client and tests can reuse without re-encoding inline
    token = base64.b64encode(f'{username}:{password}'.encode()).decode()
    return {'Authorization': f'Basic {token}'}


class Kibana__Saved_Objects__Client(Elastic__HTTP__Client):                         # Reuses request()/timeout/verify from the parent — no separate config

    @type_safe
    def find(self, base_url     : str                       ,
                   username     : str                       ,
                   password     : str                       ,
                   object_type  : Enum__Saved_Object__Type  ,
                   page_size    : int                       = 100
              ) -> Schema__Kibana__Find__Response:
        url     = base_url.rstrip('/') + f'/api/saved_objects/_find?type={str(object_type)}&per_page={int(page_size)}'
        headers = basic_auth_header(username, password)
        response = self.request('GET', url, headers=headers)
        status   = int(response.status_code)
        objects  = List__Schema__Kibana__Saved_Object()
        if status >= 300:
            return Schema__Kibana__Find__Response(total       = 0       ,
                                                  objects     = objects ,
                                                  http_status = status  ,
                                                  error       = f'HTTP {status}: {(response.text or "")[:500]}')
        try:
            payload = response.json() or {}
        except Exception:
            return Schema__Kibana__Find__Response(http_status = status,
                                                  error       = 'response was not JSON')
        for raw in payload.get('saved_objects', []):
            attributes = raw.get('attributes', {}) or {}
            objects.append(Schema__Kibana__Saved_Object(id         = str(raw.get('id'        , '')),
                                                        type       = str(raw.get('type'      , '')),
                                                        title      = str(attributes.get('title', '')),
                                                        updated_at = str(raw.get('updated_at', ''))))
        return Schema__Kibana__Find__Response(total       = int(payload.get('total', 0)),
                                              objects     = objects                      ,
                                              http_status = status                       ,
                                              error       = ''                           )

    @type_safe
    def export(self, base_url               : str                       ,
                     username               : str                       ,
                     password               : str                       ,
                     object_type            : Enum__Saved_Object__Type  ,
                     include_references_deep: bool                      = True
                ) -> Tuple[bytes, int, str]:                                        # (ndjson_bytes, http_status, error)
        url     = base_url.rstrip('/') + '/api/saved_objects/_export'
        headers = {**basic_auth_header(username, password),
                   **KBN_XSRF_HEADER                       ,
                   'Content-Type': 'application/json'      }
        body    = {'type': [str(object_type)]}                                      # List form is required when types > 1; using list always keeps the API call uniform
        if include_references_deep:                                                 # Pulls in lens/visualization/search/data-view objects so dashboards round-trip self-contained
            body['includeReferencesDeep'] = True
        data    = json.dumps(body).encode('utf-8')
        response = self.request('POST', url, headers=headers, data=data)
        status   = int(response.status_code)
        if status >= 300:
            return b'', status, f'HTTP {status}: {(response.text or "")[:500]}'
        return response.content or b'', status, ''

    @type_safe
    def import_objects(self, base_url     : str   ,
                              username     : str   ,
                              password     : str   ,
                              ndjson_bytes : bytes ,
                              overwrite    : bool  = True
                        ) -> Schema__Kibana__Import__Result:
        url     = base_url.rstrip('/') + ('/api/saved_objects/_import?overwrite=true' if overwrite else '/api/saved_objects/_import')
        boundary = '----sp-elastic-import'                                          # Fixed boundary — Kibana doesn't care about the value, only that it matches Content-Type
        body     = (f'--{boundary}\r\n'
                    f'Content-Disposition: form-data; name="file"; filename="export.ndjson"\r\n'
                    f'Content-Type: application/ndjson\r\n\r\n').encode('utf-8') + ndjson_bytes + f'\r\n--{boundary}--\r\n'.encode('utf-8')
        headers  = {**basic_auth_header(username, password),
                    **KBN_XSRF_HEADER                       ,
                    'Content-Type': f'multipart/form-data; boundary={boundary}'}
        response = self.request('POST', url, headers=headers, data=body)
        status   = int(response.status_code)
        if status >= 300:
            return Schema__Kibana__Import__Result(success     = False ,
                                                  http_status = status,
                                                  first_error = f'HTTP {status}: {(response.text or "")[:500]}')
        try:
            payload = response.json() or {}
        except Exception:
            return Schema__Kibana__Import__Result(http_status = status,
                                                  first_error = 'response was not JSON')
        errors      = payload.get('errors', []) or []
        first_err   = ''
        if errors:
            err = errors[0] or {}
            err_type   = (err.get('error') or {}).get('type', '')
            err_id     = err.get('id', '')
            first_err  = f'{err_type} on {err_id}'[:500]
        return Schema__Kibana__Import__Result(success       = bool(payload.get('success', False)),
                                              success_count = int (payload.get('successCount', 0)),
                                              error_count   = len(errors)                          ,
                                              http_status   = status                               ,
                                              first_error   = first_err                            )

    @type_safe
    def delete_data_view_by_title(self, base_url : str ,                            # Idempotent helper: find by exact title via _find, DELETE if present
                                         username : str ,
                                         password : str ,
                                         title    : str
                                   ) -> Tuple[bool, int, str]:                      # (deleted, http_status, error_message); deleted=False with status=200 means "did not exist"
        find_url     = base_url.rstrip('/') + f'/api/saved_objects/_find?type=index-pattern&per_page=200'
        find_headers = basic_auth_header(username, password)
        find_resp    = self.request('GET', find_url, headers=find_headers)
        if int(find_resp.status_code) >= 300:
            return False, int(find_resp.status_code), f'HTTP {find_resp.status_code} on _find: {(find_resp.text or "")[:500]}'
        try:
            payload = find_resp.json() or {}
        except Exception:
            return False, int(find_resp.status_code), '_find returned non-JSON'
        target_id = ''
        for raw in payload.get('saved_objects', []):
            attrs = raw.get('attributes', {}) or {}
            if str(attrs.get('title', '')) == title:
                target_id = str(raw.get('id', ''))
                break
        if not target_id:
            return False, 200, ''                                                   # Not found — idempotent success
        del_url     = base_url.rstrip('/') + f'/api/data_views/data_view/{target_id}'
        del_headers = {**basic_auth_header(username, password), **KBN_XSRF_HEADER}
        del_resp    = self.request('DELETE', del_url, headers=del_headers)
        del_status  = int(del_resp.status_code)
        if del_status >= 300:
            return False, del_status, f'HTTP {del_status}: {(del_resp.text or "")[:500]}'
        return True, del_status, ''

    @type_safe
    def ensure_data_view(self, base_url        : str ,
                                username        : str ,
                                password        : str ,
                                title           : str ,                              # Index name (or pattern) e.g. "sg-synthetic"
                                time_field_name : str = 'timestamp'
                          ) -> Schema__Kibana__Data_View__Result:
        # Step 1: list existing data views and skip when one already matches the title — keeps `sp el seed` idempotent across reruns
        find_url     = base_url.rstrip('/') + f'/api/saved_objects/_find?type=index-pattern&per_page=200'
        find_headers = basic_auth_header(username, password)
        find_resp    = self.request('GET', find_url, headers=find_headers)
        find_status  = int(find_resp.status_code)
        if find_status >= 300:
            return Schema__Kibana__Data_View__Result(title       = title       ,
                                                     http_status = find_status ,
                                                     error       = f'HTTP {find_status} on _find: {(find_resp.text or "")[:500]}')
        try:
            find_payload = find_resp.json() or {}
        except Exception:
            return Schema__Kibana__Data_View__Result(title=title, http_status=find_status, error='_find returned non-JSON')
        for raw in find_payload.get('saved_objects', []):
            attrs = raw.get('attributes', {}) or {}
            if str(attrs.get('title', '')) == title:
                return Schema__Kibana__Data_View__Result(id          = str(raw.get('id', '')),
                                                         title       = title                  ,
                                                         created     = False                  ,
                                                         http_status = find_status            ,
                                                         error       = ''                     )

        # Step 2: not found — POST to /api/data_views/data_view to create it
        create_url    = base_url.rstrip('/') + '/api/data_views/data_view'
        create_body   = json.dumps({'data_view': {'title'           : title,
                                                   'name'            : title,
                                                   'timeFieldName'   : time_field_name}}).encode('utf-8')
        create_headers = {**basic_auth_header(username, password),
                          **KBN_XSRF_HEADER                       ,
                          'Content-Type': 'application/json'      }
        create_resp   = self.request('POST', create_url, headers=create_headers, data=create_body)
        create_status = int(create_resp.status_code)
        if create_status >= 300:
            return Schema__Kibana__Data_View__Result(title       = title         ,
                                                     http_status = create_status ,
                                                     error       = f'HTTP {create_status}: {(create_resp.text or "")[:500]}')
        try:
            create_payload = create_resp.json() or {}
        except Exception:
            return Schema__Kibana__Data_View__Result(title=title, http_status=create_status, error='create returned non-JSON')
        new_view = create_payload.get('data_view') or {}
        return Schema__Kibana__Data_View__Result(id          = str(new_view.get('id', '')),
                                                 title       = title                       ,
                                                 created     = True                        ,
                                                 http_status = create_status               ,
                                                 error       = ''                          )

    @type_safe
    def disable_space_features(self, base_url : str ,                               # PUT /api/spaces/space/<space_id> with disabledFeatures — hides solution groups (Observability, Security) from the Kibana side-nav. Idempotent: PUT replaces the space config.
                                      username : str ,
                                      password : str ,
                                      space_id : str = 'default'                    ,
                                      features : list = None
                                ) -> Tuple[bool, int, str]:                         # (ok, http_status, error)
        # Default list lives in Kibana__Disabled_Features.DEFAULT_DISABLED_FEATURES so the
        # cloud-init harden script and this runtime fallback stay in sync.
        target_features = list(features) if features is not None else list(DEFAULT_DISABLED_FEATURES)

        # PUT /api/spaces/space/<id> requires the existing space body — fetch first to preserve name/description
        get_url     = base_url.rstrip('/') + f'/api/spaces/space/{space_id}'
        get_headers = basic_auth_header(username, password)
        get_resp    = self.request('GET', get_url, headers=get_headers)
        if int(get_resp.status_code) >= 300:
            return False, int(get_resp.status_code), f'HTTP {get_resp.status_code} reading space: {(get_resp.text or "")[:500]}'
        try:
            space = get_resp.json() or {}
        except Exception:
            return False, int(get_resp.status_code), 'space GET returned non-JSON'

        space['disabledFeatures'] = target_features                                 # Replace, don't merge — caller controls the full list
        put_headers = {**basic_auth_header(username, password), **KBN_XSRF_HEADER, 'Content-Type': 'application/json'}
        put_resp    = self.request('PUT', get_url, headers=put_headers, data=json.dumps(space).encode('utf-8'))
        put_status  = int(put_resp.status_code)
        if put_status >= 300:
            return False, put_status, f'HTTP {put_status}: {(put_resp.text or "")[:500]}'
        return True, put_status, ''

    @type_safe
    def ensure_default_dashboard(self, base_url     : str ,
                                        username     : str ,
                                        password     : str ,
                                        index        : str ,
                                        data_view_id : str ,
                                        time_field   : str = 'timestamp'
                                  ) -> Schema__Kibana__Dashboard__Result:
        # Programmatically build the ndjson — every panel needs the data view id baked in
        generator    = Default__Dashboard__Generator()
        ndjson       = generator.build_ndjson(index=index, data_view_id=data_view_id, time_field=time_field)
        title        = generator.dashboard_title()
        dashboard_id = generator.dashboard_id()

        # Re-use the existing import path — overwrite=true so seed is idempotent across reruns
        result = self.import_objects(base_url=base_url, username=username, password=password,
                                      ndjson_bytes=ndjson, overwrite=True)
        if not result.success and result.error_count == 0 and str(result.first_error):
            return Schema__Kibana__Dashboard__Result(id          = dashboard_id          ,
                                                     title       = title                  ,
                                                     http_status = result.http_status     ,
                                                     error       = str(result.first_error))
        return Schema__Kibana__Dashboard__Result(id           = dashboard_id            ,
                                                 title        = title                    ,
                                                 object_count = result.success_count     ,
                                                 created      = result.success_count > 0,
                                                 http_status  = result.http_status       ,
                                                 error        = str(result.first_error)  if result.error_count > 0 else '')
