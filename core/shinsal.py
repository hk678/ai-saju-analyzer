"""
신살(神殺) 테이블 및 판별 함수.

원국 신살(get_shinsal)과 대운·세운·월운용 단일 지지 신살(_get_shinsal_for_branch)을
모두 이 모듈에서 제공한다.
"""

from core.constants import (
    STEMS, BRANCHES,
    BRANCH_HIDDEN_STEMS,
)

# ── 12신살 매핑 테이블 ────────────────────────────────────────────────────────
#
# 삼합 4그룹 기준으로 12신살을 계산한다.
# 순서 (겁살부터): 겁살·재살·천살·지살·년살·월살·망신살·장성살·반안살·역마살·육해살·화개살
#
# 그룹별 겁살 시작 지지 인덱스 (BRANCHES 기준: 子=0 … 亥=11):
#   申(8)子(0)辰(4) 수국 → 겁살=巳(5)
#   寅(2)午(6)戌(10) 화국 → 겁살=亥(11)
#   巳(5)酉(9)丑(1) 금국 → 겁살=寅(2)
#   亥(11)卯(3)未(7) 목국 → 겁살=申(8)

_12SHINSAL_ORDER = [
    "겁살", "재살", "천살", "지살", "년살", "월살",
    "망신살", "장성살", "반안살", "역마살", "육해살", "화개살",
]

_12SHINSAL_GROUP_START: dict[frozenset, int] = {
    frozenset([8, 0, 4]):  5,   # 申子辰 수국 → 겁살=巳
    frozenset([2, 6, 10]): 11,  # 寅午戌 화국 → 겁살=亥
    frozenset([5, 9, 1]):  2,   # 巳酉丑 금국 → 겁살=寅
    frozenset([11, 3, 7]): 8,   # 亥卯未 목국 → 겁살=申
}


def _build_12shinsal_map() -> dict[str, dict[str, str]]:
    """
    12신살 전체 매핑 테이블 생성.
    반환: { 기준지지: { 대상지지: 신살이름 } }
    """
    result: dict[str, dict[str, str]] = {}
    for group_set, start_idx in _12SHINSAL_GROUP_START.items():
        sal_map: dict[str, str] = {}
        for offset, sal_name in enumerate(_12SHINSAL_ORDER):
            sal_map[BRANCHES[(start_idx + offset) % 12]] = sal_name
        for b_idx in group_set:
            result[BRANCHES[b_idx]] = sal_map
    return result


_12SHINSAL_MAP: dict[str, dict[str, str]] = _build_12shinsal_map()

# ── 일간 기준 신살 테이블 ─────────────────────────────────────────────────────

# 천을귀인: 일간 → 해당 지지 목록
_CHUNEUL_MAP: dict[str, list[str]] = {
    "甲": ["丑", "未"], "乙": ["子", "申"],
    "丙": ["亥", "酉"], "丁": ["亥", "酉"],
    "戊": ["丑", "未"], "己": ["子", "申"],
    "庚": ["丑", "未"], "辛": ["寅", "午"],
    "壬": ["卯", "巳"], "癸": ["卯", "巳"],
}

# 문창귀인: 일간 → 해당 지지
_MUNCHANG_MAP: dict[str, str] = {
    "甲": "巳", "乙": "午", "丙": "申", "丁": "酉",
    "戊": "申", "己": "酉", "庚": "亥", "辛": "子",
    "壬": "寅", "癸": "卯",
}

# 홍염살: 일간 → 해당 지지
_HONGYEOM_MAP: dict[str, str] = {
    "甲": "午", "乙": "申", "丙": "寅", "丁": "未",
    "戊": "辰", "己": "辰", "庚": "戌", "辛": "戌",
    "壬": "子", "癸": "申",
}

# 학당귀인: 일간 → 해당 지지
_HAKDANG_MAP: dict[str, str] = {
    "甲": "亥", "乙": "午", "丙": "寅", "丁": "酉",
    "戊": "申", "己": "卯", "庚": "巳", "辛": "子",
    "壬": "申", "癸": "卯",
}

