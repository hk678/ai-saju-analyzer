"""
프리미엄 리포트 섹션 분석 함수 (8개 + 세운·월운).

각 함수는 프롬프트를 직접 작성하지 않고
analysis.prompt_templates에서 가져와 checked_call에 전달하기만 한다.
"""

from analysis.gemini_client import KeyPool, checked_call
from analysis.prompt_templates import (
    build_prompt_personality,
    build_prompt_wealth,
    build_prompt_career,
    build_prompt_love,
    build_prompt_health,
    build_prompt_lucky_charm,
    build_prompt_relationships,
    build_prompt_fortune_peaks,
    build_prompt_yearly_fortune,
    build_prompt_monthly_fortune,
)


def analyze_personality(pool: KeyPool, saju_data: dict, db: dict) -> str:
    """섹션 1: 타고난 본질 및 성격 분석 (A4 3장 이상)"""
    return checked_call(pool, build_prompt_personality(saju_data, db))


def analyze_wealth(pool: KeyPool, saju_data: dict, db: dict) -> str:
    """섹션 2: 재물운 분석 (A4 2.5장 이상)"""
    return checked_call(pool, build_prompt_wealth(saju_data, db))


def analyze_career(pool: KeyPool, saju_data: dict, db: dict) -> str:
    """섹션 3: 직업/직장운 분석 (A4 2.5장 이상)"""
    return checked_call(pool, build_prompt_career(saju_data, db))


def analyze_love(pool: KeyPool, saju_data: dict, db: dict) -> str:
    """섹션 4: 연애/결혼운 분석 (A4 2.5장 이상)"""
    return checked_call(pool, build_prompt_love(saju_data, db))


def analyze_health(pool: KeyPool, saju_data: dict, db: dict) -> str:
    """섹션 5: 건강운 분석 (A4 2장 이상)"""
    return checked_call(pool, build_prompt_health(saju_data, db))


def analyze_lucky_charm(pool: KeyPool, saju_data: dict, db: dict) -> str:
    """섹션 6: 맞춤형 개운 가이드 (A4 2.5장 이상)"""
    return checked_call(pool, build_prompt_lucky_charm(saju_data, db))


def analyze_relationships(pool: KeyPool, saju_data: dict, db: dict) -> str:
    """섹션 7: 인간관계·가족운 분석 (A4 2.5장 이상)"""
    return checked_call(pool, build_prompt_relationships(saju_data, db))


def analyze_fortune_peaks(pool: KeyPool, saju_data: dict, db: dict) -> str:
    """섹션 8: 인생의 상승기와 저운의 시기 (1,400자 이내)"""
    return checked_call(pool, build_prompt_fortune_peaks(saju_data, db))


def analyze_yearly_fortune(pool: KeyPool, saju_data: dict, seun: dict) -> str:
    """세운(年運) 분석"""
    return checked_call(pool, build_prompt_yearly_fortune(saju_data, seun))


def analyze_monthly_fortune(pool: KeyPool, saju_data: dict, wolun: dict) -> str:
    """월운(月運) 분석"""
    return checked_call(pool, build_prompt_monthly_fortune(saju_data, wolun))
