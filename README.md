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

[//]: # (TODO)
