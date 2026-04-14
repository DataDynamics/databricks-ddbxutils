---
name: databricks-ddbxutils
description: Use when the user is working with the `databricks-ddbxutils` Python library — writing or debugging `ddbxutils.widgets` (Jinja2-templated `dbutils.widgets`), `EnvConfig` (YAML + Jinja2 environment-aware config loader with secrets/variable references/date math), or `PythonFunctionDataSource` (PySpark v2 custom DataSource that runs cloudpickled functions). Triggers on imports like `from ddbxutils import ...`, YAML files under `conf/settings.yml` with Jinja2 `{{...}}` expressions, references to `EnvConfig`, `WidgetImpl`, `add_days`/`add_months`/`today()` template helpers, or Databricks notebook code that wraps `dbutils.widgets`.
---

# databricks-ddbxutils

`databricks-ddbxutils` extends Databricks `dbutils` with three independent features. Match the user's intent to the right feature before answering — they share a name but have separate APIs and **separate Jinja2 environments with different function signatures**.

## Feature map

| Feature | Module | Purpose |
|---|---|---|
| `ddbxutils.widgets` | `ddbxutils/widgets/core.py` | Renders `dbutils.widgets` values through Jinja2 so widget defaults can reference each other and do date math |
| `EnvConfig` | `ddbxutils/config.py` | Loads `conf/settings.yml`, picks values for the current env (`dev`/`stg`/`prd`), renders Jinja2 templates, resolves Databricks secrets |
| `PythonFunctionDataSource` | `ddbxutils/datasources/pyfunc.py` | PySpark v2 DataSource that takes a base64 + cloudpickle encoded function and runs it as a partitioned reader |

## Critical gotcha: two `add_days` functions

There are **two separate Jinja2 environments** with a function named `add_days` — do not confuse them.

| Where | Signature | Notes |
|---|---|---|
| `widgets/core.py` (via `ddbxutils/functions.py`) | `add_days(value: str, fmt: str, default: str, days: int)` | String-first, format-aware; used to render `dbutils.widgets` default values |
| `config.py` | `add_days(value, n: int)` | Shorter signature; used to render `conf/settings.yml` |

When writing examples, pick the right one based on whether the user is templating a **widget** or a **YAML config value**.

## Feature 1 — `ddbxutils.widgets`

Public API (from `ddbxutils/widgets/__init__.py`):

```python
import ddbxutils
val = ddbxutils.widgets.get("next_day")   # fetches + Jinja2-renders
ddbxutils.widgets.refresh()               # re-reads all widget values
ddbxutils.widgets.get_instance()          # lazy WidgetImpl singleton
```

Typical notebook pattern:

```python
dbutils.widgets.text('rawdate',  '2025-05-24', 'Raw Date')
dbutils.widgets.text('next_day', '{{add_days(rawdate, "%Y-%m-%d", "", 1)}}', 'Next Day')

import ddbxutils
ddbxutils.widgets.get('next_day')   # -> "2025-05-25"
```

Under the hood `WidgetImpl` uses `databricks-sdk` to fetch widget values, then renders each through Jinja2 with `add_days` / `add_datetime` from `ddbxutils/functions.py`.

## Feature 2 — `EnvConfig`

### Resolution order (highest to lowest)

1. Env var `{PROJECT_PREFIX}__{KEY}` (only if `project_prefix` was set)
2. YAML value for the current `ENV`, after Jinja2 multi-pass rendering (up to 10 passes to resolve cross-references)
3. `ENV_DEFAULTS` fallback (`catalog` / `schema` per env)

### Initialization

```python
from ddbxutils import EnvConfig

cfg = EnvConfig()                                 # env/prefix/config path from env vars
cfg = EnvConfig(env="prd", project_prefix="MYAPP")
```

Env vars read when no constructor args are given:
- `ENV` — `dev` / `stg` / `prd` (default `dev`)
- `PROJECT_PREFIX` — prefix for per-key overrides
- `CONFIG_PATH` — YAML path (default `conf/settings.yml`)
- `{PREFIX}__CONFIG_PATH` — prefix-scoped path (wins over `CONFIG_PATH`)

### Access patterns

```python
cfg.run_date                       # attribute
cfg["run_date"]                    # item
cfg.get("run_date", "2024-01-01")  # with default
cfg.env / cfg.catalog / cfg.schema # built-ins
cfg.full_table_name                # "<catalog>.<schema>"
cfg.keys(); "run_date" in cfg
cfg.print_summary()
```

