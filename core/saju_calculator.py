"""
사주 계산 조립 모듈 (Saju Calculator).

담당 기능:
  - 십성(十星) 계산
  - 12운성(十二運星) 계산
  - 신강·신약 판별
  - 대운(大運) 산출
  - 세운(歲運) / 월운(月運) 산출
  - 전체 사주 조립 (calculate_saju)
  - 수동 간지 입력 재계산 (recalculate_from_pillars)

하위 모듈 의존:
  core.constants      → 상수
  core.shinsal        → 신살 계산
  core.calendar_engine → 역법·주(柱) 산출
"""

from datetime import date

from core.constants import (
    STEMS, BRANCHES,
    STEM_ELEMENT, BRANCH_ELEMENT, STEM_YIN_YANG,
    BRANCH_HIDDEN_STEMS,
    GENERATE, OVERCOME, GENERATED_BY, OVERCOME_BY,
    TWELVE_STATES, TWELVE_STATE_TABLE,
    JEOLGI,
)
from core.shinsal import get_shinsal, get_shinsal_for_branch
from core.calendar_engine import (
    get_year_pillar, get_month_pillar, get_day_pillar, get_hour_pillar,
    get_jeolgi_date, solar_to_lunar, resolve_pillars,
)


# ── 십성 (十星) ───────────────────────────────────────────────────────────────

def get_sipsung(day_stem: str, other_stem: str) -> str:
    """
    일간(day_stem) 대비 other_stem의 십성 반환.

    Args:
        day_stem:   일간 천간 문자
        other_stem: 비교 대상 천간 문자 (지지일 경우 지장간 대표 글자 사용)

    Returns:
        십성 이름 (비견·겁재·식신·상관·편재·정재·편관·정관·편인·정인)
    """
    de      = STEM_ELEMENT[day_stem]
    oe      = STEM_ELEMENT[other_stem]
    same_yy = STEM_YIN_YANG[day_stem] == STEM_YIN_YANG[other_stem]

    if de == oe:                        return "비견" if same_yy else "겁재"
    elif GENERATE.get(de) == oe:        return "식신" if same_yy else "상관"
    elif OVERCOME.get(de) == oe:        return "편재" if same_yy else "정재"
    elif OVERCOME_BY.get(de) == oe:     return "편관" if same_yy else "정관"
    elif GENERATED_BY.get(de) == oe:    return "편인" if same_yy else "정인"
    return "미상"


# ── 12운성 (十二運星) ─────────────────────────────────────────────────────────

def get_twelve_state(stem: str, branch: str) -> str:
    """
    일간(stem) 기준으로 지지(branch)의 12운성 반환.

    Returns:
        12운성 이름 (해당 없으면 "미상")
    """
    table = TWELVE_STATE_TABLE.get(stem, [])
    return TWELVE_STATES[table.index(branch)] if branch in table else "미상"


# ── 내부 조립 헬퍼 ────────────────────────────────────────────────────────────

