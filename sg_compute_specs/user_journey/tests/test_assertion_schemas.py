# ═══════════════════════════════════════════════════════════════════════════════
# Tests — User-Journey assertion schemas + registry
# ═══════════════════════════════════════════════════════════════════════════════

import pytest

from sg_compute_specs.user_journey.core.dispatcher.assertion_schema_registry           import parse_assertion, ASSERTION_SCHEMAS
from sg_compute_specs.user_journey.core.schemas.enums.Enum__Assertion__Type            import Enum__Assertion__Type
from sg_compute_specs.user_journey.core.schemas.assertions.Schema__Journey__Assertion__Url_Contains import Schema__Journey__Assertion__Url_Contains
from sg_compute_specs.user_journey.core.schemas.assertions.Schema__Journey__Assertion__Status_Code_Equals import Schema__Journey__Assertion__Status_Code_Equals


SAMPLES = {                                                                         # minimal valid fields per type
    'url_contains'           : {'expected'      : '/dashboard'        },
    'url_equals'             : {'expected'      : 'https://a.test/x'  },
    'selector_visible'       : {'selector'      : '#main .title > a'  },
    'selector_text_equals'   : {'selector'      : '#a', 'expected': 'hi'},
    'selector_text_contains' : {'selector'      : '#a', 'expected': 'hi'},
    'status_code_equals'     : {'expected_status': 200               },
    'http_header_present'    : {'header_name'   : 'Content-Type'      },
}


class TestAssertionSchemas:

    def test_registry_covers_all_types(self):
        assert set(ASSERTION_SCHEMAS.keys()) == set(Enum__Assertion__Type)

    def test_parse_dispatches_each_type(self):
        for type_value, fields in SAMPLES.items():
            parsed = parse_assertion({'assertion_type': type_value, **fields})
            assert str(parsed.assertion_type) == type_value                         # discriminator default is correct
            assert type(parsed) is ASSERTION_SCHEMAS[Enum__Assertion__Type(type_value)]

    def test_round_trip_preserves_url_path(self):
        original = Schema__Journey__Assertion__Url_Contains(expected='/dashboard')
        restored = Schema__Journey__Assertion__Url_Contains.from_json(original.json())
        assert str(restored.expected)       == '/dashboard'                         # NOT mangled to '_dashboard'
        assert restored.assertion_type      == Enum__Assertion__Type.URL_CONTAINS

    def test_status_code_url_substring_preserves_slash(self):
        parsed = parse_assertion({'assertion_type': 'status_code_equals', 'expected_status': 504, 'url_substring': '/pay'})
        assert isinstance(parsed, Schema__Journey__Assertion__Status_Code_Equals)
        assert int(parsed.expected_status)  == 504
        assert str(parsed.url_substring)    == '/pay'

    def test_parse_unknown_type_raises(self):
        with pytest.raises(ValueError):
            parse_assertion({'assertion_type': 'does_not_exist'})

    def test_parse_missing_type_raises(self):
        with pytest.raises(ValueError):
            parse_assertion({'expected': '/x'})