### YAML template capabilities

Config values can be either per-env dicts:

```yaml
storage_path:
  dev: s3://my-project-dev/data
  stg: s3://my-project-stg/data
  prd: s3://my-project-prd/data
```

…or Jinja2 expressions that reference other keys:

```yaml
run_date: "{{today()}}"
start_date: "{{add_days(run_date, -7)}}"
partition_date: "{{format_date(add_days(run_date, -1), '%Y%m%d')}}"
full_path: "{{storage_path}}/processed/{{format_date(run_date, '%Y/%m/%d')}}"
```

Available helpers in the **`EnvConfig` Jinja2 env only**:

- Dates: `today()`, `now()`, `make_date(y,m,d)`, `add_days(v,n)`, `add_months(v,n)`, `add_years(v,n)`, `start_of_month(v)`, `end_of_month(v)`, `format_date(v, fmt)`
- Arithmetic: `{{ batch_size * 2 }}`, `//`, `%`, `**`, conditional `{{ 'a' if x else 'b' }}`
- Strings: `~` concat, `| upper | lower | title | capitalize | trim | length | replace | join`, slicing `code[:3]`, `startswith`, `in`
- Refs: other YAML keys, `{{env.HOME}}`, `{{ENV}}`, `{{catalog}}`, `{{schema}}`
- Secrets: `{{secrets/SCOPE/KEY}}` → `dbutils.secrets.get("SCOPE","KEY")`; falls back to env var `SECRET_{SCOPE}_{KEY}` when dbutils is unavailable. Secrets are **pre-processed before** Jinja2 rendering.

### Project-prefix override example

```bash
export MYAPP__RUN_DATE=2024-06-01
export MYAPP__CATALOG=override_catalog
```

```python
cfg = EnvConfig(env="prd", project_prefix="MYAPP")
cfg.run_date   # "2024-06-01"  ← env var wins over YAML
```

## Feature 3 — `PythonFunctionDataSource`

PySpark v2 custom DataSource. Register once per session before use:

```python
from ddbxutils.datasources.pyfunc import PythonFunctionDataSource
spark.dataSource.register(PythonFunctionDataSource)
```

It takes a Python function serialized via `cloudpickle` + base64 and runs it as a partitioned reader. When helping users, remember that the function must be picklable in the executor environment.

## Install on a Databricks cluster (Libraries UI)

The recommended way to make `ddbxutils` available on All Purpose / Job Compute is to attach it as a **cluster Library** — no init script or notebook-scoped `%pip install` required.

### All Purpose Compute

1. Compute → select the cluster → **Libraries** tab → **Install new**
2. Library Source: **PyPI**
3. Package: `databricks-ddbxutils` (pin a version, e.g. `databricks-ddbxutils==<VERSION>`)
4. **Install** → the cluster auto-installs on driver + executors and restarts if needed

Alternatively, upload the wheel to a Unity Catalog Volume and pick **Volume** as the source:
`/Volumes/<catalog>/<schema>/<volume>/ddbxutils-<version>-py3-none-any.whl`

### Job Compute

Add the library to the job task's cluster definition. UI: Jobs → task → **Dependent libraries** → **Add** → PyPI or Volume. JSON equivalent:

```json
{
  "libraries": [
    { "pypi": { "package": "databricks-ddbxutils==<VERSION>" } }
  ]
}
```

Or with a wheel in a Volume:

```json
{
  "libraries": [
    { "whl": "/Volumes/<catalog>/<schema>/<volume>/ddbxutils-<VERSION>-py3-none-any.whl" }
  ]
}
```

After the library is attached, notebooks/jobs just `import ddbxutils` — no startup script needed.

### Local dev / build

```bash
uv sync                               # dev deps
uv run pytest tests/ -v               # tests
uv build                              # wheel + sdist into dist/
python3.12 -m twine upload dist/*     # publish (requires ~/.pypirc)
```

Note: `pyproject.toml`'s `[tool.hatch.build.targets.wheel]` currently lists `src/ddbxutils`, `src/io`, `src/utils`, but the source lives directly under `ddbxutils/` with no `src/` directory. If a user reports missing files in the built wheel, that mismatch is the likely cause.

## Setting `ENV` on Databricks compute

`EnvConfig()` with no args reads `ENV` / `PROJECT_PREFIX` / `CONFIG_PATH` from the process environment, so on Databricks you need to get those vars into the driver (and executors, if UDFs/tasks also read them). Two common patterns:

