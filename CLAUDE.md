# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

`databricks-ddbxutils` is a Python library that extends Databricks `dbutils` with:
- **Jinja2-powered widgets**: `dbutils.widgets` values can reference each other and use date functions via Jinja2 templates.
- **Environment-based config loader (`EnvConfig`)**: Reads a single `conf/settings.yml` YAML file, resolves environment-specific values (dev/stg/prd), and renders Jinja2 templates (including date math, cross-variable references, and Databricks secrets).
- **PySpark custom DataSource (`pyfunc`)**: A DataSource that takes a Python function serialized via `cloudpickle` + base64 and runs it as a partitioned PySpark reader.

## Build & Package Management

The project uses **uv** as the primary build tool (replaces the older `poetry` workflow described in README):

```shell
uv sync          # install dependencies into virtualenv
uv build         # build wheel/sdist to dist/
```

To publish to PyPI (requires `~/.pypirc` with token):
```shell
python3.12 -m twine upload dist/*
```

## Key Architecture

### Module structure

- `ddbxutils/__init__.py` — imports `widgets`, creates a lazy generator for the singleton `WidgetImpl`
- `ddbxutils/widgets/__init__.py` — public API: `get(name)`, `refresh()`, `get_instance()`
- `ddbxutils/widgets/core.py` — `WidgetImpl`: connects to Databricks via `databricks-sdk`, fetches all widget values, and renders each value through Jinja2 (using `add_days` / `add_datetime` from `functions.py`)
- `ddbxutils/functions.py` — low-level date helpers (`add_days`, `add_datetime`) used by the widget Jinja2 environment; note these have a different signature from the identically-named functions in `config.py`
- `ddbxutils/config.py` — standalone `EnvConfig` class (no dependency on `widgets`); its own Jinja2 environment registers a richer set of date globals/filters
- `ddbxutils/datasources/pyfunc.py` — `PythonFunctionDataSource` (PySpark v2 DataSource API); register with `spark.dataSource.register(PythonFunctionDataSource)` before use

### Two separate Jinja2 environments

| Location | Purpose | Functions available |
|---|---|---|
| `widgets/core.py` | Render widget default values at runtime | `add_days(str, fmt, default, days)`, `add_datetime(...)` |
| `config.py` | Render `conf/settings.yml` values | `today()`, `now()`, `make_date()`, `add_days(val, n)`, `add_months()`, `add_years()`, `format_date()`, `start_of_month()`, `end_of_month()` |

The two `add_days` functions have **different signatures** — do not confuse them.

### `EnvConfig` resolution order

1. Environment variable `{PREFIX}__{KEY}` (if `project_prefix` is set)
2. YAML value for the current `ENV` (dev/stg/prd), after Jinja2 multi-pass rendering (up to 10 passes to resolve inter-variable dependencies)
3. `ENV_DEFAULTS` fallback (catalog/schema per environment)

Secrets syntax `{{secrets/SCOPE/KEY}}` is pre-processed before Jinja2 rendering; falls back to env var `SECRET_{SCOPE}_{KEY}` when `dbutils` is not available.

### `pyproject.toml` note

The `[tool.hatch.build.targets.wheel]` section lists `src/ddbxutils`, `src/io`, and `src/utils` as packages, but the actual source lives directly under `ddbxutils/` (no `src/` directory). This is a mismatch that may need fixing for the wheel build to include the correct files.
