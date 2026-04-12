"""
EnvConfig 테스트 모음

테스트 범주:
- 기본 초기화 (env, catalog, schema)
- YAML 파일 로드 및 환경별 값 해석
- project_prefix 환경변수 오버라이드
- Jinja2 날짜 함수 렌더링
- 변수 간 참조 (다중 패스)
- conf['KEY'] / conf.key / conf.get() 접근
- secrets 폴백 (dbutils 없는 환경)
- 잘못된 환경 값 예외
"""

import os
import textwrap
import pytest
from ddbxutils.config import EnvConfig


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def write_yaml(path, content: str):
    """임시 디렉토리에 YAML 파일 작성 후 경로 반환"""
    p = path / "settings.yml"
    p.write_text(textwrap.dedent(content))
    return str(p)


# ---------------------------------------------------------------------------
# 1. 기본 초기화
# ---------------------------------------------------------------------------

class TestBasicInit:
    def test_default_env_is_dev(self, tmp_path):
        cfg = EnvConfig(config_path=write_yaml(tmp_path, ""))
        assert cfg.env == "dev"

    def test_explicit_env(self, tmp_path):
        cfg = EnvConfig(env="stg", config_path=write_yaml(tmp_path, ""))
        assert cfg.env == "stg"

    def test_env_from_os_environ(self, tmp_path, monkeypatch):
        monkeypatch.setenv("ENV", "prd")
        cfg = EnvConfig(config_path=write_yaml(tmp_path, ""))
        assert cfg.env == "prd"

    def test_invalid_env_raises(self, tmp_path):
        with pytest.raises(ValueError, match="지원하지 않는 환경"):
            EnvConfig(env="qa", config_path=write_yaml(tmp_path, ""))

    def test_default_catalog_schema_dev(self, tmp_path):
        cfg = EnvConfig(env="dev", config_path=write_yaml(tmp_path, ""))
        assert cfg.catalog == "dev_catalog"
        assert cfg.schema == "analytics_dev"

    def test_default_catalog_schema_prd(self, tmp_path):
        cfg = EnvConfig(env="prd", config_path=write_yaml(tmp_path, ""))
        assert cfg.catalog == "prd_catalog"
        assert cfg.schema == "analytics_prd"

    def test_full_table_name(self, tmp_path):
        cfg = EnvConfig(env="stg", config_path=write_yaml(tmp_path, ""))
        assert cfg.full_table_name == "stg_catalog.analytics_stg"


# ---------------------------------------------------------------------------
# 2. YAML 파일 로드
# ---------------------------------------------------------------------------

class TestYamlLoading:
    YAML = """\
        run_date: "2024-03-15"
        bucket:
            dev: s3://dev-bucket
            stg: s3://stg-bucket
            prd: s3://prd-bucket
        max_retries: 3
    """

    def test_flat_key_accessible(self, tmp_path):
        cfg = EnvConfig(env="dev", config_path=write_yaml(tmp_path, self.YAML))
        assert cfg.run_date == "2024-03-15"

    def test_env_specific_value(self, tmp_path):
        cfg = EnvConfig(env="stg", config_path=write_yaml(tmp_path, self.YAML))
        assert cfg.bucket == "s3://stg-bucket"

    def test_env_specific_value_prd(self, tmp_path):
        cfg = EnvConfig(env="prd", config_path=write_yaml(tmp_path, self.YAML))
        assert cfg.bucket == "s3://prd-bucket"

    def test_numeric_value_preserved(self, tmp_path):
        cfg = EnvConfig(env="dev", config_path=write_yaml(tmp_path, self.YAML))
        assert cfg.max_retries == 3

    def test_missing_config_file_uses_defaults(self, tmp_path):
        cfg = EnvConfig(env="dev", config_path=str(tmp_path / "no_such_file.yml"))
        assert cfg.catalog == "dev_catalog"

    def test_yaml_extension_dot_yaml(self, tmp_path):
        """settings.yaml 확장자도 인식하는지 확인"""
        yaml_path = tmp_path / "settings.yaml"
        yaml_path.write_text("app_name: myapp\n")
        cfg = EnvConfig(env="dev", config_path=str(tmp_path / "settings.yml"))
        assert cfg.app_name == "myapp"

    def test_keys_property(self, tmp_path):
        cfg = EnvConfig(env="dev", config_path=write_yaml(tmp_path, self.YAML))
        assert set(cfg.keys) == {"run_date", "bucket", "max_retries"}


