"""
만세력 계산 엔진
- 양력 → 음력 변환
- 연/월/일/시주 (8글자) 추출
- 십성, 오행, 12운성, 신살 계산
- 대운 / 세운 / 월운 계산

[대운/세운/월운 공통 데이터 구조]
_build_pillar_block() 반환:
{
  "간지": {"천간": "辛", "지지": "卯"},
  "천간": {
      "문자": "辛",
      "오행": "금",
      "십성": {"값": "정인", "기준": "일간"}
  },
  "지지": {
      "문자": "卯",
      "오행": "목",
      "십성": {"값": "편관", "기준": "일간"},
      "12운성": "절",
      "신살": ["역마살"]   ← 대운/세운/월운 모두 포함
  }
}

대운 최종 구조 (위 블록 + 메타):
{
  "순서": 1,
  "시작나이": 8,
  ...블록...
}

세운 최종 구조:
{
  "연도": 2026,
  ...블록...
}

월운 최종 구조:
{
  "연도": 2026,
  "월": 3,
  ...블록...
}
"""

import math
import ephem
from datetime import date, datetime, timedelta
from korean_lunar_calendar import KoreanLunarCalendar

STEMS    = ["甲", "乙", "丙", "丁", "戊", "己", "庚", "辛", "壬", "癸"]
STEMS_KR = ["갑", "을", "병", "정", "무", "기", "경", "신", "임", "계"]
BRANCHES    = ["子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"]
BRANCHES_KR = ["자", "축", "인", "묘", "진", "사", "오", "미", "신", "유", "술", "해"]

STEM_ELEMENT = {
    "甲": "목", "乙": "목", "丙": "화", "丁": "화", "戊": "토",
    "己": "토", "庚": "금", "辛": "금", "壬": "수", "癸": "수",
}
BRANCH_ELEMENT = {
    "子": "수", "丑": "토", "寅": "목", "卯": "목", "辰": "토", "巳": "화",
    "午": "화", "未": "토", "申": "금", "酉": "금", "戌": "토", "亥": "수",
}
STEM_YIN_YANG = {
    "甲": "양", "乙": "음", "丙": "양", "丁": "음", "戊": "양",
    "己": "음", "庚": "양", "辛": "음", "壬": "양", "癸": "음",
}
BRANCH_HIDDEN_STEMS = {
    "子": ["壬", "癸"], "丑": ["癸", "辛", "己"], "寅": ["戊", "丙", "甲"],
    "卯": ["甲", "乙"], "辰": ["乙", "癸", "戊"], "巳": ["戊", "庚", "丙"],
    "午": ["丙", "己", "丁"], "未": ["丁", "乙", "己"], "申": ["戊", "壬", "庚"],
    "酉": ["庚", "辛"], "戌": ["辛", "丁", "戊"], "亥": ["戊", "甲", "壬"],
}

_GENERATE     = {"목": "화", "화": "토", "토": "금", "금": "수", "수": "목"}
_OVERCOME     = {"목": "토", "화": "금", "토": "수", "금": "목", "수": "화"}
_GENERATED_BY = {v: k for k, v in _GENERATE.items()}
_OVERCOME_BY  = {v: k for k, v in _OVERCOME.items()}

_JEOLGI = [
    (315, "입춘",  2,  0), (345, "경칩",  3,  1), ( 15, "청명",  4,  2),
    ( 45, "입하",  5,  3), ( 75, "망종",  6,  4), (105, "소서",  7,  5),
    (135, "입추",  8,  6), (165, "백로",  9,  7), (195, "한로", 10,  8),
    (225, "입동", 11,  9), (255, "대설", 12, 10), (285, "소한",  1, 11),
]

TWELVE_STATES = ["장생", "목욕", "관대", "건록", "제왕", "쇠", "병", "사", "묘", "절", "태", "양"]
TWELVE_STATE_TABLE = {
    "甲": ["亥","子","丑","寅","卯","辰","巳","午","未","申","酉","戌"],
    "乙": ["午","巳","辰","卯","寅","丑","子","亥","戌","酉","申","未"],
    "丙": ["寅","卯","辰","巳","午","未","申","酉","戌","亥","子","丑"],
    "丁": ["酉","申","未","午","巳","辰","卯","寅","丑","子","亥","戌"],
    "戊": ["寅","卯","辰","巳","午","未","申","酉","戌","亥","子","丑"],
    "己": ["酉","申","未","午","巳","辰","卯","寅","丑","子","亥","戌"],
    "庚": ["巳","午","未","申","酉","戌","亥","子","丑","寅","卯","辰"],
    "辛": ["子","亥","戌","酉","申","未","午","巳","辰","卯","寅","丑"],
    "壬": ["申","酉","戌","亥","子","丑","寅","卯","辰","巳","午","未"],
    "癸": ["卯","寅","丑","子","亥","戌","酉","申","未","午","巳","辰"],
}

