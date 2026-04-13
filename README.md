# databricks-ddbxutils

`ddbxutils` extends Databricks `dbutils` with features it lacks out of the box.

> 한국어 문서는 [README.ko.md](README.ko.md) 를 참고하세요.

## Features

* [x] Jinja2 template support for `dbutils.widgets`
* [x] `EnvConfig` — a YAML-based, environment-aware config loader (Jinja2 templates, secrets, variable references, date/number/string operations)
* [x] `PythonFunctionDataSource` — a custom data source built on the PySpark v2 DataSource API

## Install

```shell
pip install databricks-ddbxutils
```

## Testing

```shell
uv run pytest tests/ -v
```

---

## EnvConfig

### Highlights

- **Single YAML file** that places `dev` / `stg` / `prd` values side by side, keyed by config name
- **Jinja2 templates** — secret references, variable references, date arithmetic, numeric arithmetic, and string operations
- **Multi-pass rendering** — resolves inter-variable dependencies automatically in up to 10 passes
- **`project_prefix`** — override any key at runtime via a `PREFIX__KEY` environment variable

### Resolution priority

```
env var {PREFIX}__{KEY}  >  YAML value (after Jinja2 rendering)  >  ENV_DEFAULTS fallback
```

### Initialization via environment variables

If `EnvConfig()` is called without arguments, the values below are read from environment variables. Constructor arguments take precedence when provided.

| Env var | Description | Default |
| --- | --- | --- |
| `ENV` | Environment name (`dev` / `stg` / `prd`) | `dev` |
| `PROJECT_PREFIX` | Prefix used for `{PREFIX}__{KEY}` overrides | (none) |
| `CONFIG_PATH` | Path to the YAML config file | `conf/settings.yml` |
| `{PREFIX}__CONFIG_PATH` | Prefix-scoped config path (highest-priority env var) | - |

```shell
export ENV=prd
export PROJECT_PREFIX=MYAPP
export CONFIG_PATH=conf/my-settings.yml
```

```python
cfg = EnvConfig()   # initialized from the environment variables above
```

### Basic usage

```python
from ddbxutils import EnvConfig

# Environment inferred from the ENV variable (default: dev)
cfg = EnvConfig()

# Explicit environment + project_prefix override support
cfg = EnvConfig(env="prd", project_prefix="MYAPP")

# Accessing values (attribute / dict / get all work the same way)
cfg.run_date                       # attribute access
cfg["run_date"]                    # dict-style access
cfg.get("run_date", "2024-01-01")  # with a default

# The built-in keys (env / catalog / schema) are accessible the same way
cfg.env              == cfg["env"]     == cfg.get("env")
cfg.catalog          == cfg["catalog"] == cfg.get("catalog")
cfg.schema           == cfg["schema"]  == cfg.get("schema")

# Extras
cfg.full_table_name   # "dev_catalog.analytics_dev"
cfg.keys()            # built-in keys + YAML keys
"run_date" in cfg     # membership check

# Summary output
cfg.print_summary()
```

### conf/settings.yml

```yaml
# ===========================================================
# Per-environment values
# ===========================================================
storage_path:
  dev: "s3://my-project-dev/data"
  stg: "s3://my-project-stg/data"
  prd: "s3://my-project-prd/data"

retry_count:
  dev: 1
  stg: 2
  prd: 3

log_level:
  dev: DEBUG
  stg: INFO
  prd: WARNING

# ===========================================================
# Date arithmetic (values can reference other variables)
# ===========================================================
run_date: "{{today()}}"
start_date: "{{add_days(run_date, -7)}}"
last_month: "{{add_months(run_date, -1)}}"
month_start: "{{start_of_month(run_date)}}"
month_end: "{{end_of_month(run_date)}}"

# ===========================================================
# Numeric arithmetic
# ===========================================================
batch_size:
  dev: 1000
  stg: 5000
  prd: 10000
double_batch: "{{ batch_size * 2 }}"
page_count: "{{ batch_size // 256 }}"

# ===========================================================
# String operations
# ===========================================================
app_name: "my_project"
upper_app: "{{ app_name | upper }}"
archive_path: "{{ storage_path | replace('/data', '/archive') }}"
full_table: "{{ catalog ~ '.' ~ schema ~ '.events' }}"

# ===========================================================
# Formatting + nested calls
# ===========================================================
partition_date: "{{format_date(add_days(run_date, -1), '%Y%m%d')}}"
year_month: "{{format_date(run_date, '%Y%m')}}"

# ===========================================================
# Variable references + path composition
# ===========================================================
full_path: "{{storage_path}}/processed/{{format_date(run_date, '%Y/%m/%d')}}"

# ===========================================================
# Environment / catalog references
# ===========================================================
current_env: "{{ENV}}"
table_prefix: "{{catalog}}.{{schema}}"

# ===========================================================
# Secrets (automatically calls dbutils.secrets.get)
# ===========================================================
db_password:
  dev: "{{secrets/dev-scope/db-password}}"
  stg: "{{secrets/stg-scope/db-password}}"
  prd: "{{secrets/prd-scope/db-password}}"

api_key: "{{secrets/common-scope/api-key}}"

# ===========================================================
# Shared across environments
# ===========================================================
version: "1.0.0"
```

### Overriding with `project_prefix` env vars

When initialized with `project_prefix="MYAPP"`, any key can be overridden via a `MYAPP__KEY` environment variable.