# ---------------------------------------------------------------------------
# 3. project_prefix 환경변수 오버라이드
# ---------------------------------------------------------------------------

class TestProjectPrefixOverride:
    YAML = """\
        run_date: "2024-01-01"
        bucket:
            dev: s3://dev-bucket
            stg: s3://stg-bucket
            prd: s3://prd-bucket
    """

    def test_prefix_overrides_yaml_value(self, tmp_path, monkeypatch):
        monkeypatch.setenv("MYAPP__RUN_DATE", "2025-12-31")
        cfg = EnvConfig(
            env="dev",
            project_prefix="MYAPP",
            config_path=write_yaml(tmp_path, self.YAML),
        )
        assert cfg.run_date == "2025-12-31"

    def test_prefix_overrides_catalog(self, tmp_path, monkeypatch):
        monkeypatch.setenv("MYAPP__CATALOG", "override_catalog")
        cfg = EnvConfig(
            env="dev",
            project_prefix="MYAPP",
            config_path=write_yaml(tmp_path, self.YAML),
        )
        assert cfg.catalog == "override_catalog"

    def test_prefix_overrides_schema(self, tmp_path, monkeypatch):
        monkeypatch.setenv("MYAPP__SCHEMA", "custom_schema")
        cfg = EnvConfig(
            env="dev",
            project_prefix="MYAPP",
            config_path=write_yaml(tmp_path, self.YAML),
        )
        assert cfg.schema == "custom_schema"

    def test_no_prefix_ignores_env_var(self, tmp_path, monkeypatch):
        monkeypatch.setenv("MYAPP__RUN_DATE", "2099-01-01")
        cfg = EnvConfig(
            env="dev",
            config_path=write_yaml(tmp_path, self.YAML),
        )
        # prefix 미설정이므로 오버라이드 무시
        assert cfg.run_date == "2024-01-01"

    def test_wrong_prefix_ignored(self, tmp_path, monkeypatch):
        monkeypatch.setenv("OTHER__RUN_DATE", "2099-01-01")
        cfg = EnvConfig(
            env="dev",
            project_prefix="MYAPP",
            config_path=write_yaml(tmp_path, self.YAML),
        )
        assert cfg.run_date == "2024-01-01"

    def test_get_with_prefix_override(self, tmp_path, monkeypatch):
        monkeypatch.setenv("MYAPP__RUN_DATE", "2030-06-01")
        cfg = EnvConfig(
            env="dev",
            project_prefix="MYAPP",
            config_path=write_yaml(tmp_path, self.YAML),
        )
        assert cfg.get("run_date") == "2030-06-01"


# ---------------------------------------------------------------------------
# 4. 접근 방법 (conf['KEY'], conf.key, conf.get())
# ---------------------------------------------------------------------------

class TestAccessPatterns:
    YAML = """\
        app_name: my_pipeline
        timeout: 30
    """

    def test_getitem_syntax(self, tmp_path):
        cfg = EnvConfig(env="dev", config_path=write_yaml(tmp_path, self.YAML))
        assert cfg["app_name"] == "my_pipeline"

    def test_attribute_syntax(self, tmp_path):
        cfg = EnvConfig(env="dev", config_path=write_yaml(tmp_path, self.YAML))
        assert cfg.app_name == "my_pipeline"

    def test_get_with_default(self, tmp_path):
        cfg = EnvConfig(env="dev", config_path=write_yaml(tmp_path, self.YAML))
        assert cfg.get("not_existing", "fallback") == "fallback"

    def test_get_existing_key(self, tmp_path):
        cfg = EnvConfig(env="dev", config_path=write_yaml(tmp_path, self.YAML))
        assert cfg.get("timeout") == 30

    def test_contains_true(self, tmp_path):
        cfg = EnvConfig(env="dev", config_path=write_yaml(tmp_path, self.YAML))
        assert "app_name" in cfg

    def test_contains_false(self, tmp_path):
        cfg = EnvConfig(env="dev", config_path=write_yaml(tmp_path, self.YAML))
        assert "ghost_key" not in cfg

    def test_getitem_missing_key_raises(self, tmp_path):
        cfg = EnvConfig(env="dev", config_path=write_yaml(tmp_path, self.YAML))
        with pytest.raises(KeyError):
            _ = cfg["ghost_key"]

    def test_attribute_missing_raises(self, tmp_path):
        cfg = EnvConfig(env="dev", config_path=write_yaml(tmp_path, self.YAML))
        with pytest.raises(AttributeError):
            _ = cfg.ghost_key