# ── 12신살 + 주요신살 완전 테이블 ─────────────────────────────────────────────
#
# 12신살은 "삼합 그룹의 기준지지(년지 or 일지)"를 기반으로 계산한다.
# 삼합 3그룹: 申子辰(수국), 寅午戌(화국), 巳酉丑(금국), 亥卯未(목국)
# 각 그룹의 "중심지(장성지)"를 기준으로 12지지를 순환하면
# 12개 신살 이름이 대응된다.
#
# 순서(장성 기준 +0 ~ +11):
#   장성(+0) → 반안(+1) → 역마(+6 = 충) → 육해(+10) → 화개(+11=끝)
#   겁살(-3=앞 그룹 끝) → 재살(-2) → 천살(-1) → 지살(+0-그룹시작) → 년살(+1) → 월살(+3) → 망신(+5)
#
# 구현은 "기준지지 → 12신살 위치 매핑" 딕셔너리로 단순화한다.
#
# key: 기준지지(년지 or 일지)
# value: {지지문자: 신살이름}

def _build_12shinsal_map() -> dict:
    """
    12신살 전체 매핑 테이블 생성.
    반환: { 기준지지: { 대상지지: 신살이름 } }

    삼합 4그룹 × 12신살 = 48 케이스 전체 커버.
    """
    # 4개 삼합 그룹 (시작, 중심[장성], 끝)
    # 방향: 지지 순서대로 +1씩 (子=0, 丑=1, ... 亥=11)
    # 겁살=중심-3, 재살=중심-2, 천살=중심-1,
    # 지살=중심-3+1(시작글자), 년살=시작+1,
    # 월살=중심+3, 망신=중심+5, 장성=중심+0,
    # 반안=중심+1, 역마=중심+6(충), 육해=중심+10, 화개=중심+11
    #
    # 더 직관적으로: 삼합의 첫글자(지살)를 기준으로 +0~+11 매핑

    # 삼합 그룹별 "지살(시작지지)" 인덱스
    # 申子辰水局 → 지살=申(9), 장성=子(0→12로 환산하면 9+3=12%12=0), 화개=辰(3)
    # 寅午戌火局 → 지살=寅(2), 장성=午(6), 화개=戌(10)
    # 巳酉丑金局 → 지살=巳(5), 장성=酉(9→실제인덱스 8 아님, 酉=9), 화개=丑(1)
    # 亥卯未木局 → 지살=亥(11), 장성=卯(3), 화개=未(7)
    #
    # 12신살 순서 (지살=+0 기준):
    # +0:지살, +1:년살, +2:월살, +3:장성, +4:반안, +5:역마,
    # +6:육해, +7:화개, +8:겁살, +9:재살, +10:천살, +11:망신
    #
    # ※ 국내 명리학 통설(삼합기준 12신살):
    # 地殺(지살)=삼합시작, 年殺(년살)=시작+1, 月殺(월살)=시작+2,
    # 將星(장성)=삼합중심, 攀鞍(반안)=중심+1, 驛馬(역마)=삼합끝(충),
    # 六害(육해)=끝+1, 華蓋(화개)=끝+2,
    # 劫殺(겁살)=이전삼합끝(충에서-1), 災殺(재살)=충, 天殺(천살)=충+1,
    # 亡身(망신)=중심-1
    #
    # 가장 보편적으로 쓰이는 정리:
    # 기준지지(년지/일지)가 속한 삼합 그룹 결정 후,
    # 12지지를 그룹 시작지지부터 순환하며 이름 부여.
    # 순서: 겁살,재살,천살,지살,년살,월살,망신,장성,반안,역마,육해,화개

    # 삼합 그룹: 시작지지 인덱스 (겁살 위치 = 시작-1의 삼합끝 = 이전그룹 끝)
    # 실제 순서 (겁살부터):
    #   申子辰: 겁살=巳,재살=午,천살=未,지살=申,년살=酉,월살=戌,망신=亥,장성=子,반안=丑,역마=寅,육해=卯,화개=辰
    #   寅午戌: 겁살=亥,재살=子,천살=丑,지살=寅,년살=卯,월살=辰,망신=巳,장성=午,반안=未,역마=申,육해=酉,화개=戌
    #   巳酉丑: 겁살=寅,재살=卯,천살=辰,지살=巳,년살=午,월살=未,망신=申,장성=酉,반안=戌,역마=亥,육해=子,화개=丑
    #   亥卯未: 겁살=申,재살=酉,천살=戌,지살=亥,년살=子,월살=丑,망신=寅,장성=卯,반안=辰,역마=巳,육해=午,화개=未

    ORDER = ["겁살","재살","천살","지살","년살","월살","망신살","장성살","반안살","역마살","육해살","화개살"]

    # 4그룹 × (겁살 시작 지지 인덱스)
    groups_start = {
        # 기준 그룹(년지/일지)  : 겁살 시작 지지 인덱스
        frozenset([9, 0, 3]):  5,   # 申(9)子(0)辰(3) → 겁살=巳(5)
        frozenset([2, 6, 10]): 11,  # 寅(2)午(6)戌(10)→ 겁살=亥(11)
        frozenset([5, 9, 1]):  2,   # 巳(5)酉(8→실제9)丑(1)→ 겁살=寅(2)
        frozenset([11, 3, 7]): 9,   # 亥(11)卯(3)未(7)→ 겁살=申(9)
    }
    # 지지 인덱스 보정 (酉=8이 아니라 酉=9 — BRANCHES 기준)
    # 子=0,丑=1,寅=2,卯=3,辰=4,巳=5,午=6,未=7,申=8,酉=9,戌=10,亥=11
    groups_start_corrected = {
        frozenset([8, 0, 4]):  5,   # 申(8)子(0)辰(4) → 겁살=巳(5)
        frozenset([2, 6, 10]): 11,  # 寅(2)午(6)戌(10)→ 겁살=亥(11)
        frozenset([5, 9, 1]):  2,   # 巳(5)酉(9)丑(1) → 겁살=寅(2)
        frozenset([11, 3, 7]): 8,   # 亥(11)卯(3)未(7)→ 겁살=申(8)
    }

    result = {}
    for group_set, start_idx in groups_start_corrected.items():
        sal_map = {}
        for offset, sal_name in enumerate(ORDER):
            branch_idx = (start_idx + offset) % 12
            sal_map[BRANCHES[branch_idx]] = sal_name
        # 이 그룹에 속하는 모든 지지를 기준지지로 등록
        for b_idx in group_set:
            result[BRANCHES[b_idx]] = sal_map
    return result

