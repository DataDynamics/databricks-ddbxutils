# =============================================================================
# 환경별 설정 로더 (EnvConfig)
# - 환경변수 ENV 하나로 환경 결정 → conf/settings.yml 에서 해당 환경 값 추출
# - Jinja2 템플릿 지원: secrets, 변수 참조, 날짜 계산
# - Python 함수 호출 스타일: {{add_days(run_date, -7)}}
# - 다중 패스 렌더링으로 변수 간 의존성 자동 해결
# - 우선순위: 환경변수({PREFIX}__{KEY}) > YAML 설정 > ENV_DEFAULTS 기본값
# =============================================================================
# 실제 프로젝트에서는 이 코드를 src/config/settings.py 에 배치합니다.

import yaml
import os
import re
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
from typing import Any, Optional
from jinja2 import Environment, BaseLoader


# =============================================================================
# 환경별 기본 매핑
# =============================================================================
ENV_DEFAULTS = {
    "dev": {"catalog": "dev_catalog", "schema": "analytics_dev"},
    "stg": {"catalog": "stg_catalog", "schema": "analytics_stg"},
    "prd": {"catalog": "prd_catalog", "schema": "analytics_prd"},
}

DEFAULT_CONFIG_PATH = "conf/settings.yml"


# =============================================================================
# 날짜 함수 정의 - Python 함수 호출 스타일로 Jinja2에서 사용
# =============================================================================
def _parse_date(value: Any) -> date:
    """문자열 또는 datetime을 date 객체로 변환"""
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        for fmt in ["%Y-%m-%d", "%Y/%m/%d", "%Y%m%d"]:
            try:
                return datetime.strptime(value, fmt).date()
            except ValueError:
                continue
        raise ValueError(f"날짜 파싱 실패: '{value}'")
    raise TypeError(f"날짜로 변환할 수 없는 타입: {type(value)}")


def add_days(value: Any, days: int) -> date:
    """{{add_days(run_date, -7)}}"""
    return _parse_date(value) + relativedelta(days=days)


def add_months(value: Any, months: int) -> date:
    """{{add_months(run_date, -1)}}"""
    return _parse_date(value) + relativedelta(months=months)


def add_years(value: Any, years: int) -> date:
    """{{add_years(run_date, 1)}}"""
    return _parse_date(value) + relativedelta(years=years)


def format_date(value: Any, fmt: str = "%Y-%m-%d") -> str:
    """{{format_date(run_date, '%Y%m%d')}}"""
    return _parse_date(value).strftime(fmt)


def start_of_month(value: Any) -> date:
    """{{start_of_month(run_date)}}"""
    return _parse_date(value).replace(day=1)


def end_of_month(value: Any) -> date:
    """{{end_of_month(run_date)}}"""
    d = _parse_date(value)
    return d.replace(day=1) + relativedelta(months=1) - relativedelta(days=1)


def today() -> date:
    """{{today()}}"""
    return date.today()


def now() -> datetime:
    """{{now()}}"""
    return datetime.now()


def make_date(year: int, month: int, day: int) -> date:
    """{{make_date(2024, 1, 15)}}"""
    return date(year, month, day)