# ---------------------------------------------------------------------------
# 5. Jinja2 날짜 함수 렌더링
# ---------------------------------------------------------------------------

class TestJinjaDateFunctions:
    def test_today_function(self, tmp_path):
        yaml_path = write_yaml(tmp_path, 'run_date: "{{today()}}"\n')
        cfg = EnvConfig(env="dev", config_path=yaml_path)
        from datetime import date
        assert cfg.run_date == date.today().strftime("%Y-%m-%d")

    def test_add_days_negative(self, tmp_path):
        yaml_path = write_yaml(tmp_path, 'start_date: "{{add_days(\'2024-03-15\', -7)}}"\n')
        cfg = EnvConfig(env="dev", config_path=yaml_path)
        assert cfg.start_date == "2024-03-08"

    def test_add_days_positive(self, tmp_path):
        yaml_path = write_yaml(tmp_path, 'end_date: "{{add_days(\'2024-01-01\', 10)}}"\n')
        cfg = EnvConfig(env="dev", config_path=yaml_path)
        assert cfg.end_date == "2024-01-11"

    def test_add_months(self, tmp_path):
        yaml_path = write_yaml(tmp_path, 'prev_month: "{{add_months(\'2024-03-15\', -1)}}"\n')
        cfg = EnvConfig(env="dev", config_path=yaml_path)
        assert cfg.prev_month == "2024-02-15"

    def test_start_of_month(self, tmp_path):
        yaml_path = write_yaml(tmp_path, 'month_start: "{{start_of_month(\'2024-03-15\')}}"\n')
        cfg = EnvConfig(env="dev", config_path=yaml_path)
        assert cfg.month_start == "2024-03-01"

    def test_end_of_month(self, tmp_path):
        yaml_path = write_yaml(tmp_path, 'month_end: "{{end_of_month(\'2024-02-10\')}}"\n')
        cfg = EnvConfig(env="dev", config_path=yaml_path)
        assert cfg.month_end == "2024-02-29"  # 2024년은 윤년

    def test_format_date(self, tmp_path):
        yaml_path = write_yaml(tmp_path, "formatted: \"{{format_date('2024-03-15', '%Y%m%d')}}\"\n")
        cfg = EnvConfig(env="dev", config_path=yaml_path)
        assert cfg.formatted == "20240315"

    def test_make_date(self, tmp_path):
        yaml_path = write_yaml(tmp_path, 'fixed_date: "{{make_date(2024, 6, 1)}}"\n')
        cfg = EnvConfig(env="dev", config_path=yaml_path)
        assert cfg.fixed_date == "2024-06-01"

    def test_nested_function_call(self, tmp_path):
        yaml_path = write_yaml(
            tmp_path,
            "result: \"{{format_date(add_months('2024-03-15', -3), '%Y%m')}}\"\n",
        )
        cfg = EnvConfig(env="dev", config_path=yaml_path)
        assert cfg.result == "202312"


# ---------------------------------------------------------------------------
# 6. 변수 간 참조 (다중 패스 렌더링)
# ---------------------------------------------------------------------------