_12SHINSAL_MAP = _build_12shinsal_map()

# 천을귀인: 일간 기준 → 대상지지
_CHUNEUL_MAP = {
    "甲": ["丑","未"], "乙": ["子","申"],
    "丙": ["亥","酉"], "丁": ["亥","酉"],
    "戊": ["丑","未"], "己": ["子","申"],
    "庚": ["丑","未"], "辛": ["寅","午"],
    "壬": ["卯","巳"], "癸": ["卯","巳"],
}

# 문창귀인: 일간 기준 → 대상지지
_MUNCHANG_MAP = {
    "甲":"巳","乙":"午","丙":"申","丁":"酉",
    "戊":"申","己":"酉","庚":"亥","辛":"子",
    "壬":"寅","癸":"卯",
}

# 홍염살: 일간 기준 → 대상지지
_HONGYEOM_MAP = {
    "甲":"午","乙":"申","丙":"寅","丁":"未",
    "戊":"辰","己":"辰","庚":"戌","辛":"戌",
    "壬":"子","癸":"申",
}

# 학당귀인: 일간 기준 → 대상지지
_HAKDANG_MAP = {
    "甲":"亥","乙":"午","丙":"寅","丁":"酉",
    "戊":"申","己":"卯","庚":"巳","辛":"子",
    "壬":"申","癸":"卯",
}

# 양인살: 일간 기준 → 대상지지 (건록 다음 지지 = 겁재 위치)
_YANGIN_MAP = {
    "甲":"卯","乙":"寅","丙":"午","丁":"巳",
    "戊":"午","己":"巳","庚":"酉","辛":"申",
    "壬":"子","癸":"亥",
}

# 백호대살: 해당 일주/월주 간지 목록 (60갑자 중 특정 6개)
_BAEKHO_GANJI = {"甲辰","乙未","丙戌","丁丑","戊辰","壬戌"}

# 괴강살: 해당 일주 간지 목록
_GOEGANG_GANJI = {"庚辰","庚戌","壬辰","壬戌"}

