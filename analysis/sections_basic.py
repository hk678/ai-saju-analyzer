"""
기본 리포트 섹션 분석 함수 (3개).

프리미엄과 동일한 구조 — 프롬프트 빌드는 prompt_templates에 위임,
API 호출만 checked_call로 수행한다.
"""

from analysis.gemini_client import KeyPool, checked_call
from analysis.prompt_templates import (
    build_prompt_personality_basic,
    build_prompt_basic_overview,
    build_prompt_basic_thisyear,
)


def analyze_personality_basic(pool: KeyPool, saju_data: dict, db: dict) -> str:
    """기본 리포트용 성격·기질 분석 (A4 1.5장)"""
    return checked_call(pool, build_prompt_personality_basic(saju_data, db))


def analyze_basic_overview(
    pool: KeyPool, saju_data: dict, target_year: int, db: dict
) -> str:
    """기본 리포트용 전반 운세 요약 (재물·직업·연애·건강 각 2~4줄)"""
    return checked_call(pool, build_prompt_basic_overview(saju_data, target_year))


def analyze_basic_thisyear(pool: KeyPool, saju_data: dict, seun: dict) -> str:
    """기본 리포트용 신년 총평 (3~5줄)"""
    return checked_call(pool, build_prompt_basic_thisyear(saju_data, seun))