class TestCrossVariableReference:
    def test_variable_reference(self, tmp_path):
        yaml = """\
            base_date: "2024-06-15"
            derived_date: "{{add_days(base_date, -3)}}"
        """
        cfg = EnvConfig(env="dev", config_path=write_yaml(tmp_path, yaml))
        assert cfg.base_date == "2024-06-15"
        assert cfg.derived_date == "2024-06-12"

    def test_chained_variable_reference(self, tmp_path):
        """3단계 체인: a → b → c"""
        yaml = """\
            a: "2024-01-10"
            b: "{{add_days(a, 5)}}"
            c: "{{add_days(b, 5)}}"
        """
        cfg = EnvConfig(env="dev", config_path=write_yaml(tmp_path, yaml))
        assert cfg.a == "2024-01-10"
        assert cfg.b == "2024-01-15"
        assert cfg.c == "2024-01-20"

    def test_env_variable_in_template(self, tmp_path, monkeypatch):
        monkeypatch.setenv("MY_HOME", "/home/test")
        yaml = 'home_path: "{{env.MY_HOME}}"\n'
        cfg = EnvConfig(env="dev", config_path=write_yaml(tmp_path, yaml))
        assert cfg.home_path == "/home/test"

    def test_env_context_in_template(self, tmp_path):
        yaml = 'current_env: "{{ENV}}"\n'
        cfg = EnvConfig(env="stg", config_path=write_yaml(tmp_path, yaml))
        assert cfg.current_env == "stg"

    def test_catalog_in_template(self, tmp_path):
        yaml = 'table_path: "{{catalog}}.my_schema.my_table"\n'
        cfg = EnvConfig(env="dev", config_path=write_yaml(tmp_path, yaml))
        assert cfg.table_path == "dev_catalog.my_schema.my_table"


# ---------------------------------------------------------------------------
# 7. Secrets 폴백 (dbutils 없는 환경)
# ---------------------------------------------------------------------------

class TestSecretsFallback:
    def test_secret_env_var_fallback(self, tmp_path, monkeypatch):
        monkeypatch.setenv("SECRET_MYAPP_DB_PASSWORD", "super_secret")
        yaml = 'db_password: "{{secrets/myapp/db_password}}"\n'
        cfg = EnvConfig(env="dev", config_path=write_yaml(tmp_path, yaml))
        assert cfg.db_password == "super_secret"

    def test_secret_placeholder_when_no_env_var(self, tmp_path):
        yaml = 'db_password: "{{secrets/myapp/db_password}}"\n'
        cfg = EnvConfig(env="dev", config_path=write_yaml(tmp_path, yaml))
        assert cfg.db_password == "[SECRET:myapp/db_password]"


# ---------------------------------------------------------------------------
# 8. 숫자 산술 계산
# ---------------------------------------------------------------------------

