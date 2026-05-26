import pytest

from dbt_curation_framework.cli import resolve_bundle_var

BUNDLE = {
    "variables": {
        "catalog": {"default": "enterprise"},
        "warehouse_id": {"default": "abc123"},
        "scalar_var": "direct_value",  # non-dict entry
    },
    "targets": {
        "dev": {"variables": {"catalog": "dev_enterprise"}},
        "prod": {"variables": {"catalog": "prod_enterprise", "warehouse_id": "prod_wh"}},
    },
}


def test_target_override_takes_precedence():
    assert resolve_bundle_var(BUNDLE, "dev", "catalog") == "dev_enterprise"
    assert resolve_bundle_var(BUNDLE, "prod", "catalog") == "prod_enterprise"


def test_falls_back_to_top_level_default():
    # warehouse_id has no dev override — falls back to bundle default
    assert resolve_bundle_var(BUNDLE, "dev", "warehouse_id") == "abc123"


def test_target_override_for_prod():
    assert resolve_bundle_var(BUNDLE, "prod", "warehouse_id") == "prod_wh"


def test_scalar_variable_entry():
    # Variables can be plain scalars, not just {default: ...} dicts
    assert resolve_bundle_var(BUNDLE, "dev", "scalar_var") == "direct_value"


def test_returns_fallback_when_variable_missing():
    assert resolve_bundle_var(BUNDLE, "dev", "nonexistent", fallback="<missing>") == "<missing>"


def test_raises_when_variable_missing_and_no_fallback():
    with pytest.raises(KeyError, match="nonexistent"):
        resolve_bundle_var(BUNDLE, "dev", "nonexistent")


def test_empty_bundle_uses_fallback():
    assert resolve_bundle_var({}, "dev", "catalog", fallback="fallback_catalog") == "fallback_catalog"


def test_unknown_env_falls_back_to_top_level_default():
    # "staging" has no target entry — should still resolve the bundle-level default
    assert resolve_bundle_var(BUNDLE, "staging", "catalog") == "enterprise"
