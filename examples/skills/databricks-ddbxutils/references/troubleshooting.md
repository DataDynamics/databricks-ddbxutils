# databricks-ddbxutils — Troubleshooting checklist

Go top-to-bottom when a user reports "it doesn't work." Each item is a concrete failure mode that's bitten real users, not generic advice.

## Install / import

- **`ModuleNotFoundError: ddbxutils`** on a Databricks cluster → library is not attached. Check Compute → Libraries tab (All Purpose) or task's Dependent libraries (Job). Restart the cluster after attaching if status shows "installing."
- **Wheel built locally is missing files** → `pyproject.toml`'s `[tool.hatch.build.targets.wheel]` lists `src/ddbxutils`, `src/io`, `src/utils`, but the real source is under `ddbxutils/`. Fix the packages list before `uv build`.
- **Serverless notebook** has no Libraries tab → use the right-hand **Environment** panel with a wheel in a Volume, or `%pip install databricks-ddbxutils` at the top of the notebook followed by `dbutils.library.restartPython()`.

## `ddbxutils.widgets`

- **`add_days` raises about wrong number of args** → widget `add_days` takes **4** args `(value, fmt, default, days)`. The 2-arg form is only valid inside `EnvConfig` YAML. Don't copy between them.
- **Widget value rendered literally as `{{add_days(...)}}`** → user probably called `dbutils.widgets.get(...)` instead of `ddbxutils.widgets.get(...)`. Only the `ddbxutils` wrapper runs Jinja2.
- **`WidgetImpl` fails to fetch widgets** → requires `databricks-sdk` and a real Databricks runtime. Running locally outside Databricks will not work.
- **Stale value after editing the widget in the UI** → call `ddbxutils.widgets.refresh()`; the implementation caches values on first read.

## `EnvConfig`

- **`KeyError` on a key you defined in YAML** → check: (a) the key is spelled correctly, (b) it has a value for the current `ENV`, (c) it's not shadowed by an env var like `MYAPP__KEY`.
- **Template not resolving after 10 passes** → circular or too-deep reference chain. `EnvConfig` caps multi-pass rendering at 10; flatten the chain or precompute.
- **Secrets `{{secrets/SCOPE/KEY}}` appearing literally** → secrets are **pre-processed before** Jinja2, not a Jinja2 function. Don't nest them inside another `{{...}}` expression or use filters on them.
- **Secret lookup fails locally** → off-Databricks, secrets fall back to env var `SECRET_{SCOPE}_{KEY}` (upper-cased, `-` → `_`). Set that var or run on Databricks.
- **`cfg.env` / `cfg.catalog` / `cfg.schema` returns something unexpected** → `ENV_DEFAULTS` fallback (`dev_catalog`/`analytics_dev`, etc.) kicks in only if the key isn't overridden by env var or YAML. Check the resolution order.
- **Env var override not applied** → the user must pass `project_prefix="MYAPP"` to `EnvConfig(...)` for `MYAPP__KEY` env vars to be consulted. Without `project_prefix`, `{PREFIX}__{KEY}` lookups are skipped.

## `ENV` env var on Databricks

- **`EnvConfig()` picks `dev` even though I set `ENV=prd`** → the env var is set on the driver only (e.g. in a notebook cell) but the code runs before the cell executes, OR it's set in an executor-only place. Prefer cluster `spark_env_vars` for both driver + executor visibility.
- **`os.environ["ENV"] = ...` in a cell doesn't reach a UDF** → notebook `os.environ` only affects the driver process. Executors need `spark_env_vars`.

## `PythonFunctionDataSource`

- **`DataSource not registered`** → call `spark.dataSource.register(PythonFunctionDataSource)` once per session before `spark.read.format(...)`.
- **`PicklingError` / `AttributeError` in an executor** → the function passed in references something that isn't importable/picklable on the executor side. Move the definition to a module that's installed on the cluster, or close over only picklable primitives.
