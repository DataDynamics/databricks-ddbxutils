# databricks-ddbxutils

dbutils 로 부족한 부분을 확장한 ddbxutils

## Feature

* [x] `dbutils.widgets` 에 jinja2 template 적용
* [x] `EnvConfig` — YAML 기반 환경별 설정 로더 (Jinja2 템플릿, secrets, 변수 참조, 날짜/숫자/문자열 연산)
* [x] `PythonFunctionDataSource` — PySpark v2 DataSource API 기반 커스텀 데이터소스

---

## EnvConfig

### 특징

- **하나의 YAML 파일**에서 `dev` / `stg` / `prd` 환경값을 키 기준으로 나란히 배치
- **Jinja2 템플릿** — secrets 참조, 변수 참조, 날짜 계산, 숫자 산술, 문자열 연산 지원
- **다중 패스 렌더링** — 변수 간 의존성을 최대 10 패스로 자동 해결
- **`project_prefix`** — `PREFIX__KEY` 환경변수로 특정 키를 런타임에 오버라이드

### 우선순위

```
환경변수 {PREFIX}__{KEY}  >  YAML 설정 (Jinja2 렌더링 후)  >  ENV_DEFAULTS 기본값
```

### 기본 사용법

```python
from ddbxutils import EnvConfig

# ENV 환경변수로 환경 결정 (기본값: dev)
cfg = EnvConfig()

# 명시적 환경 지정 + project_prefix 오버라이드 활성화
cfg = EnvConfig(env="prd", project_prefix="MYAPP")

# 설정값 접근 (세 가지 방법 모두 동일)
cfg.run_date          # 속성 접근
cfg["run_date"]       # dict 스타일
cfg.get("run_date", "2024-01-01")  # 기본값 지원

# 환경 정보
cfg.env               # "dev" / "stg" / "prd"
cfg.catalog           # "dev_catalog" (ENV_DEFAULTS 기반)
cfg.schema            # "analytics_dev"
cfg.full_table_name   # "dev_catalog.analytics_dev"
cfg.keys              # 로드된 설정 키 목록

# 요약 출력
cfg.print_summary()
```

### conf/settings.yml

```yaml
# ===========================================================
# 환경별 분기
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
# 날짜 계산 (다른 변수를 참조하여 날짜 계산 가능)
# ===========================================================
run_date: "{{today()}}"
start_date: "{{add_days(run_date, -7)}}"
last_month: "{{add_months(run_date, -1)}}"
month_start: "{{start_of_month(run_date)}}"
month_end: "{{end_of_month(run_date)}}"

# ===========================================================
# 숫자 산술
# ===========================================================
batch_size:
  dev: 1000
  stg: 5000
  prd: 10000
double_batch: "{{ batch_size * 2 }}"
page_count: "{{ batch_size // 256 }}"

# ===========================================================
# 문자열 연산
# ===========================================================
app_name: "my_project"
upper_app: "{{ app_name | upper }}"
archive_path: "{{ storage_path | replace('/data', '/archive') }}"
full_table: "{{ catalog ~ '.' ~ schema ~ '.events' }}"

# ===========================================================
# 포맷팅 + 중첩 호출
# ===========================================================
partition_date: "{{format_date(add_days(run_date, -1), '%Y%m%d')}}"
year_month: "{{format_date(run_date, '%Y%m')}}"

# ===========================================================
# 변수 참조 + 경로 조합
# ===========================================================
full_path: "{{storage_path}}/processed/{{format_date(run_date, '%Y/%m/%d')}}"

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
# 환경 공통 설정
# ===========================================================
version: "1.0.0"
```

### project_prefix 환경변수 오버라이드

`project_prefix="MYAPP"` 으로 초기화하면 `MYAPP__KEY` 형식의 환경변수로 임의 키를 덮어쓸 수 있습니다.

```shell
export MYAPP__RUN_DATE=2024-06-01
export MYAPP__CATALOG=override_catalog
export MYAPP__SCHEMA=custom_schema
```

