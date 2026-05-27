import tempfile
from pathlib import Path

import yaml

from dbt_curation_framework.cli import get_jinja_env, render_and_write
from tests.helpers import FULL_CONFIG, make_context


def test_job_renders_valid_yaml(jinja_env):
    context = make_context()
    rendered = jinja_env.get_template("job.yml.j2").render(context)
    parsed = yaml.safe_load(rendered)
    assert "resources" in parsed
    assert "jobs" in parsed["resources"]


def test_job_name_present(jinja_env):
    context = make_context()
    rendered = jinja_env.get_template("job.yml.j2").render(context)
    assert "dbt_curation__finance_gold" in rendered


def test_job_has_dbt_build_task(jinja_env):
    context = make_context()
    rendered = jinja_env.get_template("job.yml.j2").render(context)
    assert "dbt_build" in rendered
    assert "dbt_task" in rendered
    assert "environment_key: dbt_env" in rendered
    assert "dbt-databricks" in rendered


def test_job_uses_bundle_vars_for_warehouse_catalog(jinja_env):
    context = make_context()
    rendered = jinja_env.get_template("job.yml.j2").render(context)
    assert "${var.warehouse_id}" in rendered
    assert "${var.catalog}" in rendered
    assert "${var.pre_gold_schema}" in rendered


def test_job_schedule_rendered_when_set(jinja_env):
    context = make_context(FULL_CONFIG)
    rendered = jinja_env.get_template("job.yml.j2").render(context)
    assert "quartz_cron_expression" in rendered
    assert "MON-FRI" in rendered


def test_job_no_schedule_block_when_omitted(jinja_env):
    context = make_context()  # no schedule in MINIMAL_CONFIG
    rendered = jinja_env.get_template("job.yml.j2").render(context)
    assert "quartz_cron_expression" not in rendered


def test_job_downstream_task_rendered_when_enabled(jinja_env):
    context = make_context(FULL_CONFIG)
    rendered = jinja_env.get_template("job.yml.j2").render(context)
    assert "trigger_downstream_job" in rendered
    assert "42" in rendered


def test_job_no_downstream_task_when_disabled(jinja_env):
    context = make_context()  # trigger_downstream_job defaults to False
    rendered = jinja_env.get_template("job.yml.j2").render(context)
    assert "trigger_downstream_job" not in rendered


def test_job_permissions_rendered_for_service_principals(jinja_env):
    context = make_context(FULL_CONFIG)
    rendered = jinja_env.get_template("job.yml.j2").render(context)
    assert "sp-abc123" in rendered
    assert "CAN_MANAGE_RUN" in rendered


def test_job_governance_tags_present(jinja_env):
    context = make_context()
    rendered = jinja_env.get_template("job.yml.j2").render(context)
    assert "FrameworkUsed" in rendered
    assert "dbt-curation-framework" in rendered
    assert "Domain" in rendered
    assert "Finance" in rendered


def test_profiles_renders_default_profile_name(jinja_env):
    context = make_context()
    rendered = jinja_env.get_template("profiles.yml.j2").render(context)
    assert "default:" in rendered


def test_profiles_contains_databricks_type_and_oauth(jinja_env):
    context = make_context()
    rendered = jinja_env.get_template("profiles.yml.j2").render(context)
    assert "type: databricks" in rendered
    assert "databricks-oauth" in rendered
    assert "token" not in rendered


def test_profiles_catalog_resolved_from_bundle(jinja_env):
    context = make_context(target="dev")
    rendered = jinja_env.get_template("profiles.yml.j2").render(context)
    # dev target overrides catalog to "dev_enterprise"
    assert "dev_enterprise" in rendered


def test_email_on_success_rendered_when_enabled(jinja_env):
    context = make_context(FULL_CONFIG)
    rendered = jinja_env.get_template("job.yml.j2").render(context)
    assert "on_success" in rendered


def test_no_email_on_success_when_disabled(jinja_env):
    context = make_context()  # email_on_success defaults to False
    rendered = jinja_env.get_template("job.yml.j2").render(context)
    assert "on_success" not in rendered


def test_task_defaults_rendered(jinja_env):
    context = make_context()
    rendered = jinja_env.get_template("job.yml.j2").render(context)
    assert "disable_auto_optimization: true" in rendered
    assert "timeout_seconds: 7200" in rendered
    assert "max_retries: 0" in rendered
    assert "retry_on_timeout: false" in rendered
    assert "min_retry_interval_millis" not in rendered


def test_min_retry_interval_rendered_when_set(jinja_env):
    context = make_context(FULL_CONFIG)
    rendered = jinja_env.get_template("job.yml.j2").render(context)
    assert "min_retry_interval_millis: 30000" in rendered


def test_performance_target_rendered_when_set(jinja_env):
    context = make_context(FULL_CONFIG)
    rendered = jinja_env.get_template("job.yml.j2").render(context)
    assert "performance_target: PERFORMANCE_OPTIMIZED" in rendered


def test_performance_target_default_is_standard(jinja_env):
    context = make_context()
    rendered = jinja_env.get_template("job.yml.j2").render(context)
    assert "performance_target: STANDARD" in rendered


def test_generate_schema_name_macro_renders(jinja_env):
    context = make_context()
    rendered = jinja_env.get_template("generate_schema_name.sql.j2").render(context)
    assert "generate_schema_name" in rendered
    assert "target.schema" in rendered
    assert "custom_schema_name" in rendered
    assert "custom_schema_name | trim" in rendered


def test_render_and_write_skip_if_exists():
    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = Path(tmpdir) / "macros" / "generate_schema_name.sql"
        output_path.parent.mkdir()
        output_path.write_text("existing content")

        env = get_jinja_env()
        context = make_context()
        render_and_write(env, "generate_schema_name.sql.j2", context, str(output_path), skip_if_exists=True)

        assert output_path.read_text() == "existing content"


def test_render_and_write_overwrites_by_default():
    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = Path(tmpdir) / "macros" / "generate_schema_name.sql"
        output_path.parent.mkdir()
        output_path.write_text("existing content")

        env = get_jinja_env()
        context = make_context()
        render_and_write(env, "generate_schema_name.sql.j2", context, str(output_path))

        assert output_path.read_text() != "existing content"