# 양인살: 일간 → 해당 지지 (건록 다음 지지 = 겁재 위치)
_YANGIN_MAP: dict[str, str] = {
    "甲": "卯", "乙": "寅", "丙": "午", "丁": "巳",
    "戊": "午", "己": "巳", "庚": "酉", "辛": "申",
    "壬": "子", "癸": "亥",
}

# ── 간지 기준 특수 신살 ───────────────────────────────────────────────────────

# 백호대살: 해당 일주/월주 간지 목록
_BAEKHO_GANJI: set[str] = {"甲辰", "乙未", "丙戌", "丁丑", "戊辰", "壬戌"}

# 괴강살: 해당 일주 간지 목록
_GOEGANG_GANJI: set[str] = {"庚辰", "庚戌", "壬辰", "壬戌"}

# 원진살: 년지/일지 기준 → 대상지지
_WONJIN_MAP: dict[str, str] = {
    "子": "未", "丑": "午", "寅": "酉", "卯": "申",
    "辰": "亥", "巳": "戌", "午": "丑", "未": "子",
    "申": "卯", "酉": "寅", "戌": "巳", "亥": "辰",
}

# 귀문관살: 이 지지 쌍 중 하나가 있을 때 귀문관살
_GWIMUN_PAIRS: list[tuple[str, str]] = [
    ("子", "酉"), ("丑", "午"), ("寅", "未"), ("卯", "申"),
    ("辰", "亥"), ("巳", "戌"),
]

# 삼재: 년지 기준 → 삼재 해당 지지 3개
_SAMJAE_MAP: dict[str, list[str]] = {
    "申": ["寅", "卯", "辰"], "子": ["寅", "卯", "辰"], "辰": ["寅", "卯", "辰"],
    "寅": ["申", "酉", "戌"], "午": ["申", "酉", "戌"], "戌": ["申", "酉", "戌"],
    "巳": ["亥", "子", "丑"], "酉": ["亥", "子", "丑"], "丑": ["亥", "子", "丑"],
    "亥": ["巳", "午", "未"], "卯": ["巳", "午", "未"], "未": ["巳", "午", "未"],
}


# ── 내부 헬퍼 ─────────────────────────────────────────────────────────────────

def _calc_stem_shinsal(day_stem: str, target_branch: str) -> list[str]:
    """일간 기준으로 target_branch에 해당하는 신살 목록 반환."""
    result: list[str] = []
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


# ── 공개 API ──────────────────────────────────────────────────────────────────

def get_shinsal_for_branch(
    target_branch: str,
    year_branch: str,
    day_stem: str = "",
    day_branch: str = "",
) -> list[str]:
    """
    대운·세운·월운 단일 지지의 신살 전체 계산.

    계산 기준:
      - 12신살: 년지 기준 + 일지 기준 (중복 제거)
      - 천을귀인·문창귀인·홍염살·학당귀인·양인살: 일간 기준
      - 원진살: 년지/일지 기준
      - 귀문관살: 년지/일지와의 쌍 체크
      - 삼재: 년지 기준
    """
    result: list[str] = []
    seen: set[str] = set()

    def add(sal: str) -> None:
        if sal not in seen:
            seen.add(sal)
            result.append(sal)

    # 12신살 — 년지 기준
    for sal in (_12SHINSAL_MAP.get(year_branch, {}).get(target_branch, None),):
        if sal:
            add(sal)

    # 12신살 — 일지 기준 (다를 때만)
    if day_branch and day_branch != year_branch:
        sal = _12SHINSAL_MAP.get(day_branch, {}).get(target_branch)
        if sal:
            add(sal)

    # 일간 기준 신살
    if day_stem:
        for sal in _calc_stem_shinsal(day_stem, target_branch):
            add(sal)

    # 원진살
    if _WONJIN_MAP.get(year_branch) == target_branch:
        add("원진살")
    if day_branch and day_branch != year_branch:
        if _WONJIN_MAP.get(day_branch) == target_branch:
            add("원진살")

    # 귀문관살
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

    # 삼재
    if target_branch in _SAMJAE_MAP.get(year_branch, []):
        add("삼재")

    return result


