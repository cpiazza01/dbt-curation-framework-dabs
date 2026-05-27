# CLAUDE.md — DBT Curation Framework

## What this is

A Python CLI (`dbt-curation-generate`) that generates Databricks Asset Bundle (DABs) resources for running DBT gold-layer curation jobs on Databricks. The output is a Databricks Workflow job using the native DBT task type.

Schema routing (silver → `pre_gold` for staging/intermediate, `pre_gold` → `gold` for marts) is handled by the consumer's `dbt_project.yml` via `+schema` config and a `generate_schema_name` macro. The framework sets the default `schema` to `${var.pre_gold_schema}` in the job.

## Package layout

```
dbt_curation_framework/
├── cli.py          # Pydantic config models, bundle var resolution, generation pipeline
└── templates/
    ├── job.yml.j2                    # DABs Workflow job with single native DBT task
    ├── profiles.yml.j2               # DBT profiles.yml for local dev
    └── generate_schema_name.sql.j2   # DBT macro for exact schema routing
```

Generated outputs in consumer projects:
- `resources/dbt_job.yml` — commit to git; versioned infrastructure definition
- `dbt/profiles.yml` — gitignored; local dev only
- `dbt/macros/generate_schema_name.sql` — commit to git alongside the DBT project

## Development commands

```bash
pip install -e ".[dev]"
pytest                         # run tests with coverage
ruff check dbt_curation_framework tests   # lint
ruff format dbt_curation_framework tests  # format
```

## Config schema (dbt_curation_config.yaml)

| Field | Type | Required | Default | Notes |
|---|---|---|---|---|
| `job_name` | str | yes | — | Name of the Databricks Workflow job |
| `domain` | str | yes | — | Business domain governance tag (e.g. `Finance`, `Marketing`) |
| `dbt_project_directory` | str | no | `"./dbt"` | Path to dbt project within bundle |
| `email_notifications` | list[str] | yes | — | At least one address |
| `schedule` | Schedule | no | None | Quartz cron schedule |
| `trigger_downstream_job` | bool | no | false | Chain to another Databricks job |
| `downstream_job_id` | int | conditional | None | Required when trigger enabled |
| `dbt_commands` | list[str] | no | `["dbt deps", "dbt build"]` | Commands run inside the DBT task |
| `service_principal_job_runners` | list[str] | no | [] | SP client IDs granted CAN_MANAGE_RUN |
| `email_on_success` | bool | no | false | Also send notifications on successful runs |
| `tags` | dict | no | {} | Extra governance tags on the job |
| `dbt_version` | str | no | `">=1.9.0,<2.0.0"` | PyPI version spec for dbt-databricks |

`Schedule` fields: `quartz_cron_expression`, `timezone_id`, `pause_status` (UNPAUSED/PAUSED).

## Bundle variables (databricks.yml in consumer project)

The framework generates `${var.xxx}` references that DABs resolves at deploy time:

| Variable | Purpose |
|---|---|
| `catalog` | Unity Catalog name |
| `pre_gold_schema` | Default target schema; staging + intermediate models route here |
| `warehouse_id` | SQL warehouse for DBT execution |

## Schema routing in consumer dbt_project.yml

The framework sets the DABs job's default `schema` to `${var.pre_gold_schema}`. Consumers control per-model schema via `dbt_project.yml`:

```yaml
models:
  my_project:
    staging:
      +schema: pre_gold
    intermediate:
      +schema: pre_gold
    marts:
      +schema: gold
```

To prevent DBT from prepending the target schema (e.g. `pre_gold_pre_gold`), the framework automatically generates a `generate_schema_name` macro at `dbt/macros/generate_schema_name.sql`. Commit this file with your DBT project — it must be present for schema routing to work correctly.

## Adding a new config field

1. Add field to `DbtCurationConfig` in `cli.py` (Pydantic takes care of defaults and validation).
2. Add it to `build_context()` return dict.
3. Reference it in `job.yml.j2` or `profiles.yml.j2`.
4. Add a validation test in `tests/test_validation.py`.
5. Add a template rendering test in `tests/test_templates.py`.

## Validation rules

- `email_notifications` must be non-empty
- `dbt_commands` must be non-empty
- `downstream_job_id` is required when `trigger_downstream_job: true`
- `schedule.pause_status` must be `UNPAUSED` or `PAUSED`