# 원진살: 년지/일지 기준 → 대상지지
_WONJIN_MAP = {
    "子":"未","丑":"午","寅":"酉","卯":"申",
    "辰":"亥","巳":"戌","午":"丑","未":"子",
    "申":"卯","酉":"寅","戌":"巳","亥":"辰",
}

# 귀문관살: 특정 지지 쌍 (어느 한쪽이 있으면 해당)
_GWIMUN_PAIRS = [
    ("子","酉"),("丑","午"),("寅","未"),("卯","申"),
    ("辰","亥"),("巳","戌"),
]

# 삼재: 년지 기준 삼재 해당 지지 3개
# 申子辰생 → 寅卯辰년, 寅午戌생 → 申酉戌년, 巳酉丑생 → 亥子丑년, 亥卯未생 → 巳午未년
_SAMJAE_MAP = {
    "申":["寅","卯","辰"], "子":["寅","卯","辰"], "辰":["寅","卯","辰"],
    "寅":["申","酉","戌"], "午":["申","酉","戌"], "戌":["申","酉","戌"],
    "巳":["亥","子","丑"], "酉":["亥","子","丑"], "丑":["亥","子","丑"],
    "亥":["巳","午","未"], "卯":["巳","午","未"], "未":["巳","午","未"],
}


# ── 절기 날짜 계산 ────────────────────────────────────────────────────────────

def _get_jeolgi_date(year: int, longitude: float, cal_month: int) -> date:
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


# ── 공통 헬퍼 ─────────────────────────────────────────────────────────────────

def _calc_12shinsal(base_branch: str, target_branch: str) -> list:
    """
    base_branch(년지 또는 일지) 기준으로 target_branch의 12신살 판별.
    해당 없으면 빈 리스트 반환.
    """
    sal_map = _12SHINSAL_MAP.get(base_branch, {})
    sal = sal_map.get(target_branch)
    return [sal] if sal else []


def _calc_stem_shinsal(day_stem: str, target_branch: str) -> list:
    """
    일간(day_stem) 기준으로 target_branch의 신살 판별.
    천을귀인, 문창귀인, 홍염살, 학당귀인, 양인살.
    """
    result = []
    if target_branch in _CHUNEUL_MAP.get(day_stem, []):
        result.append("천을귀인")
    if _MUNCHANG_MAP.get(day_stem) == target_branch:
        result.append("문창귀인")
    if _HONGYEOM_MAP.get(day_stem) == target_branch:
        result.append("홍염살")
    if _HAKDANG_MAP.get(day_stem) == target_branch:
        result.append("학당귀인")
    if _YANGIN_MAP.get(day_stem) == target_branch:
        result.append("양인살")
    return result


def _get_shinsal_for_branch(year_branch: str, target_branch: str,
                             day_stem: str = "",
                             day_branch: str = "") -> list:
    """
    대운/세운/월운 단일 지지의 신살 전체 계산.

    계산 기준:
      - 12신살: 년지 기준 + (일지 기준도 체크, 중복 제거)
      - 천을귀인/문창귀인/홍염살/학당귀인/양인살: 일간 기준
      - 원진살: 년지/일지 기준
      - 귀문관살: 년지/일지와의 쌍 체크
      - 삼재: 년지 기준
    """
    result = []
    seen = set()

    def add(sal: str):
        if sal not in seen:
            seen.add(sal)
            result.append(sal)

    # 12신살 — 년지 기준
    for sal in _calc_12shinsal(year_branch, target_branch):
        add(sal)

    # 12신살 — 일지 기준 (일지가 다를 때만 추가 체크)
    if day_branch and day_branch != year_branch:
        for sal in _calc_12shinsal(day_branch, target_branch):
            add(sal)

    # 일간 기준 신살
    if day_stem:
        for sal in _calc_stem_shinsal(day_stem, target_branch):
            add(sal)

    # 원진살 — 년지/일지 기준
    if _WONJIN_MAP.get(year_branch) == target_branch:
        add("원진살")
    if day_branch and day_branch != year_branch:
        if _WONJIN_MAP.get(day_branch) == target_branch:
            add("원진살")

    # 귀문관살 — 년지/일지와 target_branch가 쌍을 이루는지 체크
    for b1, b2 in _GWIMUN_PAIRS:
        if (year_branch == b1 and target_branch == b2) or \
           (year_branch == b2 and target_branch == b1):
            add("귀문관살")
            break
        if day_branch and day_branch != year_branch:
            if (day_branch == b1 and target_branch == b2) or \
               (day_branch == b2 and target_branch == b1):
                add("귀문관살")
                break

    # 삼재 — 년지 기준 (target_branch가 삼재 해당 지지인지)
    samjae_branches = _SAMJAE_MAP.get(year_branch, [])
    if target_branch in samjae_branches:
        add("삼재")

    return result