def _build_pillar_block(
    stem: str, branch: str,
    day_stem: str, year_branch: str,
    day_branch: str = "",
) -> dict:
    """
    천간+지지 하나의 완전한 분석 블록 생성.
    대운·세운·월운에서 공통 사용.

    반환 구조:
        {
          "간지":  {"천간": "辛", "지지": "卯"},
          "천간": {"문자": "辛", "오행": "금", "십성": {"값": "정인", "기준": "일간"}},
          "지지": {
              "문자": "卯", "오행": "목",
              "십성": {"값": "편관", "기준": "일간"},
              "12운성": "절",
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
            "신살":   get_shinsal_for_branch(branch, year_branch, day_stem, day_branch),
        },
    }


def _calc_element_distribution(
    all_stems: list[str], all_branches: list[str]
) -> dict[str, int]:
    """8글자의 오행 분포 집계."""
    element_count = {"목": 0, "화": 0, "토": 0, "금": 0, "수": 0}
    for s in all_stems:    element_count[STEM_ELEMENT[s]]   += 1
    for b in all_branches: element_count[BRANCH_ELEMENT[b]] += 1
    return element_count


def _calc_sipsung_map(d_stem: str, all_stems: list[str], all_branches: list[str]) -> dict[str, str]:
    """원국 8글자의 십성 매핑 딕셔너리."""
    y_stem, m_stem, _, h_stem           = all_stems
    y_branch, m_branch, d_branch, h_branch = all_branches
    return {
        "연간": get_sipsung(d_stem, y_stem),
        "연지": get_sipsung(d_stem, BRANCH_HIDDEN_STEMS[y_branch][-1]),
        "월간": get_sipsung(d_stem, m_stem),
        "월지": get_sipsung(d_stem, BRANCH_HIDDEN_STEMS[m_branch][-1]),
        "일지": get_sipsung(d_stem, BRANCH_HIDDEN_STEMS[d_branch][-1]),
        "시간": get_sipsung(d_stem, h_stem),
        "시지": get_sipsung(d_stem, BRANCH_HIDDEN_STEMS[h_branch][-1]),
    }


def _calc_twelve_states(d_stem: str, all_branches: list[str]) -> dict[str, str]:
    """원국 4개 지지의 12운성 매핑 딕셔너리."""
    y_branch, m_branch, d_branch, h_branch = all_branches
    return {
        "연지": get_twelve_state(d_stem, y_branch),
        "월지": get_twelve_state(d_stem, m_branch),
        "일지": get_twelve_state(d_stem, d_branch),
        "시지": get_twelve_state(d_stem, h_branch),
    }


def _calc_strength(d_stem: str, all_stems: list[str], all_branches: list[str]) -> str:
    """신강·신약 판별."""
    day_elem    = STEM_ELEMENT[d_stem]
    support_cnt = sum(
        (1 if STEM_ELEMENT[s] == day_elem else 0) +
        (1 if GENERATED_BY.get(day_elem) == STEM_ELEMENT[s] else 0)
        for s in all_stems
    ) + sum(
        (1 if BRANCH_ELEMENT[b] == day_elem else 0) +
        (1 if GENERATED_BY.get(day_elem) == BRANCH_ELEMENT[b] else 0)
        for b in all_branches
    ) - 1  # 일간 자신 제외
    if support_cnt >= 4:
        return "신강(身強)"
    elif support_cnt >= 2:
        return "중화(中和)"
    return "신약(身弱)"


def _calc_daewun_start(
    birth_year: int, birth_month: int, birth_day: int,
    forward: bool,
) -> int:
    """
    절기까지의 일수로 대운수(大運數) 계산.

    forward=True  → 다음 절기까지의 일수
    forward=False → 직전 절기까지의 일수
    """
    birth_date = date(birth_year, birth_month, birth_day)
    gap_days   = None
    search_years = [birth_year, birth_year + (1 if forward else -1)]

    for sy in search_years:
        for lon, _, cal_m, _ in JEOLGI:
            ty = sy + 1 if cal_m == 1 else sy
            try:
                td = get_jeolgi_date(ty, lon, cal_m)
            except Exception:
                continue
            cond = td > birth_date if forward else td < birth_date
            if cond:
                diff = abs((td - birth_date).days)
                if gap_days is None or diff < gap_days:
                    gap_days = diff
        if gap_days is not None:
            break

    q, r = divmod(gap_days or 0, 3)
    return max(q + (1 if r >= 2 else 0), 1)


def _build_daewun_list(
    m_stem: str, m_branch: str,
    d_stem: str, y_branch: str, d_branch: str,
    daewun_su: int,
    forward: bool,
) -> list[dict]:
    """대운 10개 리스트 생성."""
    m_si = STEMS.index(m_stem)
    m_bi = BRANCHES.index(m_branch)
    daewun_list = []
    for i in range(1, 11):
        s_idx = (m_si + i if forward else m_si - i + 100) % 10
        b_idx = (m_bi + i if forward else m_bi - i + 120) % 12
        block = _build_pillar_block(
            STEMS[s_idx], BRANCHES[b_idx], d_stem, y_branch, d_branch
        )
        daewun_list.append({
            "순서":     i,
            "시작나이": daewun_su + (i - 1) * 10,
            **block,
        })
    return daewun_list


# ── 세운 / 월운 ───────────────────────────────────────────────────────────────

def get_seun(
    target_year: int,
    day_stem: str,
    year_branch: str,
    day_branch: str = "",
) -> dict:
    """
    특정 연도의 세운(年運) 반환.

    Args:
        target_year: 세운 연도
        day_stem:    원국 일간
        year_branch: 원국 연지 (신살 기준)
        day_branch:  원국 일지 (신살 이중 기준용)

    Returns:
        {"연도": int, ...pillar_block}
    """
    stem, branch = get_year_pillar(target_year)
    return {
        "연도": target_year,
        **_build_pillar_block(stem, branch, day_stem, year_branch, day_branch),
    }


def get_wolun(
    target_year: int,
    target_month: int,
    day_stem: str,
    year_branch: str,
    day_branch: str = "",
) -> dict:
    """
    특정 연도·월의 월운(月運) 반환 (오호둔법).

    Returns:
        {"연도": int, "월": int, ...pillar_block}
    """
    ref_year = target_year - 1 if target_month == 1 else target_year
    y_stem, _ = get_year_pillar(ref_year)

    y_stem_idx       = STEMS.index(y_stem)
    month_stem_start = (y_stem_idx % 5 * 2 + 2) % 10

    month_to_idx = {
        2: 0, 3: 1, 4: 2, 5: 3, 6: 4, 7: 5,
        8: 6, 9: 7, 10: 8, 11: 9, 12: 10, 1: 11,
    }
    month_idx = month_to_idx[target_month]
    stem      = STEMS[(month_stem_start + month_idx) % 10]
    branch    = BRANCHES[(2 + month_idx) % 12]

    return {
        "연도": target_year,
        "월":   target_month,
        **_build_pillar_block(stem, branch, day_stem, year_branch, day_branch),
    }


# ── 메인 계산 ─────────────────────────────────────────────────────────────────

def calculate_saju(
    name:         str,
    birth_year:   int,
    birth_month:  int,
    birth_day:    int,
    birth_hour:   int,
    gender:       str = "남",
    birth_minute: int = 0,
    yajasi:       bool = False,
) -> dict:
    """
    전체 사주 계산 후 딕셔너리 반환.

    세운·월운은 이 함수에서 계산하지 않는다.
    app/pipeline.py에서 get_seun()/get_wolun()을 호출하여 별도 키로 추가한다.

    Returns:
        {
          "기본정보": {...},
          "사주원국": {연주·월주·일주·시주},
          "일간정보": {...},
          "십성":    {...},
          "오행분포": {...},
          "십이운성": {...},
          "신살":    {...},
          "대운수":  int,
          "대운":    [...],
        }
    """
    # 1. 8글자 (야자시 포함)
    y_stem, y_branch, m_stem, m_branch, d_stem, d_branch, h_stem, h_branch = \
        resolve_pillars(birth_year, birth_month, birth_day, birth_hour, birth_minute, yajasi)

    all_stems    = [y_stem, m_stem, d_stem, h_stem]
    all_branches = [y_branch, m_branch, d_branch, h_branch]

    # 2. 음력
    lunar_month, lunar_day, is_leap = solar_to_lunar(birth_year, birth_month, birth_day)

    # 3. 오행 분포
    element_count = _calc_element_distribution(all_stems, all_branches)

    # 4. 십성
    sipsung = _calc_sipsung_map(d_stem, all_stems, all_branches)

    # 5. 12운성
    twelve_states = _calc_twelve_states(d_stem, all_branches)

    # 6. 신살
    shinsal = get_shinsal(y_branch, d_stem, d_branch, all_branches, all_stems)

    # 7. 신강·신약
    strength = _calc_strength(d_stem, all_stems, all_branches)

    # 8. 대운
    y_yy    = STEM_YIN_YANG[y_stem]
    forward = (gender == "남" and y_yy == "양") or (gender == "여" and y_yy == "음")

    daewun_su   = _calc_daewun_start(birth_year, birth_month, birth_day, forward)
    daewun_list = _build_daewun_list(
        m_stem, m_branch, d_stem, y_branch, d_branch, daewun_su, forward
    )

    # 9. 기본정보 문자열
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
        "신살":    shinsal,
        "대운수":  daewun_su,
        "대운":    daewun_list,
    }


# ── 수동 간지 입력 재계산 ─────────────────────────────────────────────────────

def recalculate_from_pillars(
    existing_data: dict,
    y_stem: str, y_branch: str,
    m_stem: str, m_branch: str,
    d_stem: str, d_branch: str,
    h_stem: str, h_branch: str,
) -> dict:
    """
    8글자(천간·지지)를 직접 받아 모든 파생 데이터를 재계산.

    기본정보(이름·생년월일·성별·음력)와 대운수는 existing_data에서 보존.
    대운 간지는 월주 기준으로 재계산하며 시작나이는 기존 값을 유지한다.
    """
    all_stems    = [y_stem, m_stem, d_stem, h_stem]
    all_branches = [y_branch, m_branch, d_branch, h_branch]

    element_count = _calc_element_distribution(all_stems, all_branches)
    sipsung       = _calc_sipsung_map(d_stem, all_stems, all_branches)
    twelve_states = _calc_twelve_states(d_stem, all_branches)
    shinsal       = get_shinsal(y_branch, d_stem, d_branch, all_branches, all_stems)
    strength      = _calc_strength(d_stem, all_stems, all_branches)

    gender    = existing_data["기본정보"]["성별"]
    y_yy      = STEM_YIN_YANG[y_stem]
    forward   = (gender == "남" and y_yy == "양") or (gender == "여" and y_yy == "음")
    daewun_su = existing_data["대운수"]  # 생년월일 기반이므로 보존

    daewun_list = _build_daewun_list(
        m_stem, m_branch, d_stem, y_branch, d_branch, daewun_su, forward
    )

    return {
        "기본정보": existing_data["기본정보"],
        "사주원국": {
            "연주": {"천간": y_stem,  "지지": y_branch,  "간지": y_stem  + y_branch},
            "월주": {"천간": m_stem,  "지지": m_branch,  "간지": m_stem  + m_branch},
            "일주": {"천간": d_stem,  "지지": d_branch,  "간지": d_stem  + d_branch},
            "시주": {"천간": h_stem,  "지지": h_branch,  "간지": h_stem  + h_branch},
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
        "신살":    shinsal,
        "대운수":  daewun_su,
        "대운":    daewun_list,
    }