class EnvConfig:
    """환경변수 ENV 기반 설정 관리 클래스 (Jinja2 템플릿 지원)

    Jinja2 템플릿 문법 (Python 함수 호출 스타일):

        날짜 함수:
            {{today()}}                            → 오늘 날짜
            {{now()}}                              → 현재 시간
            {{make_date(2024, 1, 15)}}             → 특정 날짜

        날짜 계산 (다른 변수 참조 가능):
            {{add_days(run_date, -7)}}             → run_date에서 7일 전
            {{add_months(run_date, -1)}}           → run_date에서 1개월 전
            {{add_years(run_date, 1)}}             → run_date에서 1년 후
            {{start_of_month(run_date)}}           → run_date 해당 월 1일
            {{end_of_month(run_date)}}             → run_date 해당 월 마지막 날

        포맷팅 및 중첩:
            {{format_date(run_date, '%Y%m%d')}}    → 날짜 포맷팅
            {{format_date(add_months(run_date, -3), '%Y%m')}}  → 중첩 호출

        변수/환경 참조:
            {{storage_path}}                       → 다른 설정값 직접 참조
            {{env.HOME}}                           → OS 환경변수
            {{ENV}}, {{catalog}}, {{schema}}       → 현재 환경 정보

        Secrets:
            {{secrets/SCOPE/KEY}}                  → dbutils.secrets.get()

    우선순위:
        1. 환경변수 {PREFIX}__{KEY}
        2. YAML 설정 (Jinja2 템플릿 처리 후)
        3. ENV_DEFAULTS 기본값
    """

    MAX_RENDER_PASSES = 10

    def __init__(
        self,
        env: Optional[str] = None,
        project_prefix: Optional[str] = None,
        config_path: Optional[str] = None,
    ):
        self.env = env or os.environ.get("ENV", "dev")
        self.project_prefix = project_prefix

        if self.env not in ENV_DEFAULTS:
            raise ValueError(
                f"지원하지 않는 환경: '{self.env}'. 허용: {list(ENV_DEFAULTS.keys())}"
            )

        defaults = ENV_DEFAULTS[self.env]
        self.catalog = defaults["catalog"]
        self.schema = defaults["schema"]

        self.config_path = config_path or self._env_override(
            "CONFIG_PATH", DEFAULT_CONFIG_PATH
        )

        # Jinja2 환경 초기화
        self._jinja_env = self._create_jinja_env()

        # YAML 로드 → 환경별 값 추출 → Jinja2 다중 패스 렌더링
        self._raw_config = self._load_config()
        self._config_pre_template = self._resolve_env_values(self._raw_config)
        self._config = self._render_templates(self._config_pre_template)

        # PREFIX 환경변수 오버라이드
        self.catalog = self._env_override("CATALOG", self.catalog)
        self.schema = self._env_override("SCHEMA", self.schema)
        self._overrides = self._detect_overrides()

    # =========================================================================
    # Jinja2 환경 설정
    # =========================================================================
    def _create_jinja_env(self) -> Environment:
        """날짜 함수를 전역 함수 + 필터 둘 다로 등록"""
        env = Environment(loader=BaseLoader())

        # 전역 함수 등록 - Python 함수 호출 스타일 {{add_days(run_date, -7)}}
        env.globals["today"] = today
        env.globals["now"] = now
        env.globals["make_date"] = make_date
        env.globals["add_days"] = add_days
        env.globals["add_months"] = add_months
        env.globals["add_years"] = add_years
        env.globals["format_date"] = format_date
        env.globals["start_of_month"] = start_of_month
        env.globals["end_of_month"] = end_of_month

        # 필터도 등록 - 파이프 스타일 {{run_date | add_days(-7)}} 도 사용 가능
        env.filters["add_days"] = add_days
        env.filters["add_months"] = add_months
        env.filters["add_years"] = add_years
        env.filters["format_date"] = format_date
        env.filters["start_of_month"] = start_of_month
        env.filters["end_of_month"] = end_of_month

        return env

    # =========================================================================
    # 다중 패스 템플릿 렌더링 - 변수 간 의존성 자동 해결
    # =========================================================================
    def _render_templates(self, config: dict) -> dict:
        """다중 패스로 템플릿 렌더링.

        예) run_date: "{{today()}}" → 1패스에서 "2026-04-12"로 해결
            start_date: "{{add_days(run_date, -7)}}" → run_date가 해결된 후 2패스에서 해결
        """
        rendered = dict(config)

        for pass_num in range(self.MAX_RENDER_PASSES):
            changed = False
            is_final = (pass_num == self.MAX_RENDER_PASSES - 1)

            for key in list(rendered.keys()):
                value = rendered[key]
                new_value = self._render_value(value, rendered, silent=not is_final)
                if new_value != value:
                    rendered[key] = new_value
                    changed = True

            if not changed:
                break

        return rendered

    def _render_value(self, value: Any, ctx: dict, silent: bool = False) -> Any:
        """값 하나에 Jinja2 템플릿 적용 (재귀적)"""
        if isinstance(value, str) and "{{" in value and "}}" in value:
            return self._render_string(value, ctx, silent)
        elif isinstance(value, list):
            return [self._render_value(v, ctx, silent) for v in value]
        elif isinstance(value, dict):
            return {k: self._render_value(v, ctx, silent) for k, v in value.items()}
        return value

    def _render_string(self, template_str: str, ctx: dict, silent: bool = False) -> Any:
        """문자열에 Jinja2 템플릿 적용"""
        # 1) {{secrets/SCOPE/KEY}} 처리 - Jinja2 전에 먼저 처리
        template_str = self._process_secrets(template_str)

        # 2) Jinja2 컨텍스트 구성
        #    - 설정값을 토프 레벨에 등록하여 run_date 로 직접 참조 가능
        context = {
            **ctx,                       # {{run_date}}, {{storage_path}} 등 직접 참조
            "config": ctx,               # {{config.run_date}} 도 가능 (호환)
            "env": os.environ,           # {{env.HOME}}
            "ENV": self.env,             # {{ENV}}
            "catalog": self.catalog,     # {{catalog}}
            "schema": self.schema,       # {{schema}}
        }

        try:
            template = self._jinja_env.from_string(template_str)
            result = template.render(context)

            # date/datetime 결과는 문자열로 변환
            if isinstance(result, (date, datetime)):
                return result.strftime("%Y-%m-%d")
            return result
        except Exception as e:
            if not silent:
                print(f"⚠️ 템플릿 렌더링 실패: {template_str} - {e}")
            return template_str

    def _process_secrets(self, template_str: str) -> str:
        """{{secrets/SCOPE/KEY}} 패턴을 실제 값으로 치환"""
        pattern = r"\{\{\s*secrets/([^/]+)/([^}\s]+)\s*\}\}"

        def replace_secret(match):
            scope, key = match.group(1), match.group(2)
            try:
                return dbutils.secrets.get(scope, key)
            except NameError:
                env_key = f"SECRET_{scope.upper()}_{key.upper()}"
                fallback = os.environ.get(env_key, f"[SECRET:{scope}/{key}]")
                return fallback
            except Exception as e:
                print(f"❌ Secret 조회 실패 ({scope}/{key}): {e}")
                return f"[SECRET_ERROR:{scope}/{key}]"

        return re.sub(pattern, replace_secret, template_str)

    # =========================================================================
    # 동적 속성 접근
    # =========================================================================
    def __getattr__(self, name: str) -> Any:
        if name.startswith("_"):
            raise AttributeError(name)
        config = self.__dict__.get("_config", {})
        if name in config:
            return self._env_override(name.upper(), config[name])
        raise AttributeError(
            f"'{type(self).__name__}'에 '{name}' 설정이 없습니다. "
            f"사용 가능: {list(config.keys())}"
        )

    def __getitem__(self, key: str) -> Any:
        return self.get(key)

    def __contains__(self, key: str) -> bool:
        return key in self._config

    # =========================================================================
    # 내부 메서드
    # =========================================================================
    def _env_override(self, key: str, current_value: Any) -> Any:
        if not self.project_prefix:
            return current_value
        return os.environ.get(f"{self.project_prefix}__{key}", current_value)

    def _detect_overrides(self) -> dict:
        if not self.project_prefix:
            return {}
        return {
            k: v for k, v in os.environ.items()
            if k.startswith(f"{self.project_prefix}__")
        }

    def _load_config(self) -> dict:
        candidates = [self.config_path]
        if self.config_path.endswith(".yml"):
            candidates.append(self.config_path[:-4] + ".yaml")
        elif self.config_path.endswith(".yaml"):
            candidates.append(self.config_path[:-5] + ".yml")

        for path in candidates:
            try:
                with open(path, "r") as f:
                    config = yaml.safe_load(f)
                    print(f"✅ 설정 파일 로드: {path}")
                    return config or {}
            except FileNotFoundError:
                continue
            except yaml.YAMLError as e:
                print(f"❌ YAML 파싱 오류: {e}")
                return {}

        print(f"⚠️ 설정 파일 없음: {self.config_path} - 기본값 사용")
        return {}

    def _resolve_env_values(self, raw: dict) -> dict:
        resolved = {}
        for key, value in raw.items():
            if isinstance(value, dict) and self.env in value:
                resolved[key] = value[self.env]
            elif isinstance(value, dict):
                print(f"⚠️ '{key}'에 '{self.env}' 환경값 없음: {list(value.keys())}")
                resolved[key] = None
            else:
                resolved[key] = value
        return resolved

    # =========================================================================
    # 핵심 속성
    # =========================================================================
    @property
    def full_table_name(self) -> str:
        return f"{self.catalog}.{self.schema}"

    @property
    def keys(self) -> list:
        return list(self._config.keys())

    def get(self, key: str, default: Any = None) -> Any:
        yaml_value = self._config.get(key, default)
        return self._env_override(key.upper(), yaml_value)

    def __repr__(self) -> str:
        prefix = f", prefix='{self.project_prefix}'" if self.project_prefix else ""
        return f"EnvConfig(env='{self.env}', catalog='{self.catalog}', schema='{self.schema}'{prefix})"

    def print_summary(self):
        print("=" * 60)
        print(f"  🔧 환경 설정 요약")
        print("=" * 60)
        print(f"  환경          : {self.env}")
        print(f"  PREFIX       : {self.project_prefix or '(미설정)'}")
        print(f"  카탈로그      : {self.catalog}")
        print(f"  스키마        : {self.schema}")
        print(f"  테이블 경로   : {self.full_table_name}")
        print(f"  설정 파일     : {self.config_path}")
        if self._config:
            print(f"\n  📋 설정 값 ({len(self._config)}개):")
            for key in sorted(self._config.keys()):
                val = self._env_override(key.upper(), self._config[key])
                display_val = str(val)[:60] + "..." if len(str(val)) > 60 else val
                print(f"    {key} = {display_val}")
        if self._overrides:
            print(f"\n  🔄 환경변수 오버라이드:")
            for k, v in self._overrides.items():
                print(f"    {k} = {v}")
        print("=" * 60)