```python
cfg = EnvConfig(env="prd", project_prefix="MYAPP")
cfg.run_date   # "2024-06-01"  ← 환경변수 우선
cfg.catalog    # "override_catalog"
```

### Jinja2 템플릿 문법 정리

#### 날짜 함수
| 문법 | 설명 |
| --- | --- |
| `{{today()}}` | 오늘 날짜 |
| `{{now()}}` | 현재 시간 |
| `{{make_date(2024, 1, 15)}}` | 특정 날짜 생성 |

#### 날짜 계산
| 문법 | 설명 |
| --- | --- |
| `{{add_days(run_date, -7)}}` | n일 추가/감소 |
| `{{add_months(run_date, -1)}}` | n개월 추가/감소 |
| `{{add_years(run_date, 1)}}` | n년 추가/감소 |
| `{{start_of_month(run_date)}}` | 해당 월 1일 |
| `{{end_of_month(run_date)}}` | 해당 월 마지막 날 |
| `{{format_date(run_date, '%Y%m%d')}}` | 날짜 포맷팅 |
| `{{format_date(add_months(run_date, -3), '%Y%m')}}` | 중첩 호출 |

#### 숫자 산술
| 문법 | 설명 |
| --- | --- |
| `{{ batch_size * 2 }}` | 곱셈 |
| `{{ batch_size + 500 }}` | 덧셈 |
| `{{ total // page_size }}` | 정수 나눗셈 |
| `{{ count % 7 }}` | 나머지 |
| `{{ 2 ** 10 }}` | 거듭제곱 |
| `{{ 'large' if count > 100 else 'small' }}` | 조건 표현식 |

#### 문자열 연산
| 문법 | 설명 |
| --- | --- |
| `{{ a ~ '_' ~ b }}` | 문자열 연결 (`~` 연산자) |
| `{{ name \| upper }}` | 대문자 변환 |
| `{{ name \| lower }}` | 소문자 변환 |
| `{{ name \| title }}` | 단어 첫 글자 대문자 |
| `{{ name \| capitalize }}` | 첫 글자만 대문자 |
| `{{ name \| trim }}` | 앞뒤 공백 제거 |
| `{{ path \| replace('/raw', '/processed') }}` | 문자열 치환 |
| `{{ tags.split(',') \| join('-') }}` | 분리 후 결합 |
| `{{ name \| length }}` | 문자열 길이 |
| `{{ code[:3] }}` | 슬라이스 |
| `{{ 'yes' if path.startswith('/data') else 'no' }}` | startswith |
| `{{ 'yes' if 'raw' in path else 'no' }}` | 포함 여부 |

#### 변수 참조
| 문법 | 설명 |
| --- | --- |
| `{{storage_path}}` | 다른 YAML 설정값 직접 참조 |
| `{{env.HOME}}` | OS 환경변수 참조 |
| `{{ENV}}`, `{{catalog}}`, `{{schema}}` | 현재 환경 정보 |
| `{{secrets/SCOPE/KEY}}` | `dbutils.secrets.get()` 호출 |

---

## Install

```shell
pip install databricks-ddbxutils
```

## Project Build

```shell
uv sync          # 의존성 설치
uv build         # wheel/sdist 빌드 (dist/ 에 생성)
```

PyPI 배포 (`~/.pypirc` 에 토큰 필요):

```shell
python3.12 -m twine upload dist/*
```

## Testing

```shell
uv run pytest tests/ -v
```

---

## Run

### in databricks w/o init_script (Serverless)

* wheel upload 용 Volume 생성 후 upload
  * `/Volumes/<CATALOG>/<DATABASE>/<VOLUME_NAME>/ddbxutils-<VERSION>-py3-none-any.whl`
* notebook 우측 Environment 에서 wheel file 추가 후 Apply
* Usage
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

### in databricks w/ init_script

* wheel 및 init_script 준비
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