class TestNumericArithmetic:
    """Jinja2 템플릿 내에서 숫자 산술이 올바르게 렌더링되는지 검증.

    렌더링 결과는 항상 str이므로 assert 는 문자열 기준으로 작성한다.
    YAML 정수값을 컨텍스트로 참조해도 Jinja2 가 타입을 보존하므로
    산술 결과도 정확하게 나온다.
    """

    # ---- 리터럴 산술 --------------------------------------------------------

    def test_literal_addition(self, tmp_path):
        cfg = EnvConfig(env="dev", config_path=write_yaml(tmp_path, 'result: "{{ 10 + 5 }}"\n'))
        assert cfg.result == "15"

    def test_literal_subtraction(self, tmp_path):
        cfg = EnvConfig(env="dev", config_path=write_yaml(tmp_path, 'result: "{{ 20 - 8 }}"\n'))
        assert cfg.result == "12"

    def test_literal_multiplication(self, tmp_path):
        cfg = EnvConfig(env="dev", config_path=write_yaml(tmp_path, 'result: "{{ 6 * 7 }}"\n'))
        assert cfg.result == "42"

    def test_literal_true_division(self, tmp_path):
        cfg = EnvConfig(env="dev", config_path=write_yaml(tmp_path, 'result: "{{ 10 / 4 }}"\n'))
        assert cfg.result == "2.5"

    def test_literal_floor_division(self, tmp_path):
        cfg = EnvConfig(env="dev", config_path=write_yaml(tmp_path, 'result: "{{ 10 // 3 }}"\n'))
        assert cfg.result == "3"

    def test_literal_modulo(self, tmp_path):
        cfg = EnvConfig(env="dev", config_path=write_yaml(tmp_path, 'result: "{{ 17 % 5 }}"\n'))
        assert cfg.result == "2"

    def test_literal_power(self, tmp_path):
        cfg = EnvConfig(env="dev", config_path=write_yaml(tmp_path, 'result: "{{ 2 ** 10 }}"\n'))
        assert cfg.result == "1024"

    # ---- YAML 정수 변수 참조 산술 -------------------------------------------

    def test_variable_addition(self, tmp_path):
        yaml = "base: 100\nresult: \"{{ base + 50 }}\"\n"
        cfg = EnvConfig(env="dev", config_path=write_yaml(tmp_path, yaml))
        assert cfg.result == "150"

    def test_variable_multiplication(self, tmp_path):
        yaml = "batch_size: 256\ndoubled: \"{{ batch_size * 2 }}\"\n"
        cfg = EnvConfig(env="dev", config_path=write_yaml(tmp_path, yaml))
        assert cfg.doubled == "512"

    def test_two_variables_arithmetic(self, tmp_path):
        yaml = "price: 1200\nqty: 3\ntotal: \"{{ price * qty }}\"\n"
        cfg = EnvConfig(env="dev", config_path=write_yaml(tmp_path, yaml))
        assert cfg.total == "3600"

    def test_variable_modulo(self, tmp_path):
        yaml = "count: 100\nremainder: \"{{ count % 7 }}\"\n"
        cfg = EnvConfig(env="dev", config_path=write_yaml(tmp_path, yaml))
        assert cfg.remainder == "2"

    # ---- 환경별 숫자 값 산술 -------------------------------------------------

    def test_env_specific_numeric_arithmetic(self, tmp_path):
        yaml = """\
            timeout:
                dev: 30
                stg: 60
                prd: 120
            extended: "{{ timeout * 2 }}"
        """
        cfg_dev = EnvConfig(env="dev", config_path=write_yaml(tmp_path, yaml))
        assert cfg_dev.extended == "60"

        cfg_prd = EnvConfig(env="prd", config_path=write_yaml(tmp_path, yaml))
        assert cfg_prd.extended == "240"

    # ---- 체인 산술 (다중 패스 렌더링) ----------------------------------------

    def test_chained_arithmetic(self, tmp_path):
        """a → b(a 기반) → c(b 기반) 3단계 체인"""
        yaml = "a: 10\nb: \"{{ a * 3 }}\"\nc: \"{{ b | int + 5 }}\"\n"
        cfg = EnvConfig(env="dev", config_path=write_yaml(tmp_path, yaml))
        assert cfg.a == 10
        assert cfg.b == "30"
        assert cfg.c == "35"

    # ---- project_prefix 환경변수 오버라이드는 문자열 --------------------------

    def test_prefix_override_numeric_returns_string(self, tmp_path, monkeypatch):
        """환경변수는 항상 str이므로 오버라이드 후 값도 str"""
        monkeypatch.setenv("APP__TIMEOUT", "999")
        yaml = "timeout: 30\n"
        cfg = EnvConfig(
            env="dev",
            project_prefix="APP",
            config_path=write_yaml(tmp_path, yaml),
        )
        assert cfg.timeout == "999"

    # ---- 조건 표현식 (숫자 비교) ---------------------------------------------

    def test_conditional_based_on_number(self, tmp_path):
        yaml = "count: 150\nlabel: \"{{ 'large' if count > 100 else 'small' }}\"\n"
        cfg = EnvConfig(env="dev", config_path=write_yaml(tmp_path, yaml))
        assert cfg.label == "large"

    def test_conditional_based_on_number_small(self, tmp_path):
        yaml = "count: 50\nlabel: \"{{ 'large' if count > 100 else 'small' }}\"\n"
        cfg = EnvConfig(env="dev", config_path=write_yaml(tmp_path, yaml))
        assert cfg.label == "small"


# ---------------------------------------------------------------------------
# 9. 문자열 연산
# ---------------------------------------------------------------------------

