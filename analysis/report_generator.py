"""
리포트 생성 오케스트레이터 (Report Generator).

프리미엄·기본 리포트 전체 생성 흐름을 담당한다.
섹션별 분석 함수와 API 클라이언트를 조율하되,
프롬프트·계산 로직은 직접 포함하지 않는다.

역방향 의존성 수정:
  구버전 gemini_analyzer.py:1238 에서 함수 본문 안에서
  `from saju_calculator import get_seun` 을 하던 패턴을
  이 오케스트레이터 최상단 import 로 이동하여 의존성을 명시적으로 관리한다.
"""

import json
from datetime import datetime

from analysis.gemini_client import ApiUnavailableError, load_db, make_key_pool
from analysis.sections_premium import (
    analyze_personality,
    analyze_wealth,
    analyze_career,
    analyze_love,
    analyze_health,
    analyze_lucky_charm,
    analyze_relationships,
    analyze_fortune_peaks,
    analyze_yearly_fortune,
    analyze_monthly_fortune,
)
from analysis.sections_basic import (
    analyze_personality_basic,
    analyze_basic_overview,
    analyze_basic_thisyear,
)
# 계산 레이어에서 세운 데이터를 직접 생성 (폴백용)
from core.saju_calculator import get_seun


# ── 프리미엄 리포트 ───────────────────────────────────────────────────────────

def generate_premium_report(
    api_keys_input,
    saju_data: dict,
    target_year: int = None,
    progress_callback=None,
    progress_save_path: str = None,
    skip_keys: set = None,
) -> dict:
    """
    프리미엄 100페이지 리포트 전체 생성.

    Args:
        api_keys_input:      콤마 구분 문자열 또는 리스트
        saju_data:           calculate_saju() 반환값 + "세운"/"월운" 키 포함
        target_year:         기준 연도 (None이면 현재 연도)
        progress_callback:   (step, total, msg) → None
        progress_save_path:  진행 상황 자동 저장 경로 (.json)
        skip_keys:           이미 완료된 항목 키 집합 (재시작용)

    Returns:
        {
          "personality": str, "wealth": str, ...,   # 8개 기본 섹션
          "yearly": {"2026": str, ...},              # 세운
          "monthly": {"2026-01": str, ...},          # 월운
        }
    """
    if target_year is None:
        target_year = datetime.now().year
    if skip_keys is None:
        skip_keys = set()

    pool    = make_key_pool(api_keys_input)
    db      = load_db()
    results: dict = {}

    print(f"  🔑 API 키 {len(pool)}개 로드 완료 (라운드 로빈 활성화)")

    wolun_list = saju_data.get("월운", [])
    seun_list  = saju_data.get("세운", [])
    total_steps = 8 + len(seun_list) + len(wolun_list)
    step = 0

    def _autosave() -> None:
        if progress_save_path:
            with open(progress_save_path, "w", encoding="utf-8") as f:
                json.dump(results, f, ensure_ascii=False, indent=2)

    def _progress(msg: str) -> None:
        nonlocal step
        step += 1
        if progress_callback:
            progress_callback(step, total_steps, msg)
        else:
            print(f"  [{step}/{total_steps}] {msg}")

    # ── 섹션 1~8: 기본 분석 ──────────────────────────────────────────────────
    print("\n📖 기본 분석 섹션 생성 중...")

    _BASIC_SECTIONS = [
        ("personality",   "성격/본질 분석 중...",           lambda: analyze_personality(pool, saju_data, db)),
        ("wealth",        "재물운 분석 중...",               lambda: analyze_wealth(pool, saju_data, db)),
        ("career",        "직업/직장운 분석 중...",           lambda: analyze_career(pool, saju_data, db)),
        ("love",          "연애/결혼운 분석 중...",           lambda: analyze_love(pool, saju_data, db)),
        ("health",        "건강운 분석 중...",               lambda: analyze_health(pool, saju_data, db)),
        ("lucky_charm",   "개운 가이드 작성 중...",           lambda: analyze_lucky_charm(pool, saju_data, db)),
        ("relationships", "인간관계·가족운 분석 중...",       lambda: analyze_relationships(pool, saju_data, db)),
        ("fortune_peaks", "인생 상승기·저운 분석 중...",      lambda: analyze_fortune_peaks(pool, saju_data, db)),
    ]

    for key, msg, fn in _BASIC_SECTIONS:
        _progress(msg)
        if key in skip_keys:
            print(f"  ⏭  {key} — 이미 완료, 건너뜀")
            continue
        results[key] = fn()
        _autosave()

    # ── 월운 루프 ─────────────────────────────────────────────────────────────
    print("\n📆 월운 분석 생성 중...")
    if "monthly" not in results:
        results["monthly"] = {}

    for wolun in wolun_list:
        yr        = wolun["연도"]
        m         = wolun["월"]
        ym_str    = f"{yr}-{m:02d}"
        month_key = f"monthly.{ym_str}"
        _progress(f"{yr}년 {m}월 월운 분석 중...")
        if month_key in skip_keys:
            print(f"  ⏭  {yr}년 {m}월 월운 — 이미 완료, 건너뜀")
            continue
        results["monthly"][ym_str] = analyze_monthly_fortune(pool, saju_data, wolun)
        _autosave()

    # ── 세운 루프 ─────────────────────────────────────────────────────────────
    print("\n📅 세운(연운) 분석 생성 중...")
    if "yearly" not in results:
        results["yearly"] = {}

    for seun in seun_list:
        yr      = seun["연도"]
        yr_str  = str(yr)
        yr_key  = f"yearly.{yr_str}"
        _progress(f"{yr}년 세운 분석 중...")
        if yr_key in skip_keys:
            print(f"  ⏭  {yr}년 세운 — 이미 완료, 건너뜀")
            continue
        results["yearly"][yr_str] = analyze_yearly_fortune(pool, saju_data, seun)
        _autosave()

    return results


