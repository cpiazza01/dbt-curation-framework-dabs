# dbt-curation-framework

A Python CLI that generates [Databricks Asset Bundle (DABs)](https://docs.databricks.com/en/dev-tools/bundles/index.html) resources for running DBT gold-layer curation jobs on Databricks. Point it at a YAML config file and it produces a ready-to-deploy Databricks Workflow that runs your DBT project using the native DBT task type.

## How it works

```
dbt_curation_config.yaml  ──▶  dbt-curation-generate  ──▶  resources/dbt_job.yml
databricks.yml (yours)                                  ──▶  dbt/profiles.yml
                                                        ──▶  dbt/macros/generate_schema_name.sql
```

The generated Workflow job runs a single native DBT task against a Databricks SQL warehouse. Schema routing (silver → `pre_gold` for staging/intermediate models, `pre_gold` → `gold` for mart models) is handled by your `dbt_project.yml` and the auto-generated `generate_schema_name` macro — no custom cluster code needed.

## Prerequisites

- Python 3.9+
- [Databricks CLI](https://docs.databricks.com/en/dev-tools/cli/index.html) with bundle support (`databricks bundle`)
- A Databricks workspace with Unity Catalog enabled
- A SQL warehouse

## Installation

```bash
pip install dbt-curation-framework
```

## Quick start

**1. Create `dbt_curation_config.yaml` in your bundle root:**

```yaml
job_name: dbt_curation__finance_gold
domain: Finance
email_notifications:
  - data-team@org.com

schedule:
  quartz_cron_expression: "0 0 6 ? * MON-FRI"
  timezone_id: "America/Los_Angeles"
```

**2. Create `databricks.yml` in your bundle root:**

```yaml
bundle:
  name: finance_gold

variables:
  catalog:
    default: "enterprise"
  pre_gold_schema:
    default: "pre_gold"
  warehouse_id:
    default: "<your-warehouse-id>"

include:
  - resources/*.yml

targets:
  dev:
    mode: development
    variables:
      catalog: "dev_enterprise"
  prod:
    mode: production
    variables:
      catalog: "prod_enterprise"
```

**3. Configure schema routing in your `dbt/dbt_project.yml`:**

```yaml
models:
  finance_gold:
    staging:
      +schema: pre_gold
    intermediate:
      +schema: pre_gold
    marts:
      +schema: gold
```

**4. Generate and deploy:**

```bash
dbt-curation-generate --config dbt_curation_config.yaml --env dev
databricks bundle deploy --target dev
```

## Generated files

| File | Commit? | Description |
|---|---|---|
| `resources/dbt_job.yml` | Yes | DABs Workflow job definition |
| `dbt/macros/generate_schema_name.sql` | Yes | DBT macro for exact schema routing |
| `dbt/profiles.yml` | No (gitignored) | Local dev profile using OAuth SSO |

The `generate_schema_name` macro prevents DBT from prepending the target schema to custom schemas (which would produce `pre_gold_pre_gold` instead of `pre_gold`). Commit it alongside your DBT project.

## Config reference (`dbt_curation_config.yaml`)

| Field | Type | Required | Default | Description |
|---|---|---|---|---|
| `job_name` | str | yes | — | Name of the Databricks Workflow job |
| `domain` | str | yes | — | Business domain governance tag (e.g. `Finance`, `Marketing`) |
| `dbt_project_directory` | str | no | `"../dbt"` | Path to dbt project, relative to `resources/dbt_job.yml` |
| `email_notifications` | list[str] | yes | — | At least one address; receives failure alerts |
| `email_on_success` | bool | no | `false` | Also send notifications on successful runs |
| `schedule` | Schedule | no | None | Quartz cron expression for automatic triggering |
| `trigger_downstream_job` | bool | no | `false` | Run another Databricks job after completion |
| `downstream_job_id` | str | conditional | — | Required when `trigger_downstream_job: true` |
| `dbt_commands` | list[str] | no | `["dbt deps", "dbt build"]` | Commands passed to the native DBT task |
| `service_principal_job_runners` | list[str] | no | `[]` | SP client IDs granted `CAN_MANAGE_RUN` |
| `tags` | dict | no | `{}` | Extra key/value tags applied to the job |
| `dbt_version` | str | no | `">=1.9.0,<2.0.0"` | PyPI version spec for `dbt-databricks` |

### Schedule fields

| Field | Type | Required | Default |
|---|---|---|---|
| `quartz_cron_expression` | str | yes | — |
| `timezone_id` | str | yes | — |
| `pause_status` | str | no | `UNPAUSED` |

## Bundle variables

The generated job uses these DABs bundle variables, which must be declared in your `databricks.yml`:

| Variable | Purpose |
|---|---|
| `catalog` | Unity Catalog name for all models |
| `pre_gold_schema` | Default target schema; staging + intermediate models route here |
| `warehouse_id` | SQL warehouse used by the DBT task |

## Full config example

```yaml
job_name: dbt_curation__finance_gold
domain: Finance
dbt_project_directory: ../dbt

email_notifications:
  - data-team@org.com
  - oncall@org.com
email_on_success: false

schedule:
  quartz_cron_expression: "0 0 6 ? * MON-FRI"
  timezone_id: "America/Los_Angeles"
  pause_status: UNPAUSED

dbt_commands:
  - "dbt deps"
  - "dbt build"

trigger_downstream_job: true
downstream_job_id: "12345"

service_principal_job_runners:
  - "my-sp-client-id"

tags:
  CostCenter: BI

dbt_version: ">=1.9.0,<2.0.0"
```

## Local development

The generated `dbt/profiles.yml` uses OAuth (SSO) — no token required. Set two environment variables and run dbt as normal:

```bash
export DATABRICKS_HOST="https://adb-123456789.azuredatabricks.net"
export DATABRICKS_HTTP_PATH="/sql/1.0/warehouses/abc123"

dbt run --select staging
```

On first run, dbt will open a browser window for SSO login.

## Contributing

```bash
pip install -e ".[dev]"
pytest                                      # run tests with coverage
ruff check dbt_curation_framework tests    # lint
ruff format dbt_curation_framework tests   # format
```

Releases are automated on push to `main` for `feat`/`fix`/`refactor` commits. Use `workflow_dispatch` on the Release workflow to manually cut a `minor` or `major` bump.
