"""CLI for generating DABs resources for DBT gold-layer curation jobs."""
from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import Literal

import yaml
from jinja2 import Environment, PackageLoader
from pydantic import BaseModel, model_validator

# ── Pydantic models ───────────────────────────────────────────────────────────


class Schedule(BaseModel):
    quartz_cron_expression: str
    timezone_id: str
    pause_status: Literal["UNPAUSED", "PAUSED"] = "UNPAUSED"


class DbtCurationConfig(BaseModel):
    job_name: str
    domain: str
    dbt_project_directory: str = "../dbt"
    email_notifications: list[str]
    schedule: Schedule | None = None
    trigger_downstream_job: bool = False
    downstream_job_id: str | None = None
    # DBT commands to run — consumers can override to add selectors, vars, flags, etc.
    # Schema routing (pre_gold vs gold) is handled via +schema in the consumer's dbt_project.yml.
    dbt_commands: list[str] = ["dbt deps", "dbt build"]
    service_principal_job_runners: list[str] = []
    tags: dict[str, str] = {}
    dbt_version: str = ">=1.9.0,<2.0.0"
    email_on_success: bool = False

    @model_validator(mode="after")
    def validate_email_notifications(self) -> "DbtCurationConfig":
        if not self.email_notifications:
            raise ValueError("email_notifications must contain at least one address")
        return self

    @model_validator(mode="after")
    def validate_downstream_job(self) -> "DbtCurationConfig":
        if self.trigger_downstream_job and self.downstream_job_id is None:
            raise ValueError("downstream_job_id is required when trigger_downstream_job is true")
        return self

    @model_validator(mode="after")
    def validate_commands_non_empty(self) -> "DbtCurationConfig":
        if not self.dbt_commands:
            raise ValueError("dbt_commands must contain at least one command")
        return self


# ── Bundle variable resolution ────────────────────────────────────────────────


def resolve_bundle_var(bundle: dict, env: str, var_name: str, fallback: str | None = None) -> str:
    """Resolve a DABs bundle variable, preferring target-level overrides."""
    target_vars = bundle.get("targets", {}).get(env, {}).get("variables", {})
    if var_name in target_vars:
        val = target_vars[var_name]
        return str(val) if val is not None else (fallback or "")

    top_entry = bundle.get("variables", {}).get(var_name)
    if top_entry is not None:
        default = top_entry.get("default") if isinstance(top_entry, dict) else top_entry
        if default is not None:
            return str(default)

    if fallback is not None:
        return fallback
    raise KeyError(f"Variable '{var_name}' not found in databricks.yml for env '{env}'")


def load_bundle(bundle_path: str = "databricks.yml") -> dict:
    if not os.path.exists(bundle_path):
        return {}
    with open(bundle_path) as f:
        return yaml.safe_load(f) or {}


# ── Context building ──────────────────────────────────────────────────────────


def build_context(config: DbtCurationConfig, bundle: dict, env: str) -> dict:
    all_tags = {
        "Domain": config.domain,
        "FrameworkUsed": "dbt-curation-framework",
        "JobName": config.job_name,
        **config.tags,
    }

    # Resolve catalog for profiles.yml local dev default; fall back gracefully.
    catalog = resolve_bundle_var(bundle, env, "catalog", fallback="<catalog>")

    return {
        "job_name": config.job_name,
        "dbt_project_directory": config.dbt_project_directory,
        "email_notifications": config.email_notifications,
        "schedule": config.schedule.model_dump() if config.schedule else None,
        "trigger_downstream_job": config.trigger_downstream_job,
        "downstream_job_id": config.downstream_job_id,
        "dbt_commands": config.dbt_commands,
        "email_on_success": config.email_on_success,
        "service_principal_job_runners": config.service_principal_job_runners,
        "tags": all_tags,
        "dbt_version": config.dbt_version,
        "env": env,
        "catalog": catalog,
    }


# ── Template rendering ────────────────────────────────────────────────────────


def get_jinja_env() -> Environment:
    return Environment(
        loader=PackageLoader("dbt_curation_framework", "templates"),
        trim_blocks=True,
        lstrip_blocks=True,
        keep_trailing_newline=True,
    )


def render_and_write(
    jinja_env: Environment,
    template_name: str,
    context: dict,
    output_path: str,
    skip_if_exists: bool = False,
) -> None:
    if skip_if_exists and Path(output_path).exists():
        print(f"  Skipped (already exists): {output_path}")
        return
    template = jinja_env.get_template(template_name)
    rendered = template.render(context)
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        f.write(rendered)
    print(f"  Generated: {output_path}")


# ── Main ──────────────────────────────────────────────────────────────────────


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate DABs resources for DBT curation jobs")
    parser.add_argument("--config", required=True, help="Path to dbt_curation_config.yaml")
    parser.add_argument("--env", required=True, help="Target environment (e.g. dev, prod)")
    args = parser.parse_args()

    with open(args.config) as f:
        raw = yaml.safe_load(f)

    config = DbtCurationConfig.model_validate(raw)
    bundle = load_bundle("databricks.yml")
    context = build_context(config, bundle, args.env)

    jinja_env = get_jinja_env()

    print(f"\nGenerating DABs resources for '{config.job_name}' (env: {args.env})...")
    render_and_write(jinja_env, "job.yml.j2", context, "resources/dbt_job.yml")
    render_and_write(jinja_env, "profiles.yml.j2", context, "dbt/profiles.yml")
    render_and_write(
        jinja_env, "generate_schema_name.sql.j2", context, "dbt/macros/generate_schema_name.sql", skip_if_exists=True
    )

    print(f"""
Next steps:
  1. Ensure your databricks.yml declares the required variables and includes resources/:

       variables:
         catalog:          {{default: "<catalog>"}}
         pre_gold_schema:  {{default: "pre_gold"}}
         warehouse_id:     {{default: "<warehouse-id>"}}
       include:
         - resources/*.yml

  2. Configure +schema in your dbt_project.yml so models land in the right schema:

       models:
         <your_dbt_project_name>:
           staging:
             +schema: pre_gold
           intermediate:
             +schema: pre_gold
           marts:
             +schema: gold

  3. Commit resources/dbt_job.yml and dbt/macros/generate_schema_name.sql to git.

  4. Deploy: databricks bundle deploy --target {args.env}
""")