def get_shinsal(
    year_branch: str,
    day_stem: str,
    day_branch: str,
    all_branches: list[str],
    all_stems: list[str] | None = None,
) -> dict[str, list[str]]:
    """
    원국(사주팔자) 신살 계산. 주(柱)별로 귀속하여 딕셔너리로 반환.

    반환 구조:
        {
          "연주": ["화개살", ...],
          "월주": ["천살", ...],
          "일주": ["화개살", "괴강살", ...],
          "시주": ["재살", ...],
          "원국": [],   # 향후 확장용 (현재 미사용)
        }

    Args:
        year_branch:  원국 연지
        day_stem:     원국 일간
        day_branch:   원국 일지
        all_branches: [연지, 월지, 일지, 시지]
        all_stems:    [연간, 월간, 일간, 시간] — 백호대살(월주) 판별에 필요
    """
    pillar_keys = ["연주", "월주", "일주", "시주"]
    result: dict[str, list[str]] = {k: [] for k in pillar_keys}
    result["원국"] = []

    def add_to(key: str, sal: str) -> None:
        if sal not in result[key]:
            result[key].append(sal)

    # ── 지지별 신살 ───────────────────────────────────────────────────────────
    for key, branch in zip(pillar_keys, all_branches):
        seen_this: set[str] = set()

        def add(sal: str, _key: str = key, _seen: set = seen_this) -> None:
            if sal not in _seen:
                _seen.add(sal)
                result[_key].append(sal)

        # 12신살 — 년지 기준
        sal = _12SHINSAL_MAP.get(year_branch, {}).get(branch)
        if sal:
            add(sal)

        # 12신살 — 일지 기준 (다를 때만)
        if day_branch != year_branch:
            sal = _12SHINSAL_MAP.get(day_branch, {}).get(branch)
            if sal:
                add(sal)

        # 일간 기준 신살
        for sal in _calc_stem_shinsal(day_stem, branch):
            add(sal)

        # 원진살
        if _WONJIN_MAP.get(year_branch) == branch:
            add("원진살")
        if day_branch != year_branch and _WONJIN_MAP.get(day_branch) == branch:
            add("원진살")

        # 귀문관살
        other_branches = set(all_branches) - {branch}
        for b1, b2 in _GWIMUN_PAIRS:
            if (branch == b1 and b2 in other_branches) or \
               (branch == b2 and b1 in other_branches):
                add("귀문관살")
                break

    # ── 백호대살 (일주·월주 간지 체크) ──────────────────────────────────────
    day_ganji = day_stem + day_branch
    if day_ganji in _BAEKHO_GANJI:
        add_to("일주", "백호대살")

    if all_stems and len(all_stems) >= 2:
        month_ganji = all_stems[1] + all_branches[1]
        if month_ganji in _BAEKHO_GANJI:
            add_to("월주", "백호대살")

    # ── 괴강살 (일주 간지 체크) ──────────────────────────────────────────────
    if day_ganji in _GOEGANG_GANJI:
        add_to("일주", "괴강살")

    # ── 삼재 (년지 기준) ─────────────────────────────────────────────────────
    samjae_branches = _SAMJAE_MAP.get(year_branch, [])
    for key, branch in zip(pillar_keys, all_branches):
        if branch in samjae_branches:
            add_to(key, "삼재")

    # ── 공망 (일주 기준) ─────────────────────────────────────────────────────
    ds_idx   = STEMS.index(day_stem)
    db_idx   = BRANCHES.index(day_branch)
    ji_start = (db_idx - ds_idx % 12 + 60) % 12
    gm_idxs  = {(ji_start + 10) % 12, (ji_start + 11) % 12}
    for key, branch in zip(pillar_keys, all_branches):
        if BRANCHES.index(branch) in gm_idxs:
            add_to(key, "공망")

    return result