```shell
export MYAPP__RUN_DATE=2024-06-01
export MYAPP__CATALOG=override_catalog
export MYAPP__SCHEMA=custom_schema
```

```python
cfg = EnvConfig(env="prd", project_prefix="MYAPP")
cfg.run_date   # "2024-06-01"  ← env var wins
cfg.catalog    # "override_catalog"
```

### Jinja2 template reference

#### Date functions
| Syntax | Description |
| --- | --- |
| `{{today()}}` | Today's date |
| `{{now()}}` | Current timestamp |
| `{{make_date(2024, 1, 15)}}` | Build a specific date |

#### Date arithmetic
| Syntax | Description |
| --- | --- |
| `{{add_days(run_date, -7)}}` | Add/subtract n days |
| `{{add_months(run_date, -1)}}` | Add/subtract n months |
| `{{add_years(run_date, 1)}}` | Add/subtract n years |
| `{{start_of_month(run_date)}}` | First day of the month |
| `{{end_of_month(run_date)}}` | Last day of the month |
| `{{format_date(run_date, '%Y%m%d')}}` | Format a date |
| `{{format_date(add_months(run_date, -3), '%Y%m')}}` | Nested calls |

#### Numeric arithmetic
| Syntax | Description |
| --- | --- |
| `{{ batch_size * 2 }}` | Multiplication |
| `{{ batch_size + 500 }}` | Addition |
| `{{ total // page_size }}` | Integer division |
| `{{ count % 7 }}` | Modulo |
| `{{ 2 ** 10 }}` | Exponent |
| `{{ 'large' if count > 100 else 'small' }}` | Conditional expression |

#### String operations
| Syntax | Description |
| --- | --- |
| `{{ a ~ '_' ~ b }}` | String concatenation (`~` operator) |
| `{{ name \| upper }}` | Uppercase |
| `{{ name \| lower }}` | Lowercase |
| `{{ name \| title }}` | Title-case every word |
| `{{ name \| capitalize }}` | Capitalize the first letter only |
| `{{ name \| trim }}` | Strip surrounding whitespace |
| `{{ path \| replace('/raw', '/processed') }}` | String replacement |
| `{{ tags.split(',') \| join('-') }}` | Split then join |
| `{{ name \| length }}` | String length |
| `{{ code[:3] }}` | Slicing |
| `{{ 'yes' if path.startswith('/data') else 'no' }}` | `startswith` check |
| `{{ 'yes' if 'raw' in path else 'no' }}` | Substring membership |

#### Variable references
| Syntax | Description |
| --- | --- |
| `{{storage_path}}` | Reference another YAML config value |
| `{{env.HOME}}` | Reference an OS environment variable |
| `{{ENV}}`, `{{catalog}}`, `{{schema}}` | Current environment info |
| `{{secrets/SCOPE/KEY}}` | Calls `dbutils.secrets.get('SCOPE', 'KEY')` |

---

## Run

### On Databricks without an init script (Serverless)

* Create a Volume for the wheel and upload it:
  * `/Volumes/<CATALOG>/<DATABASE>/<VOLUME_NAME>/ddbxutils-<VERSION>-py3-none-any.whl`
* In the notebook's right-hand Environment panel, add the wheel file and click Apply.
* Usage:
  ```python
  # dbutils.widgets.text('rawdate', '2025-05-24', 'Raw Date')
  # dbutils.widgets.text('next_day', '{{add_days(rawdate, "%Y-%m-%d", "", 1)}}', 'Next Day')
  import ddbxutils
  next_day = ddbxutils.widgets.get('next_day')
  # next_day: 2025-05-25

  from ddbxutils import EnvConfig
  cfg = EnvConfig(project_prefix="MYAPP")
  cfg.print_summary()
  ```

### On Databricks with an init script

* Prepare the wheel and the init script:
  * `/Volumes/<CATALOG>/<DATABASE>/<VOLUME_NAME>/ddbxutils-<VERSION>-py3-none-any.whl`
* `/Volumes/<CATALOG>/<DATABASE>/<VOLUME_NAME>/init_script_ddbxutils.sh`
  ```shell
  #! /bin/bash

  STARTUP_SCRIPT=/tmp/pyspark_startup.py

  cat >> ${STARTUP_SCRIPT} << EOF

  prefix = 'PYTHONSTARTUP_ddbxutils'
  print(f'{prefix} custom startup script loading...')
  try:
    import ddbxutils
    print(f'{prefix} Custom modules [ddbxutils] are loaded.')
  except Exception as e:
    print(f'{prefix} e={e}')
    print(f'{prefix} import ddbxutils failed')
  EOF
  ```
* Spark config:
  ```text
  spark.executorEnv.PYTHONSTARTUP /tmp/pyspark_startup.py
  ```
* Environment variables:
  ```shell
  PYTHONSTARTUP=/tmp/pyspark_startup.py
  ```
* Init scripts:
  ```text
  /Volumes/<CATALOG>/<DATABASE>/<VOLUME_NAME>/init_script_ddbxutils.sh
  ```
* Usage:
  ```python
  # dbutils.widgets.text('rawdate', '2025-05-24', 'Raw Date')
  # dbutils.widgets.text('next_day', '{{add_days(rawdate, "%Y-%m-%d", "", 1)}}', 'Next Day')
  next_day = ddbxutils.widgets.get('next_day')
  # next_day: 2025-05-25
  ```