def _build_pillar_block(stem: str, branch: str,
                        day_stem: str, year_branch: str,
                        day_branch: str = "") -> dict:
    """
    천간+지지 하나의 완전한 분석 블록.
    대운 / 세운 / 월운에서 공통 사용.

    신살 계산:
      - 12신살: 년지(year_branch) + 일지(day_branch) 이중 기준
      - 일간 기반 신살: day_stem 기준

    반환 구조:
    {
      "간지": {"천간": "癸", "지지": "巳"},
      "천간": {"문자": "癸", "오행": "수", "십성": {"값": "정재", "기준": "일간"}},
      "지지": {
          "문자": "巳", "오행": "화",
          "십성": {"값": "편인", "기준": "일간"},
          "12운성": "건록",
          "신살": ["역마살", "천을귀인"]
      }
    }
    """
    return {
        "간지": {"천간": stem, "지지": branch},
        "천간": {
            "문자": stem,
            "오행": STEM_ELEMENT[stem],
            "십성": {"값": get_sipsung(day_stem, stem), "기준": "일간"},
        },
        "지지": {
            "문자": branch,
            "오행": BRANCH_ELEMENT[branch],
            "십성": {
                "값":   get_sipsung(day_stem, BRANCH_HIDDEN_STEMS[branch][-1]),
                "기준": "일간",
            },
            "12운성": get_twelve_state(day_stem, branch),
            "신살":   _get_shinsal_for_branch(year_branch, branch, day_stem, day_branch),
        },
    }


# ── 사주 계산 함수들 ──────────────────────────────────────────────────────────

def get_year_pillar(year: int) -> tuple:
    idx = (year - 4) % 60
    return STEMS[idx % 10], BRANCHES[idx % 12]


def get_month_pillar(year: int, month: int, day: int = 1) -> tuple:
    target   = date(year, month, day)
    lichun   = _get_jeolgi_date(year, 315, 2)
    adj_year = year if target >= lichun else year - 1

    month_idx = 11
    for lon, _, cal_m, saju_m in _JEOLGI:
        term_year = adj_year + 1 if cal_m == 1 else adj_year
        if target >= _get_jeolgi_date(term_year, lon, cal_m):
            month_idx = saju_m

    year_stem_idx    = (adj_year - 4) % 10
    month_stem_start = (year_stem_idx % 5 * 2 + 2) % 10
    return STEMS[(month_stem_start + month_idx) % 10], BRANCHES[(2 + month_idx) % 12]


_DAY_BASE_DATE = date(1992, 10, 24)
_DAY_BASE_IDX  = 9

def get_day_pillar(year: int, month: int, day: int) -> tuple:
    delta     = (date(year, month, day) - _DAY_BASE_DATE).days
    ganji_idx = ((_DAY_BASE_IDX + delta) % 60 + 60) % 60
    return STEMS[ganji_idx % 10], BRANCHES[ganji_idx % 12]


def get_hour_pillar(day_stem: str, hour: int, minute: int = 0) -> tuple:
    # 1. 전체 분 계산
    total_min = hour * 60 + minute

    # 2. 한국 경도 보정 (자시 시작 = 23:30 기준)
    # 23:30 ~ 01:29 → 자시(子時, index 0)
    # 01:30 ~ 03:29 → 축시(丑時, index 1)  ...
    # 21:30 ~ 23:29 → 해시(亥時, index 11)
    offset     = (total_min - 23 * 60 - 30 + 1440) % 1440
    branch_idx = offset // 120

    # 3. 기존의 시두법 공식 유지
    day_stem_idx = STEMS.index(day_stem)
    stem_idx     = ((day_stem_idx % 5 * 2) + branch_idx) % 10
    return STEMS[stem_idx], BRANCHES[branch_idx]


def get_sipsung(day_stem: str, other_stem: str) -> str:
    de, oe  = STEM_ELEMENT[day_stem], STEM_ELEMENT[other_stem]
    same_yy = STEM_YIN_YANG[day_stem] == STEM_YIN_YANG[other_stem]
    if de == oe:                          return "비견" if same_yy else "겁재"
    elif _GENERATE[de] == oe:             return "식신" if same_yy else "상관"
    elif _OVERCOME[de] == oe:             return "편재" if same_yy else "정재"
    elif _OVERCOME_BY[de] == oe:          return "편관" if same_yy else "정관"
    elif _GENERATED_BY[de] == oe:         return "편인" if same_yy else "정인"
    return "미상"


