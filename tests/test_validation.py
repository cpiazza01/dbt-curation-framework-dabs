import pytest
from pydantic import ValidationError

from dbt_curation_framework.cli import DbtCurationConfig
from tests.helpers import MINIMAL_CONFIG


def test_minimal_config_valid():
    config = DbtCurationConfig.model_validate(MINIMAL_CONFIG)
    assert config.job_name == "dbt_curation__finance_gold"
    assert config.domain == "Finance"
    assert config.dbt_commands == ["dbt deps", "dbt build"]
    assert config.trigger_downstream_job is False


def test_job_name_required():
    raw = {k: v for k, v in MINIMAL_CONFIG.items() if k != "job_name"}
    with pytest.raises(ValidationError, match="job_name"):
        DbtCurationConfig.model_validate(raw)


def test_domain_required():
    raw = {k: v for k, v in MINIMAL_CONFIG.items() if k != "domain"}
    with pytest.raises(ValidationError, match="domain"):
        DbtCurationConfig.model_validate(raw)


def test_email_notifications_required():
    with pytest.raises(ValidationError, match="email_notifications"):
        DbtCurationConfig.model_validate({**MINIMAL_CONFIG, "email_notifications": []})


def test_downstream_job_id_required_when_trigger_enabled():
    with pytest.raises(ValidationError, match="downstream_job_id"):
        DbtCurationConfig.model_validate({
            **MINIMAL_CONFIG,
            "trigger_downstream_job": True,
            # downstream_job_id omitted
        })


def test_downstream_job_id_not_required_when_trigger_disabled():
    config = DbtCurationConfig.model_validate({**MINIMAL_CONFIG, "trigger_downstream_job": False})
    assert config.downstream_job_id is None


def test_dbt_commands_non_empty():
    with pytest.raises(ValidationError, match="dbt_commands"):
        DbtCurationConfig.model_validate({**MINIMAL_CONFIG, "dbt_commands": []})


def test_schedule_parsed():
    config = DbtCurationConfig.model_validate({
        **MINIMAL_CONFIG,
        "schedule": {
            "quartz_cron_expression": "0 0 6 ? * MON-FRI",
            "timezone_id": "America/Los_Angeles",
        },
    })
    assert config.schedule is not None
    assert config.schedule.pause_status == "UNPAUSED"


def test_schedule_optional():
    config = DbtCurationConfig.model_validate(MINIMAL_CONFIG)
    assert config.schedule is None


def test_custom_dbt_commands():
    config = DbtCurationConfig.model_validate({
        **MINIMAL_CONFIG,
        "dbt_commands": ["dbt deps", "dbt seed", "dbt build --select +marts+"],
    })
    assert len(config.dbt_commands) == 3
