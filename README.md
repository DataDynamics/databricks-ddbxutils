# databricks-ddbxutils

dbutils 로 부족한 부분을 확장한 ddbxutils

## Feature

* [x] `dbutils.widgets` 에 jinja2 template 적용

## setup

```shell
cd <PROJECT_ROOT>
pip install poetry
```

## venv

```shell
poetry shell
```

## Build

```shell
poetry build
```

## Run

### in databricks w/o init_script(= Serverless)

* Add Wheel
  * wheel upload 용 Volume 생성 후 upload
    * `/Volumes/<CATALOG>/<DATABASE>/<VOLUME_NAME>/ddbxutils-<VERSION>-py3-none-any.whl`
  * notebook 의 우측 Environment 에서 Environment version 2로 지정 후 volume 에 upload 한 wheel file 추가 후 Apply
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