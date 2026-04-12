# databricks-ddbxutils

dbutils 로 부족한 부분을 확장한 ddbxutils

## Feature

* [x] `dbutils.widgets` 에 jinja2 template 적용
* [x] yaml file 로 공통 변수 사용

## 환경별 설정 파일 (conf/settings.yml)

**하나의 YAML 파일**에서 설정 키 기준으로 환경값을 나란히 배치하고,  
**Jinja2 템플릿**으로 secrets 참조, 변수 참조, 날짜 계산이 가능합니다.  
Python 함수 호출 스타일로 직관적으로 작성할 수 있습니다.

---

### conf/settings.yml
```yaml
# ===========================================================
# 스토리지 설정
# ===========================================================
storage_path:
  dev: "s3://my-project-dev/data"
  stg: "s3://my-project-stg/data"
  prd: "s3://my-project-prd/data"

# ===========================================================
# 날짜 계산 (다른 변수를 참조하여 날짜 계산 가능)
# ===========================================================
run_date: "{{today()}}"
start_date: "{{add_days(run_date, -7)}}"
last_month: "{{add_months(run_date, -1)}}"
month_start: "{{start_of_month(run_date)}}"
month_end: "{{end_of_month(run_date)}}"
process_end: "{{add_days(run_date, 7)}}"

# ===========================================================
# 포맷팅 + 중첩 호출
# ===========================================================
partition_date: "{{format_date(add_days(run_date, -1), '%Y%m%d')}}"
year_month: "{{format_date(run_date, '%Y%m')}}"

# ===========================================================
# 변수 참조 + 날짜 조합
# ===========================================================
full_path: "{{storage_path}}/processed/{{format_date(run_date, '%Y/%m/%d')}}"
archive_path: "{{storage_path}}/archive/{{format_date(add_months(run_date, -3), '%Y%m')}}"

# ===========================================================
# 환경/카탈로그 참조
# ===========================================================
current_env: "{{ENV}}"
table_prefix: "{{catalog}}.{{schema}}"

# ===========================================================
# Secrets (자동으로 dbutils.secrets.get 호출)
# ===========================================================
db_password:
  dev: "{{secrets/dev-scope/db-password}}"
  stg: "{{secrets/stg-scope/db-password}}"
  prd: "{{secrets/prd-scope/db-password}}"

api_key: "{{secrets/common-scope/api-key}}"

# ===========================================================
# 처리 설정
# ===========================================================
retry_count:
  dev: 1
  stg: 2
  prd: 3

batch_size:
  dev: 1000
  stg: 5000
  prd: 10000

log_level:
  dev: DEBUG
  stg: INFO
  prd: WARNING

# ===========================================================
# 환경 공통 설정 (스칼라)
# ===========================================================
app_name: "my_project"
version: "1.0.0"
```

---

### Jinja2 템플릿 문법 정리

#### 날짜 함수
| 문법 | 설명 |
| --- | --- |
| `{{today()}}` | 오늘 날짜 |
| `{{now()}}` | 현재 시간 |
| `{{make_date(2024, 1, 15)}}` | 특정 날짜 생성 |

#### 날짜 계산 (다른 변수 참조 가능)
| 문법 | 설명 |
| --- | --- |
| `{{add_days(run_date, -7)}}` | n일 추가 |
| `{{add_months(run_date, -1)}}` | n개월 추가 |
| `{{add_years(run_date, 1)}}` | n년 추가 |
| `{{start_of_month(run_date)}}` | 해당 월 1일 |
| `{{end_of_month(run_date)}}` | 해당 월 마지막 날 |

#### 포맷팅 / 중첩 호출
| 문법 | 설명 |
| --- | --- |
| `{{format_date(run_date, '%Y%m%d')}}` | 날짜 포맷팅 |
| `{{format_date(add_months(run_date, -3), '%Y%m')}}` | 중첩 호출 |

#### 변수 참조
| 문법 | 설명 |
| --- | --- |
| `{{storage_path}}` | 다른 YAML 설정값 직접 참조 |
| `{{env.HOME}}` | OS 환경변수 참조 |
| `{{ENV}}`, `{{catalog}}`, `{{schema}}` | 현재 환경 정보 |
| `{{secrets/SCOPE/KEY}}` | `dbutils.secrets.get()` 호출 |

## Install

```shell
pip install databricks-ddbxutils
```

## Project Build

### setup

```shell
cd <PROJECT_ROOT>
pip install poetry
```

### venv

```shell
poetry shell
```

### Build

```shell
poetry build
```

## Run

### in databricks w/o init_script(= Serverless)

* Add Wheel
  * wheel upload 용 Volume 생성 후 upload
    * `/Volumes/<CATALOG>/<DATABASE>/<VOLUME_NAME>/ddbxutils-<VERSION>-py3-none-any.whl`
  * notebook 의 우측 Environment 에서 Environment version 지정 후 volume 에 upload 한 wheel file 추가 후 Apply
* Usage
  ```python
  # dbutils.widgets.text('rawdate', '2025-05-24', 'Raw Date')
  # dbutils.widgets.text('next_day', '{{add_days(rawdate, "%Y-%m-%d", "", 1)}}', 'Next Day')
  import ddbxutils
  next_day = ddbxutils.widgets.get('next_day')
  # next_day: 2025-05-25
  ```

### in databricks w/ init_script

* Add Wheel
  * wheel upload 용 Volume 생성 후 upload
    * `/Volumes/<CATALOG>/<DATABASE>/<VOLUME_NAME>/ddbxutils-<VERSION>-py3-none-any.whl`
  * Libraries
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
* Spark config
  ```text
  spark.executorEnv.PYTHONSTARTUP /tmp/pyspark_startup.py
  ```
* Environment variables
  ```shell
  PYTHONSTARTUP=/tmp/pyspark_startup.py
  ```
* Init scripts
  ```text
  /Volumes/<CATALOG>/<DATABASE>/<VOLUME_NAME>/init_script_ddbxutils.sh
  ```
* Usage
  ```python
  # dbutils.widgets.text('rawdate', '2025-05-24', 'Raw Date')
  # dbutils.widgets.text('next_day', '{{add_days(rawdate, "%Y-%m-%d", "", 1)}}', 'Next Day')
  next_day = ddbxutils.widgets.get('next_day')
  # next_day: 2025-05-25
  ```