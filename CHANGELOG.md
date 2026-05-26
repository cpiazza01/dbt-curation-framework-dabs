# Changelog

All notable changes to this project will be documented here. This project adheres to [Semantic Versioning](https://semver.org/).

---

## [Unreleased]

---

## [0.1.0] — 2026-05-25

### Added
- Initial framework: `dbt-curation-generate` CLI generates DABs Workflow job and DBT profiles from YAML config
- Native Databricks DBT task integration with `dbt-databricks` adapter
- OAuth (SSO) authentication for local development profiles
- Schema routing via `${var.pre_gold_schema}` bundle variable and `+schema` config in `dbt_project.yml`
- Pydantic v2 config validation with helpful error messages
- CI/CD: test, release (git-cliff changelog + bump-my-version), and Claude Code review workflows

---
