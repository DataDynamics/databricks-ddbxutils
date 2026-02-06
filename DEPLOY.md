# Deploy this Project

## Prepare

* https://pypi.org/
  * 회원가입
* https://pypi.org/manage/account/
  * 2FA 추가
  * API Token 추가
* `~/.pypirc` file 에 username, password 추가
  ```text
  [pypi]
  username = __token__
  password = pypi-PASSWORDpasswordPASSWORDpasswordPASSWORDpasswordPASSWORDpasswordPASSWORDpasswordPASSWORDpasswordPASSWORDpasswordPASSWORDpasswordPASSWORDpasswordPASSWORDpasswordPASSWORDpasswo
  ```
* twine 설치
  ```shell
  pip3.12 install -U twine --break-system-packages
  pip3.11 install -U twine --break-system-packages
  pip3.13 install -U twine --break-system-packages
  pip3.14 install -U twine --break-system-packages
  ```

## Build

Project 를 build 합니다.

### poetry

```shell
poetry install
poetry build
```

### uv

```shell
uv sync
uv build
```

## Upload

Build 한 결과물을 python version  pypi 에 upload 합니다.

```shell
python3.11 -m twine upload dist/*
python3.12 -m twine upload dist/*
python3.13 -m twine upload dist/*
python3.14 -m twine upload dist/*
```

