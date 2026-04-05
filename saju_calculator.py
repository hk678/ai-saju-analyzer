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

_YEOKMA_MAP = {
    "寅":"申","午":"申","戌":"申","申":"寅","子":"寅","辰":"寅",
    "亥":"巳","卯":"巳","未":"巳","巳":"亥","酉":"亥","丑":"亥",
}
_DOHWA_MAP = {
    "寅":"卯","午":"卯","戌":"卯","申":"酉","子":"酉","辰":"酉",
    "亥":"子","卯":"子","未":"子","巳":"午","酉":"午","丑":"午",
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

def _get_shinsal_for_branch(year_branch: str, target_branch: str) -> list:
    """특정 지지의 신살 (원국 연지 기준). 대운/세운/월운 공통."""
    result = []
    if _YEOKMA_MAP.get(year_branch) == target_branch:
        result.append("역마살")
    if _DOHWA_MAP.get(year_branch) == target_branch:
        result.append("도화살")
    return result


def _build_pillar_block(stem: str, branch: str,
                        day_stem: str, year_branch: str) -> dict:
    """
    천간+지지 하나의 완전한 분석 블록.
    대운 / 세운 / 월운에서 공통 사용.

    반환 구조:
    {
      "간지": {"천간": "癸", "지지": "巳"},
      "천간": {
          "문자": "癸", "오행": "수",
          "십성": {"값": "정재", "기준": "일간"}
      },
      "지지": {
          "문자": "巳", "오행": "화",
          "십성": {"값": "편인", "기준": "일간"},
          "12운성": "건록",
          "신살": ["역마살"]
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
            "신살":   _get_shinsal_for_branch(year_branch, branch),
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
    if hour == 23:
        branch_idx = 11
    else:
        branch_idx = (hour * 60 + minute + 60) // 120 % 12
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
    result = []
    if _YEOKMA_MAP.get(year_branch) in all_branches:
        result.append("역마살")
    if _DOHWA_MAP.get(year_branch) in all_branches:
        result.append("도화살")
    hakdang = {"甲":"亥","乙":"午","丙":"寅","丁":"酉","戊":"申",
               "己":"卯","庚":"巳","辛":"子","壬":"申","癸":"卯"}
    if hakdang.get(day_stem) in all_branches:
        result.append("학당귀인")
    chuneul = {"甲":["丑","未"],"乙":["子","申"],"丙":["亥","酉"],"丁":["亥","酉"],
               "戊":["丑","未"],"己":["子","申"],"庚":["丑","未"],"辛":["寅","午"],
               "壬":["卯","巳"],"癸":["卯","巳"]}
    if any(b in all_branches for b in chuneul.get(day_stem, [])):
        result.append("천을귀인")
    # 공망
    ds_idx  = STEMS.index(day_stem)
    db_idx  = BRANCHES.index(day_branch)
    g_idx   = ds_idx % 10 + (db_idx - ds_idx % 12 + 60) % 12
    gm_list = [(( g_idx // 10) * 10 + 10) % 12, ((g_idx // 10) * 10 + 11) % 12]
    if any(BRANCHES.index(b) in gm_list for b in all_branches):
        result.append("공망")
    return list(dict.fromkeys(result))


# ── 세운 / 월운 ───────────────────────────────────────────────────────────────

def get_seun(target_year: int, day_stem: str, year_branch: str) -> dict:
    """
    특정 연도의 세운(年運).

    반환:
    {
      "연도": 2026,
      "간지": {"천간": "丙", "지지": "午"},
      "천간": {"문자": "丙", "오행": "화", "십성": {"값": "...", "기준": "일간"}},
      "지지": {"문자": "午", "오행": "화", "십성": {...}, "12운성": "...", "신살": [...]}
    }
    """
    stem, branch = get_year_pillar(target_year)
    return {
        "연도": target_year,
        **_build_pillar_block(stem, branch, day_stem, year_branch),
    }


def get_wolun(target_year: int, target_month: int,
              day_stem: str, year_branch: str) -> dict:
    """
    특정 연도·월의 월운(月運). 오호둔법(五虎遁法) 사용.

    반환:
    {
      "연도": 2026,
      "월": 3,
      "간지": {"천간": "壬", "지지": "寅"},
      "천간": {"문자": "壬", "오행": "수", "십성": {...}},
      "지지": {"문자": "寅", "오행": "목", "십성": {...}, "12운성": "...", "신살": [...]}
    }
    """
    y_stem, _        = get_year_pillar(target_year)
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
        **_build_pillar_block(stem, branch, day_stem, year_branch),
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
        block = _build_pillar_block(STEMS[s_idx], BRANCHES[b_idx], d_stem, y_branch)
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