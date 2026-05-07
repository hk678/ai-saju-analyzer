"""
역법 엔진 (Calendar Engine).

담당 기능:
  - 절기 날짜 계산 (ephem 라이브러리 사용)
  - 연주·월주·일주·시주 산출
  - 야자시(夜子時) 처리
  - 양력 → 음력 변환 (korean_lunar_calendar)
"""

import math
from datetime import date, datetime, timedelta

import ephem
from korean_lunar_calendar import KoreanLunarCalendar

from core.constants import STEMS, BRANCHES, STEM_YIN_YANG, JEOLGI, DAY_BASE_DATE_PARAMS, DAY_BASE_IDX


# ── 절기 계산 ─────────────────────────────────────────────────────────────────

def get_jeolgi_date(year: int, longitude: float, cal_month: int) -> date:
    """
    태양 황경(longitude)이 특정 값에 도달하는 날짜를 반환.

    Args:
        year:       계산 연도
        longitude:  목표 태양 황경 (예: 315 = 입춘)
        cal_month:  해당 절기의 양력 월 (근사값 계산용)

    Returns:
        한국 표준시(KST) 기준 date 객체
    """
    approx = datetime(year, cal_month, 6, 12, 0)
    t = ephem.Date(approx)
    for _ in range(300):
        sun = ephem.Sun(t)
        ecl = ephem.Ecliptic(sun, epoch=ephem.J2000)
        cur = math.degrees(ecl.lon) % 360
        diff = (longitude - cur + 360) % 360
        if diff > 180:
            diff -= 360
        if abs(diff) < 1e-6:
            break
        t = ephem.Date(t + max(-20.0, min(20.0, diff / 1.0)))
    return (ephem.Date(t).datetime() + timedelta(hours=9)).date()


# ── 음력 변환 ─────────────────────────────────────────────────────────────────

def solar_to_lunar(year: int, month: int, day: int) -> tuple[int, int, bool]:
    """
    양력 → 음력 변환.

    Returns:
        (음력 월, 음력 일, 윤달 여부)
    """
    cal = KoreanLunarCalendar()
    cal.setSolarDate(year, month, day)
    return cal.lunarMonth, cal.lunarDay, cal.isIntercalation


# ── 연주 (年柱) ───────────────────────────────────────────────────────────────

def get_year_pillar(year: int) -> tuple[str, str]:
    """
    연주 천간·지지 반환.

    Args:
        year: 양력 연도

    Returns:
        (천간, 지지)
    """
    idx = (year - 4) % 60
    return STEMS[idx % 10], BRANCHES[idx % 12]


# ── 월주 (月柱) ───────────────────────────────────────────────────────────────

def get_month_pillar(year: int, month: int, day: int = 1) -> tuple[str, str]:
    """
    월주 천간·지지 반환 (오호둔법 기반).

    입춘(立春)을 기준으로 연도를 보정하고,
    절기 테이블에서 월 인덱스를 추출하여 월주를 산출한다.

    Args:
        year:  양력 연도
        month: 양력 월
        day:   양력 일

    Returns:
        (천간, 지지)
    """
    target   = date(year, month, day)
    lichun   = get_jeolgi_date(year, 315, 2)
    adj_year = year if target >= lichun else year - 1

    month_idx = 11
    for lon, _, cal_m, saju_m in JEOLGI:
        term_year = adj_year + 1 if cal_m == 1 else adj_year
        if target >= get_jeolgi_date(term_year, lon, cal_m):
            month_idx = saju_m

    year_stem_idx    = (adj_year - 4) % 10
    month_stem_start = (year_stem_idx % 5 * 2 + 2) % 10
    return STEMS[(month_stem_start + month_idx) % 10], BRANCHES[(2 + month_idx) % 12]


# ── 일주 (日柱) ───────────────────────────────────────────────────────────────

_DAY_BASE_DATE = date(*DAY_BASE_DATE_PARAMS)

def get_day_pillar(year: int, month: int, day: int) -> tuple[str, str]:
    """
    일주 천간·지지 반환.

    기준일(1992-10-24, 60갑자 인덱스 9)로부터 경과 일수를 계산한다.

    Returns:
        (천간, 지지)
    """
    delta     = (date(year, month, day) - _DAY_BASE_DATE).days
    ganji_idx = ((DAY_BASE_IDX + delta) % 60 + 60) % 60
    return STEMS[ganji_idx % 10], BRANCHES[ganji_idx % 12]


# ── 시주 (時柱) ───────────────────────────────────────────────────────────────

def get_hour_pillar(day_stem: str, hour: int, minute: int = 0) -> tuple[str, str]:
    """
    시주 천간·지지 반환.

    한국 경도 기준 보정(23:30 자시 시작)을 적용한다.
    시두법(時頭法) 공식으로 천간을 산출한다.

    Args:
        day_stem: 시주 산출 기준 일간 (야자시 처리 후 값)
        hour:     출생 시각 (0~23)
        minute:   출생 분 (0~59)

    Returns:
        (천간, 지지)
    """
    total_min  = hour * 60 + minute
    # 23:30 ~ 01:29 → 자시(index 0), 01:30 ~ 03:29 → 축시(index 1) …
    offset     = (total_min - 23 * 60 - 30 + 1440) % 1440
    branch_idx = offset // 120

    day_stem_idx = STEMS.index(day_stem)
    stem_idx     = ((day_stem_idx % 5 * 2) + branch_idx) % 10
    return STEMS[stem_idx], BRANCHES[branch_idx]


# ── 야자시(夜子時) 처리 통합 ──────────────────────────────────────────────────

def resolve_pillars(
    birth_year:   int,
    birth_month:  int,
    birth_day:    int,
    birth_hour:   int,
    birth_minute: int = 0,
    yajasi:       bool = False,
) -> tuple[str, str, str, str, str, str, str, str]:
    """
    연·월·일·시주 8글자를 야자시 처리까지 포함하여 반환.

    야자시(夜子時): 23:30 이후 출생인 경우
      - yajasi=True:  일주는 당일 기준 유지, 시주 천간만 다음날 일간으로 계산
      - yajasi=False: 일주 자체를 다음날로 교체, 시주도 다음날 일간 기준

    Returns:
        (연간, 연지, 월간, 월지, 일간, 일지, 시간, 시지)
    """
    y_stem, y_branch = get_year_pillar(birth_year)
    m_stem, m_branch = get_month_pillar(birth_year, birth_month, birth_day)
    d_stem, d_branch = get_day_pillar(birth_year, birth_month, birth_day)

    is_yajasi_time = birth_hour * 60 + birth_minute >= 23 * 60 + 30

    if is_yajasi_time:
        next_day = date(birth_year, birth_month, birth_day) + timedelta(days=1)
        next_d_stem, next_d_branch = get_day_pillar(
            next_day.year, next_day.month, next_day.day
        )
        if yajasi:
            # 야자시 적용: 일주 유지, 시주만 다음날 일간 기준
            h_day_stem = next_d_stem
        else:
            # 야자시 미적용: 일주 자체를 다음날로 교체
            d_stem, d_branch = next_d_stem, next_d_branch
            h_day_stem = next_d_stem
    else:
        h_day_stem = d_stem

    h_stem, h_branch = get_hour_pillar(h_day_stem, birth_hour, birth_minute)

    return y_stem, y_branch, m_stem, m_branch, d_stem, d_branch, h_stem, h_branch