class TestStringOperations:
    """Jinja2 템플릿 내 문자열 연산 검증.

    렌더링 결과는 항상 str.
    """

    # ---- 연결 (~ 연산자) -----------------------------------------------------

    def test_tilde_concat_literals(self, tmp_path):
        cfg = EnvConfig(env="dev", config_path=write_yaml(tmp_path, "result: \"{{ 'hello' ~ '_' ~ 'world' }}\"\n"))
        assert cfg.result == "hello_world"

    def test_tilde_concat_variables(self, tmp_path):
        yaml = "prefix: hello\nsuffix: world\nfull: \"{{ prefix ~ '_' ~ suffix }}\"\n"
        cfg = EnvConfig(env="dev", config_path=write_yaml(tmp_path, yaml))
        assert cfg.full == "hello_world"

    def test_plus_concat_variables(self, tmp_path):
        yaml = "a: foo\nb: bar\nresult: \"{{ a + b }}\"\n"
        cfg = EnvConfig(env="dev", config_path=write_yaml(tmp_path, yaml))
        assert cfg.result == "foobar"

    # ---- 대소문자 변환 필터 ---------------------------------------------------

    def test_upper_filter(self, tmp_path):
        yaml = "name: hello\nupper_name: \"{{ name | upper }}\"\n"
        cfg = EnvConfig(env="dev", config_path=write_yaml(tmp_path, yaml))
        assert cfg.upper_name == "HELLO"

    def test_lower_filter(self, tmp_path):
        yaml = "name: WORLD\nlower_name: \"{{ name | lower }}\"\n"
        cfg = EnvConfig(env="dev", config_path=write_yaml(tmp_path, yaml))
        assert cfg.lower_name == "world"

    def test_title_filter(self, tmp_path):
        yaml = "phrase: hello world\ntitled: \"{{ phrase | title }}\"\n"
        cfg = EnvConfig(env="dev", config_path=write_yaml(tmp_path, yaml))
        assert cfg.titled == "Hello World"

    def test_capitalize_filter(self, tmp_path):
        yaml = "phrase: hello world\ncapped: \"{{ phrase | capitalize }}\"\n"
        cfg = EnvConfig(env="dev", config_path=write_yaml(tmp_path, yaml))
        assert cfg.capped == "Hello world"

    # ---- 공백 제거 필터 -------------------------------------------------------

    def test_trim_filter(self, tmp_path):
        yaml = "raw: \"  spaced  \"\ntrimmed: \"{{ raw | trim }}\"\n"
        cfg = EnvConfig(env="dev", config_path=write_yaml(tmp_path, yaml))
        assert cfg.trimmed == "spaced"

    # ---- replace 필터 --------------------------------------------------------

    def test_replace_filter(self, tmp_path):
        yaml = "path: /data/raw\nprocessed_path: \"{{ path | replace('raw', 'processed') }}\"\n"
        cfg = EnvConfig(env="dev", config_path=write_yaml(tmp_path, yaml))
        assert cfg.processed_path == "/data/processed"

    def test_replace_env_in_path(self, tmp_path):
        """환경별 경로에서 환경명 교체"""
        yaml = """\
            bucket:
                dev: s3://dev-bucket/data
                stg: s3://stg-bucket/data
                prd: s3://prd-bucket/data
            archive_bucket: "{{ bucket | replace('/data', '/archive') }}"
        """
        cfg = EnvConfig(env="dev", config_path=write_yaml(tmp_path, yaml))
        assert cfg.archive_bucket == "s3://dev-bucket/archive"

    # ---- split / join --------------------------------------------------------

    def test_split_and_join(self, tmp_path):
        yaml = "tags: \"a,b,c\"\njoined: \"{{ tags.split(',') | join('-') }}\"\n"
        cfg = EnvConfig(env="dev", config_path=write_yaml(tmp_path, yaml))
        assert cfg.joined == "a-b-c"

    # ---- length 필터 ---------------------------------------------------------

    def test_length_filter(self, tmp_path):
        yaml = "name: hello\nname_len: \"{{ name | length }}\"\n"
        cfg = EnvConfig(env="dev", config_path=write_yaml(tmp_path, yaml))
        assert cfg.name_len == "5"

    # ---- 슬라이스 ------------------------------------------------------------

    def test_string_slice(self, tmp_path):
        yaml = "code: abcdef\nshort_code: \"{{ code[:3] }}\"\n"
        cfg = EnvConfig(env="dev", config_path=write_yaml(tmp_path, yaml))
        assert cfg.short_code == "abc"

    def test_string_slice_from_end(self, tmp_path):
        yaml = "filename: report_20240315.csv\nextension: \"{{ filename[-4:] }}\"\n"
        cfg = EnvConfig(env="dev", config_path=write_yaml(tmp_path, yaml))
        assert cfg.extension == ".csv"

    # ---- 메서드 호출 (startswith / endswith) ----------------------------------

    def test_startswith(self, tmp_path):
        yaml = "path: /data/raw\nis_data: \"{{ 'yes' if path.startswith('/data') else 'no' }}\"\n"
        cfg = EnvConfig(env="dev", config_path=write_yaml(tmp_path, yaml))
        assert cfg.is_data == "yes"

    def test_endswith(self, tmp_path):
        yaml = "filename: report.csv\nis_csv: \"{{ 'yes' if filename.endswith('.csv') else 'no' }}\"\n"
        cfg = EnvConfig(env="dev", config_path=write_yaml(tmp_path, yaml))
        assert cfg.is_csv == "yes"

    # ---- in 연산자 (포함 여부) -----------------------------------------------

    def test_in_operator_true(self, tmp_path):
        yaml = "path: /data/raw\nhas_raw: \"{{ 'yes' if 'raw' in path else 'no' }}\"\n"
        cfg = EnvConfig(env="dev", config_path=write_yaml(tmp_path, yaml))
        assert cfg.has_raw == "yes"

    def test_in_operator_false(self, tmp_path):
        yaml = "path: /data/raw\nhas_proc: \"{{ 'yes' if 'processed' in path else 'no' }}\"\n"
        cfg = EnvConfig(env="dev", config_path=write_yaml(tmp_path, yaml))
        assert cfg.has_proc == "no"

    # ---- 체인 문자열 연산 (다중 패스 렌더링) ----------------------------------

    def test_chained_string_ops(self, tmp_path):
        """base → normalized(upper) → full(prefix + normalized) 체인"""
        yaml = "base: world\nnormalized: \"{{ base | upper }}\"\nfull: \"{{ 'HELLO_' ~ normalized }}\"\n"
        cfg = EnvConfig(env="dev", config_path=write_yaml(tmp_path, yaml))
        assert cfg.normalized == "WORLD"
        assert cfg.full == "HELLO_WORLD"

    # ---- 환경별 문자열 + 연산 ------------------------------------------------

    def test_env_specific_string_with_operation(self, tmp_path):
        yaml = """\
            env_label:
                dev: development
                stg: staging
                prd: production
            upper_label: "{{ env_label | upper }}"
        """
        cfg_dev = EnvConfig(env="dev", config_path=write_yaml(tmp_path, yaml))
        assert cfg_dev.upper_label == "DEVELOPMENT"

        cfg_prd = EnvConfig(env="prd", config_path=write_yaml(tmp_path, yaml))
        assert cfg_prd.upper_label == "PRODUCTION"

    # ---- catalog / schema 컨텍스트 활용 경로 조합 ----------------------------

    def test_path_with_catalog_schema(self, tmp_path):
        yaml = "table: my_table\nfull_path: \"{{ catalog ~ '.' ~ schema ~ '.' ~ table }}\"\n"
        cfg = EnvConfig(env="stg", config_path=write_yaml(tmp_path, yaml))
        assert cfg.full_path == "stg_catalog.analytics_stg.my_table"

    # ---- project_prefix 오버라이드 후 문자열 연산 ----------------------------

    def test_prefix_override_string_upper(self, tmp_path, monkeypatch):
        """PREFIX 오버라이드 값에도 Jinja2 연산이 적용되는지 확인"""
        monkeypatch.setenv("APP__BASE_PATH", "/override/path")
        yaml = "base_path: /default/path\narchive: \"{{ base_path | replace('path', 'archive') }}\"\n"
        cfg = EnvConfig(
            env="dev",
            project_prefix="APP",
            config_path=write_yaml(tmp_path, yaml),
        )
        # base_path 자체는 오버라이드되지만 archive 템플릿은 YAML 렌더링 시점에 고정됨
        assert cfg.base_path == "/override/path"
        assert cfg.archive == "/default/archive"


# ---------------------------------------------------------------------------
# 11. repr
# ---------------------------------------------------------------------------

class TestRepr:
    def test_repr_without_prefix(self, tmp_path):
        cfg = EnvConfig(env="dev", config_path=write_yaml(tmp_path, ""))
        assert "EnvConfig(env='dev'" in repr(cfg)
        assert "prefix=" not in repr(cfg)

    def test_repr_with_prefix(self, tmp_path):
        cfg = EnvConfig(env="dev", project_prefix="MYAPP", config_path=write_yaml(tmp_path, ""))
        assert "prefix='MYAPP'" in repr(cfg)
