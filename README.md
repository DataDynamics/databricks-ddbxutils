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

### in databricks w/o init_script

* Add Wheel
  * wheel upload 용 Volume 생성 후 upload
    * `/Volumes/<CATALOG>/<DATABASE>/<VOLUME_NAME>/ddbxutils-<VERSION>-py3-none-any.whl`
  * notebook 의 우측 Environment 에서 Environment version 2로 지정 후 volume 에 upload 한 wheel file 추가 후 Apply

### in databricks w/ init_script

[//]: # (TODO)