# ── 기본 리포트 ───────────────────────────────────────────────────────────────

def generate_basic_report(
    api_keys_input,
    saju_data: dict,
    target_year: int = None,
) -> dict:
    """
    기본 리포트 생성 (목표 10페이지).
    섹션: 성격·기질 / 전반 운세 요약 / 신년 총평

    폴백:
      saju_data["세운"] 에 target_year 항목이 없을 경우
      core.saju_calculator.get_seun() 으로 현장 계산 후 사용한다.
      (구버전의 함수 내부 동적 import 패턴을 최상단 import로 교체)

    Returns:
        {"personality": str, "summary": str, "this_year": str}
    """
    if target_year is None:
        target_year = datetime.now().year

    pool     = make_key_pool(api_keys_input)
    db       = load_db()
    results: dict = {}

    print(f"  🔑 API 키 {len(pool)}개 로드 완료 (라운드 로빈 활성화)")

    try:
        print("  [1/3] 성격·기질 분석 중...")
        results["personality"] = analyze_personality_basic(pool, saju_data, db)

        print("  [2/3] 전반 운세 요약 중...")
        results["summary"] = analyze_basic_overview(pool, saju_data, target_year, db)

        print(f"  [3/3] {target_year}년 간략 총평 중...")
        seun_list      = saju_data.get("세운", [])
        this_year_seun = next(
            (s for s in seun_list if s["연도"] == target_year), None
        )

        if this_year_seun is None:
            # 폴백: 계산 레이어에서 직접 생성
            d_stem   = saju_data["일간정보"]["일간"]
            y_branch = saju_data["사주원국"]["연주"]["지지"]
            d_branch = saju_data["사주원국"]["일주"]["지지"]
            this_year_seun = get_seun(target_year, d_stem, y_branch, d_branch)

        results["this_year"] = analyze_basic_thisyear(pool, saju_data, this_year_seun)

    except ApiUnavailableError as e:
        print(f"\n🛑 API 연속 실패로 전체 생성을 중단합니다: {e}")
        raise

    return results
