"""Shared test fixtures and factory helpers."""
from dbt_curation_framework.cli import DbtCurationConfig, build_context

MINIMAL_CONFIG = {
    "project_name": "finance_gold",
    "github_repo": "github.com/org/finance-gold",
    "email_notifications": ["oncall@org.com"],
}

FULL_CONFIG = {
    **MINIMAL_CONFIG,
    "dbt_project_directory": "./dbt",
    "schedule": {
        "quartz_cron_expression": "0 0 6 ? * MON-FRI",
        "timezone_id": "America/Los_Angeles",
        "pause_status": "UNPAUSED",
    },
    "trigger_downstream_job": True,
    "downstream_job_id": 42,
    "dbt_commands": ["dbt deps", "dbt build --vars '{env: prod}'"],
    "service_principal_job_runners": ["sp-abc123"],
    "tags": {"Domain": "Finance", "CostCenter": "BI"},
    "dbt_version": ">=1.9.0,<2.0.0",
    "email_on_success": True,
}

SAMPLE_BUNDLE = {
    "variables": {
        "catalog": {"default": "enterprise"},
        "pre_gold_schema": {"default": "pre_gold"},
        "warehouse_id": {"default": "abc123"},
    },
    "targets": {
        "dev": {"variables": {"catalog": "dev_enterprise"}},
        "prod": {"variables": {"catalog": "prod_enterprise"}},
    },
}


def make_config(overrides: dict | None = None) -> DbtCurationConfig:
    raw = {**MINIMAL_CONFIG, **(overrides or {})}
    return DbtCurationConfig.model_validate(raw)


def make_context(overrides: dict | None = None, env: str = "dev") -> dict:
    config = make_config(overrides)
    return build_context(config, SAMPLE_BUNDLE, env)