def get_twelve_state(stem: str, branch: str) -> str:
    table = TWELVE_STATE_TABLE.get(stem, [])
    return TWELVE_STATES[table.index(branch)] if branch in table else "미상"


def get_shinsal(year_branch: str, day_stem: str, day_branch: str,
                all_branches: list) -> list:
    """
    원국(사주팔자) 전체 신살 계산.

    포함:
      - 12신살: 년지 기준 + 일지 기준 (all_branches 내 해당 지지 존재 여부)
      - 천을귀인, 문창귀인, 홍염살, 학당귀인, 양인살: 일간 기준
      - 원진살: 년지/일지 기준
      - 귀문관살: 원국 지지 쌍 체크
      - 백호대살: 일주/월주 간지 체크
      - 괴강살: 일주 간지 체크
      - 삼재: 년지 기준
      - 공망: 일주 기준

    all_branches: 원국 4지지 리스트 [년지, 월지, 일지, 시지]
    """
    seen = set()
    result = []

    def add(sal: str):
        if sal not in seen:
            seen.add(sal)
            result.append(sal)

    # ── 12신살 (년지 기준) ──────────────────────────────────────────────────
    y_sal_map = _12SHINSAL_MAP.get(year_branch, {})
    for b in all_branches:
        sal = y_sal_map.get(b)
        if sal:
            add(sal)

    # ── 12신살 (일지 기준 — 년지와 다를 때만) ────────────────────────────
    if day_branch != year_branch:
        d_sal_map = _12SHINSAL_MAP.get(day_branch, {})
        for b in all_branches:
            sal = d_sal_map.get(b)
            if sal:
                add(sal)

    # ── 일간 기준 신살 (양인살 포함) ─────────────────────────────────────
    for b in all_branches:
        for sal in _calc_stem_shinsal(day_stem, b):
            add(sal)

    # ── 원진살 (년지/일지 기준) ───────────────────────────────────────────
    wonjin_target_y = _WONJIN_MAP.get(year_branch)
    wonjin_target_d = _WONJIN_MAP.get(day_branch) if day_branch != year_branch else None
    for b in all_branches:
        if b == wonjin_target_y or b == wonjin_target_d:
            add("원진살")
            break

    # ── 귀문관살 (원국 지지들 간 쌍 체크) ────────────────────────────────
    branch_set = set(all_branches)
    for b1, b2 in _GWIMUN_PAIRS:
        if b1 in branch_set and b2 in branch_set:
            add("귀문관살")
            break

    # ── 백호대살 (일주/월주 간지 체크) ───────────────────────────────────
    # all_stems는 여기서 없으므로 day_stem+day_branch(일주) 체크
    # 월주는 caller에서 넘겨주지 않으므로 일주만 체크
    day_ganji = day_stem + day_branch
    if day_ganji in _BAEKHO_GANJI:
        add("백호대살")

    # ── 괴강살 (일주 간지 체크) ──────────────────────────────────────────
    if day_ganji in _GOEGANG_GANJI:
        add("괴강살")

    # ── 삼재 (년지 기준) ─────────────────────────────────────────────────
    samjae_branches = _SAMJAE_MAP.get(year_branch, [])
    for b in all_branches:
        if b in samjae_branches:
            add("삼재")
            break

    # ── 공망 (空亡) ────────────────────────────────────────────────────────
    # 일주 육십갑자 순번에서 빠진 마지막 두 지지
    ds_idx = STEMS.index(day_stem)
    db_idx = BRANCHES.index(day_branch)
    # 육십갑자 블록(10간 * 12지) 중 현재 블록의 시작 간지 인덱스
    cycle_pos   = (ds_idx * 12 + db_idx) % 60   # 0~59
    block_start = (cycle_pos // 10) * 10         # 블록 시작(0,10,20,30,40,50)
    # 해당 블록에서 사용된 간지 수는 10개, 지지 시작 인덱스
    ji_start    = (db_idx - ds_idx % 12 + 60) % 12
    # 공망 지지 인덱스 (블록 내 마지막 두 지지)
    gm_idxs = [(ji_start + 10) % 12, (ji_start + 11) % 12]
    for b in all_branches:
        if BRANCHES.index(b) in gm_idxs:
            add("공망")
            break

    return result


# ── 세운 / 월운 ───────────────────────────────────────────────────────────────

def get_seun(target_year: int, day_stem: str, year_branch: str,
             day_branch: str = "") -> dict:
    """
    특정 연도의 세운(年運).
    day_branch: 원국 일지 (신살 이중 기준용)
    """
    stem, branch = get_year_pillar(target_year)
    return {
        "연도": target_year,
        **_build_pillar_block(stem, branch, day_stem, year_branch, day_branch),
    }


def get_wolun(target_year: int, target_month: int,
              day_stem: str, year_branch: str,
              day_branch: str = "") -> dict:
    """
    특정 연도·월의 월운(月運). 오호둔법(五虎遁法) 사용.
    day_branch: 원국 일지 (신살 이중 기준용)
    """
    ref_year = target_year - 1 if target_month == 1 else target_year
    y_stem, _ = get_year_pillar(ref_year)
    y_stem_idx       = STEMS.index(y_stem)
    month_stem_start = (y_stem_idx % 5 * 2 + 2) % 10

    month_to_idx = {2:0, 3:1, 4:2, 5:3, 6:4, 7:5,
                    8:6, 9:7, 10:8, 11:9, 12:10, 1:11}
    month_idx = month_to_idx[target_month]
    stem      = STEMS[(month_stem_start + month_idx) % 10]
    branch    = BRANCHES[(2 + month_idx) % 12]

    return {
        "연도":  target_year,
        "월":    target_month,
        **_build_pillar_block(stem, branch, day_stem, year_branch, day_branch),
    }


# ── 메인 계산 ─────────────────────────────────────────────────────────────────

def calculate_saju(name: str,
                   birth_year: int, birth_month: int, birth_day: int,
                   birth_hour: int,
                   gender: str = "남",
                   birth_minute: int = 0) -> dict:
    """
    전체 사주 계산.
    세운/월운은 saju_data에 저장하지 않음 — main.py에서 get_seun()/get_wolun()
    결과를 별도 키로 붙여 넣는다.
    """
    # 1. 음력
    cal = KoreanLunarCalendar()
    cal.setSolarDate(birth_year, birth_month, birth_day)
    lunar_month, lunar_day, is_leap = cal.lunarMonth, cal.lunarDay, cal.isIntercalation

    # 2. 8글자
    y_stem, y_branch = get_year_pillar(birth_year)
    m_stem, m_branch = get_month_pillar(birth_year, birth_month, birth_day)
    d_stem, d_branch = get_day_pillar(birth_year, birth_month, birth_day)
    h_stem, h_branch = get_hour_pillar(d_stem, birth_hour, birth_minute)
    all_stems    = [y_stem, m_stem, d_stem, h_stem]
    all_branches = [y_branch, m_branch, d_branch, h_branch]

    # 3. 오행 분포
    element_count = {"목": 0, "화": 0, "토": 0, "금": 0, "수": 0}
    for s in all_stems:    element_count[STEM_ELEMENT[s]]    += 1
    for b in all_branches: element_count[BRANCH_ELEMENT[b]]  += 1

    # 4. 십성
    sipsung = {
        "연간": get_sipsung(d_stem, y_stem),
        "연지": get_sipsung(d_stem, BRANCH_HIDDEN_STEMS[y_branch][-1]),
        "월간": get_sipsung(d_stem, m_stem),
        "월지": get_sipsung(d_stem, BRANCH_HIDDEN_STEMS[m_branch][-1]),
        "일지": get_sipsung(d_stem, BRANCH_HIDDEN_STEMS[d_branch][-1]),
        "시간": get_sipsung(d_stem, h_stem),
        "시지": get_sipsung(d_stem, BRANCH_HIDDEN_STEMS[h_branch][-1]),
    }

    # 5. 12운성
    twelve_states = {
        "연지": get_twelve_state(d_stem, y_branch),
        "월지": get_twelve_state(d_stem, m_branch),
        "일지": get_twelve_state(d_stem, d_branch),
        "시지": get_twelve_state(d_stem, h_branch),
    }

    # 6. 신살
    shinsal = get_shinsal(y_branch, d_stem, d_branch, all_branches)

    # 7. 신강/신약
    day_elem    = STEM_ELEMENT[d_stem]
    support_cnt = sum(
        (1 if STEM_ELEMENT[s] == day_elem else 0) +
        (1 if _GENERATED_BY.get(day_elem) == STEM_ELEMENT[s] else 0)
        for s in all_stems
    ) + sum(
        (1 if BRANCH_ELEMENT[b] == day_elem else 0) +
        (1 if _GENERATED_BY.get(day_elem) == BRANCH_ELEMENT[b] else 0)
        for b in all_branches
    ) - 1
    strength = "신강(身強)" if support_cnt >= 4 else ("중화(中和)" if support_cnt >= 2 else "신약(身弱)")

    # 8. 대운
    y_yy    = STEM_YIN_YANG[y_stem]
    forward = (gender == "남" and y_yy == "양") or (gender == "여" and y_yy == "음")

    birth_date = date(birth_year, birth_month, birth_day)
    gap_days   = None
    search_years = [birth_year, birth_year + (1 if forward else -1)]
    for sy in search_years:
        for lon, _, cal_m, _ in _JEOLGI:
            ty = sy + 1 if cal_m == 1 else sy
            try:
                td = _get_jeolgi_date(ty, lon, cal_m)
            except Exception:
                continue
            cond = td > birth_date if forward else td < birth_date
            if cond:
                diff = abs((td - birth_date).days)
                if gap_days is None or diff < gap_days:
                    gap_days = diff
        if gap_days is not None:
            break

    q, r      = divmod(gap_days or 0, 3)
    daewun_su = max(q + (1 if r >= 2 else 0), 1)

    m_si = STEMS.index(m_stem)
    m_bi = BRANCHES.index(m_branch)
    daewun_list = []
    for i in range(1, 11):
        s_idx = (m_si + i if forward else m_si - i + 100) % 10
        b_idx = (m_bi + i if forward else m_bi - i + 120) % 12
        block = _build_pillar_block(STEMS[s_idx], BRANCHES[b_idx],
                                    d_stem, y_branch, d_branch)
        daewun_list.append({
            "순서":    i,
            "시작나이": daewun_su + (i - 1) * 10,
            **block,
        })

    # 9. 결과
    hour_str = f"{birth_hour}시" + (f" {birth_minute}분" if birth_minute else "")
    return {
        "기본정보": {
            "이름":     name,
            "생년월일": f"{birth_year}년 {birth_month}월 {birth_day}일 {hour_str}",
            "성별":     gender,
            "음력":     f"{birth_year}년 {lunar_month}월 {lunar_day}일"
                        + ("(윤달)" if is_leap else ""),
        },
        "사주원국": {
            "연주": {"천간": y_stem, "지지": y_branch, "간지": y_stem + y_branch},
            "월주": {"천간": m_stem, "지지": m_branch, "간지": m_stem + m_branch},
            "일주": {"천간": d_stem, "지지": d_branch, "간지": d_stem + d_branch},
            "시주": {"천간": h_stem, "지지": h_branch, "간지": h_stem + h_branch},
        },
        "일간정보": {
            "일간":     d_stem,
            "오행":     STEM_ELEMENT[d_stem],
            "음양":     STEM_YIN_YANG[d_stem],
            "신강신약":  strength,
        },
        "십성":    sipsung,
        "오행분포": element_count,
        "십이운성": twelve_states,
        "신살":    shinsal if shinsal else ["없음"],
        "대운수":  daewun_su,
        "대운":    daewun_list,
        # 세운/월운은 main.py에서 추가:
        # "세운": [get_seun(...), ...]
        # "월운": [get_wolun(...), ...]
    }


# ── 단독 실행 테스트 ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    import json

    data = calculate_saju("테스트", 1995, 12, 13, 23, "남", 0)
    print("=== 원국 ===")
    for p in ["연주","월주","일주","시주"]:
        print(f"  {p}: {data['사주원국'][p]['간지']}")
    print(f"\n대운수: {data['대운수']}")

    print("\n=== 대운[0] 구조 ===")
    print(json.dumps(data["대운"][0], ensure_ascii=False, indent=2))

    d_stem   = data["일간정보"]["일간"]
    y_branch = data["사주원국"]["연주"]["지지"]

    print("\n=== 세운 2026 ===")
    print(json.dumps(get_seun(2026, d_stem, y_branch), ensure_ascii=False, indent=2))

    print("\n=== 월운 2026년 1~3월 ===")
    for m in [1, 2, 3]:
        print(json.dumps(get_wolun(2026, m, d_stem, y_branch), ensure_ascii=False, indent=2))

    print("\n[연주 검증]")
    for y, ex in [(1984,"甲子"),(1990,"庚午"),(2024,"甲辰"),(2026,"丙午")]:
        s, b = get_year_pillar(y)
        print(f"  {y}: {s}{b}  {'✓' if s+b==ex else '✗'} (기대 {ex})")