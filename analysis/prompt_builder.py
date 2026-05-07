"""
프롬프트 컨텍스트 조립 모듈 (Prompt Builder).

프롬프트에 삽입되는 사주 데이터 요약 문자열을 생성한다.
API 호출 로직과 프롬프트 템플릿 양쪽 모두와 분리된 순수 데이터 변환 레이어.

공개 함수:
  build_origin_context   — 사주원국 전체 컨텍스트 (프롬프트 공통 삽입용)
  pillar_str             — _build_pillar_block 구조 → 한 줄 요약
  current_year_from_saju — saju_data에서 현재 연도 추출
"""

from datetime import datetime


# ── 공개 헬퍼 ─────────────────────────────────────────────────────────────────

def current_year_from_saju(saju_data: dict) -> int:
    """saju_data의 세운 첫 연도를 현재 연도로 사용 (대운 강조용)."""
    seun_list = saju_data.get("세운", [])
    if seun_list:
        return seun_list[0]["연도"]
    return datetime.now().year


def pillar_str(pillar: dict) -> str:
    """
    _build_pillar_block 구조에서 한 줄 요약 문자열 반환.

    예) "丙午 (천간:丙·화·정인 / 지지:午·화·편관 / 12운성:제왕 / 신살:육해살/장성살)"
    """
    gan      = pillar["간지"]["천간"]
    ji       = pillar["간지"]["지지"]
    gan_elem = pillar["천간"]["오행"]
    gan_ss   = pillar["천간"]["십성"]["값"]
    ji_elem  = pillar["지지"]["오행"]
    ji_ss    = pillar["지지"]["십성"]["값"]
    un       = pillar["지지"]["12운성"]
    sal      = "/".join(pillar["지지"]["신살"]) if pillar["지지"]["신살"] else "없음"
    return (
        f"{gan}{ji} "
        f"(천간:{gan}·{gan_elem}·{gan_ss} / "
        f"지지:{ji}·{ji_elem}·{ji_ss} / "
        f"12운성:{un} / 신살:{sal})"
    )


def build_origin_context(saju_data: dict, current_year: int = None) -> str:
    """
    사주원국 전체 컨텍스트 문자열 생성 (모든 프롬프트에 공통 삽입).

    current_year 전달 시 해당 나이에 해당하는 대운을 ★현재대운★ 으로 강조한다.
    """
    ori        = saju_data["사주원국"]
    twelve     = saju_data.get("십이운성", {})
    sipsung    = saju_data.get("십성", {})
    shinsal_raw = saju_data.get("신살", {})

    # 신살: 주별 dict(신버전) or list(구버전) 모두 지원
    def _shinsal_str(data) -> str:
        if isinstance(data, dict):
            parts = []
            for pkey in ["연주", "월주", "일주", "시주"]:
                sals = data.get(pkey, [])
                parts.append(f"{pkey}=[{', '.join(sals) if sals else '없음'}]")
            extra = data.get("원국", [])
            if extra:
                parts.append(f"원국추가=[{', '.join(extra)}]")
            return "  ".join(parts)
        elif isinstance(data, list):
            return ", ".join(data) if data else "없음"
        return "없음"

    # 현재 나이 계산
    current_age = None
    if current_year:
        try:
            birth_year  = int(saju_data["기본정보"]["생년월일"][:4])
            current_age = current_year - birth_year
        except Exception:
            pass

    lines = [
        (
            f"사주원국: 연주 {ori['연주']['간지']}  월주 {ori['월주']['간지']}"
            f"  일주 {ori['일주']['간지']}  시주 {ori['시주']['간지']}"
        ),
        f"일간: {saju_data['일간정보']['일간']} ({saju_data['일간정보']['오행']} · {saju_data['일간정보']['음양']})",
        f"신강신약: {saju_data['일간정보']['신강신약']}",
        (
            f"오행분포: 목{saju_data['오행분포']['목']} 화{saju_data['오행분포']['화']} "
            f"토{saju_data['오행분포']['토']} 금{saju_data['오행분포']['금']} 수{saju_data['오행분포']['수']}"
        ),
        (
            f"십성: 연간={sipsung.get('연간','-')} 연지={sipsung.get('연지','-')} "
            f"월간={sipsung.get('월간','-')} 월지={sipsung.get('월지','-')} "
            f"일지={sipsung.get('일지','-')} 시간={sipsung.get('시간','-')} 시지={sipsung.get('시지','-')}"
        ),
        (
            f"십이운성: 연지={twelve.get('연지','-')} 월지={twelve.get('월지','-')} "
            f"일지={twelve.get('일지','-')} 시지={twelve.get('시지','-')}"
        ),
        f"원국 신살(주별): {_shinsal_str(shinsal_raw)}",
        f"대운수: {saju_data.get('대운수', '-')}세 시작",
    ]

    # 대운 흐름 (현재 대운 ★강조★)
    daewun = saju_data.get("대운", [])
    if daewun:
        dw_lines = []
        for i, d in enumerate(daewun):
            gan      = d["간지"]["천간"]
            ji       = d["간지"]["지지"]
            sal      = "/".join(d["지지"]["신살"]) if d["지지"]["신살"] else "-"
            next_age = daewun[i + 1]["시작나이"] if i + 1 < len(daewun) else d["시작나이"] + 10
            is_now   = current_age is not None and d["시작나이"] <= current_age < next_age
            marker   = " ★현재대운★" if is_now else ""
            dw_lines.append(
                f"  {d['시작나이']}세~{next_age - 1}세: {gan}{ji}{marker} "
                f"(천간십성:{d['천간']['십성']['값']} / "
                f"지지십성:{d['지지']['십성']['값']} / "
                f"12운성:{d['지지']['12운성']} / 신살:{sal})"
            )
        lines.append("대운 흐름:\n" + "\n".join(dw_lines))

    return "\n".join(lines)
