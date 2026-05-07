"""
사용자 입력 수집 및 사주 원국 수정 (User Input).

담당 기능:
  - get_user_input()   : CLI 인터랙션으로 사용자 정보 수집
  - correct_pillars()  : 8글자 수동 수정 후 재계산
"""

import os
from datetime import datetime

from core.constants import STEMS, STEMS_KR, BRANCHES, BRANCHES_KR
from core.saju_calculator import recalculate_from_pillars


# ── 상수 ──────────────────────────────────────────────────────────────────────

_STEM_DISPLAY   = "  甲갑 乙을 丙병 丁정 戊무 己기 庚경 辛신 壬임 癸계"
_BRANCH_DISPLAY = "  子자 丑축 寅인 卯묘 辰진 巳사 午오 未미 申신 酉유 戌술 亥해"

_KR_TO_STEM   = dict(zip(STEMS_KR,   STEMS))
_KR_TO_BRANCH = dict(zip(BRANCHES_KR, BRANCHES))


# ── 공개 함수 ─────────────────────────────────────────────────────────────────

def get_user_input() -> dict:
    """CLI 인터랙션으로 사용자 정보 수집."""
    print("\n" + "=" * 60)
    print("   ✦ AI 사주 리포트 자동화 시스템 ✦")
    print("=" * 60 + "\n")

    name   = input("이름: ").strip() or "홍길동"
    birth  = input("생년월일 (예: 1990-05-15): ").strip() or "1990-05-15"
    hour   = input("태어난 시각 - 시 (예: 05, 모르면 엔터): ").strip() or "10"
    minute = input("태어난 시각 - 분 (예: 30, 모르면 엔터): ").strip() or "0"

    # ── 야자시 여부 확인 ──────────────────────────────────────────────────────
    yajasi = False
    try:
        h_check  = int(hour)
        mi_check = int(minute)
        total    = h_check * 60 + mi_check
        is_jasi  = total >= 23 * 60 + 30 or total < 1 * 60 + 30
    except ValueError:
        is_jasi = False

    if is_jasi:
        print("\n  ⏰ 입력하신 시각이 자시(子時, 23:30~01:29) 범위입니다.")
        print("     야자시(夜子時) 적용 여부에 따라 일주·시주가 달라집니다.")
        print("     - 야자시 적용  : 23:30 이후를 다음날로 간주 (현대 명리)")
        print("     - 야자시 미적용: 자정(00:00) 기준 날짜 전환 (전통 방식)")
        ya_input = input("  야자시를 적용하시겠습니까? (y: 적용 / 엔터: 미적용): ").strip().lower()
        yajasi = ya_input == "y"

    gender      = input("\n성별 (남/여): ").strip() or "남"
    rtype_input = input("리포트 유형 (1: 기본, 2: 프리미엄 / 기본값 1): ").strip()
    rtype       = "premium" if rtype_input == "2" else "basic"

    current_year = datetime.now().year
    year_input   = input(
        f"운세 기준 연도 (엔터: {current_year}년 / 다른 연도 예: {current_year + 1}): "
    ).strip()
    target_year  = (
        int(year_input)
        if year_input.isdigit() and 2000 <= int(year_input) <= 2100
        else current_year
    )

    current_month = datetime.now().month if target_year == current_year else 1
    month_input   = input(
        f"월운 시작 월 (엔터: {current_month}월부터 / 1~12 직접 입력): "
    ).strip()
    start_month   = (
        int(month_input)
        if month_input.isdigit() and 1 <= int(month_input) <= 12
        else current_month
    )

    try:
        y, m, d = map(int, birth.split("-"))
        h       = int(hour)
        mi      = int(minute)
    except Exception:
        print("날짜 형식 오류. 기본값으로 진행합니다.")
        y, m, d, h, mi = 1990, 5, 15, 10, 0

    return {
        "name":        name,
        "year":        y,
        "month":       m,
        "day":         d,
        "hour":        h,
        "minute":      mi,
        "gender":      gender,
        "report_type": rtype,
        "target_year": target_year,
        "start_month": start_month,
        "yajasi":      yajasi,
    }


def correct_pillars(saju_data: dict) -> dict:
    """
    사주 원국 8글자를 사용자가 직접 수정하고 파생 데이터를 재계산한다.

    천간 독음 입력: 갑·을·병·정·무·기·경·신·임·계
    지지 독음 입력: 자·축·인·묘·진·사·오·미·신·유·술·해
    """
    def _pick(label: str, mapping: dict, display: str, current: str) -> str:
        """독음 입력 → 한자 반환. 엔터 시 현재값 유지."""
        while True:
            raw = input(
                f"    {label} [{current}] (엔터: 유지)\n{display}\n    > "
            ).strip().lower()
            if raw == "":
                return current
            if raw in mapping:
                return mapping[raw]
            print(f"    ⚠️  '{raw}' 을 인식할 수 없습니다. 다시 입력하세요.")

    orig          = saju_data["사주원국"]
    pillar_labels = [("연주", "연"), ("월주", "월"), ("일주", "일"), ("시주", "시")]

    print("\n" + "=" * 60)
    print("  📝 사주 원국 수정")
    print("  수정할 주(柱)를 선택하세요. 여러 개 선택 가능합니다.")
    print("  예) 1 3  /  전체  /  엔터(건너뜀)")
    print("  1: 연주  2: 월주  3: 일주  4: 시주")
    print("=" * 60)

    sel_raw = input("  선택 > ").strip()
    if sel_raw == "":
        print("  수정 없이 계속합니다.")
        return saju_data

    targets: set[int] = (
        {1, 2, 3, 4}
        if "전체" in sel_raw
        else {int(ch) for ch in sel_raw.split() if ch.isdigit() and 1 <= int(ch) <= 4}
    )

    if not targets:
        print("  선택값이 없습니다. 수정 없이 계속합니다.")
        return saju_data

    new_pillars: dict[str, tuple[str, str]] = {}
    for idx, (key, short) in enumerate(pillar_labels, start=1):
        if idx not in targets:
            new_pillars[key] = (orig[key]["천간"], orig[key]["지지"])
            continue

        cur_stem   = orig[key]["천간"]
        cur_branch = orig[key]["지지"]
        print(f"\n  ── {key} (현재: {cur_stem}{cur_branch}) ──")

        new_stem   = _pick(f"{short}주 천간", _KR_TO_STEM,   _STEM_DISPLAY,   cur_stem)
        new_branch = _pick(f"{short}주 지지", _KR_TO_BRANCH, _BRANCH_DISPLAY, cur_branch)
        new_pillars[key] = (new_stem, new_branch)
        print(f"  → {key}: {new_stem}{new_branch}")

    return recalculate_from_pillars(
        existing_data=saju_data,
        y_stem=new_pillars["연주"][0],  y_branch=new_pillars["연주"][1],
        m_stem=new_pillars["월주"][0],  m_branch=new_pillars["월주"][1],
        d_stem=new_pillars["일주"][0],  d_branch=new_pillars["일주"][1],
        h_stem=new_pillars["시주"][0],  h_branch=new_pillars["시주"][1],
    )


def get_api_keys() -> str:
    """환경변수에서 API 키 로드, 없으면 직접 입력받기."""
    api_keys_str = os.environ.get("GEMINI_API_KEYS", "")
    if not api_keys_str:
        print("\n⚠️  GEMINI_API_KEYS 환경변수가 설정되지 않았습니다.")
        manual = input(
            "   Gemini API 키를 콤마로 구분해 입력하세요 (없으면 엔터): "
        ).strip()
        api_keys_str = manual
    return api_keys_str