### All Purpose Compute (interactive cluster)

Cluster settings → **Advanced options** → **Spark** → **Environment variables**:

```text
ENV=prd
PROJECT_PREFIX=MYAPP
CONFIG_PATH=/Volumes/<catalog>/<schema>/<volume>/conf/settings.yml
```

Restart the cluster to apply. Then in a notebook:

```python
from ddbxutils import EnvConfig
cfg = EnvConfig()          # ENV=prd picked up automatically
cfg.print_summary()
```

### Job Compute (job cluster per task)

In the Jobs UI for the task → **Compute** → edit the job cluster → **Advanced options** → **Spark** → **Environment variables** (or the equivalent field in the JSON job definition):

```json
{
  "new_cluster": {
    "spark_env_vars": {
      "ENV": "prd",
      "PROJECT_PREFIX": "MYAPP",
      "CONFIG_PATH": "/Volumes/<catalog>/<schema>/<volume>/conf/settings.yml"
    }
  }
}
```

Per-env job definitions typically differ only in the `ENV` value, so the same notebook / wheel runs unchanged across `dev`/`stg`/`prd`.

### Serverless notebooks / Serverless Jobs

Serverless compute does **not** expose cluster env vars. Set them at the top of the notebook before importing `EnvConfig`, or pass them explicitly to the constructor:

```python
import os
os.environ["ENV"] = "prd"
os.environ["PROJECT_PREFIX"] = "MYAPP"
os.environ["CONFIG_PATH"] = "/Volumes/main/ops/config/conf/settings.yml"

from ddbxutils import EnvConfig
cfg = EnvConfig()
```

Or skip env vars entirely:

```python
cfg = EnvConfig(env="prd", project_prefix="MYAPP",
                config_path="/Volumes/main/ops/config/conf/settings.yml")
```

### Switching env per run via widgets

A common Databricks pattern — drive `ENV` from a notebook widget so one job definition covers all environments:

```python
dbutils.widgets.dropdown("env", "dev", ["dev", "stg", "prd"], "Environment")
import os
os.environ["ENV"] = dbutils.widgets.get("env")

from ddbxutils import EnvConfig
cfg = EnvConfig()
```

Note: cluster `spark_env_vars` are visible to the driver **and** executors. `os.environ[...]` set in a notebook cell only affects the driver — if a UDF/task reads `ENV` on the executor side, use `spark_env_vars` instead.

## Serverless compute

Serverless notebooks/jobs don't expose the Libraries tab. Either:

- Upload the wheel to a Volume and attach it via the notebook's right-hand **Environment** panel, then **Apply**, or
- Use notebook-scoped `%pip install databricks-ddbxutils` at the top of the notebook (followed by `dbutils.library.restartPython()` if needed).

## Reference files

When the user needs a concrete example, read the matching file in `references/` and adapt it — do not reconstruct these from memory.

- `references/settings.example.yml` — canonical `conf/settings.yml` covering per-env values, date math, secrets, numeric/string ops, and cross-references. Starting point for any new project.
- `references/widget_patterns.py` — `ddbxutils.widgets` usage patterns with the correct **4-arg** `add_days` form, env-switch dropdown, refresh, `add_datetime`.
- `references/cluster_libraries.json` — Databricks Jobs API snippets: `libraries` (PyPI + Volume wheel), `spark_env_vars` for `ENV`/`PROJECT_PREFIX`/`CONFIG_PATH`, and a per-env job variant layout.
- `references/troubleshooting.md` — ordered debugging checklist for install, widgets, `EnvConfig`, env-var propagation, and `PythonFunctionDataSource`. Walk it top-to-bottom when a user reports a failure.

## When helping users

- If they paste a YAML template, check whether it would need multiple passes (keys referencing keys that reference keys). `EnvConfig` retries up to 10 passes — more than that is a bug in their template.
- If they write `{{add_days(...)}}` in a widget, enforce the 4-arg form (`value, fmt, default, days`). In YAML, enforce the 2-arg form (`value, n`).
- Secrets syntax `{{secrets/SCOPE/KEY}}` is **not** standard Jinja2 — it's pre-processed. Don't suggest moving it inside another Jinja2 expression.
- `cfg.schema` shadows the Python `schema` builtin only within the config object; it's safe as an attribute but warn users if they plan to `from ddbxutils import schema`-style imports (those don't exist).
- For widget issues, confirm the user has `databricks-sdk` available and is running inside a Databricks runtime — `WidgetImpl` will fail to fetch values otherwise.
