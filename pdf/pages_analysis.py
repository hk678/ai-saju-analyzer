"""
AI 분석 섹션 페이지 빌더 (Pages Analysis).

프리미엄 8개 분석 섹션 / 기본 리포트 3개 섹션 /
월별·연간 운세 서술 페이지를 담당한다.

모든 함수는 SajuPDF 인스턴스를 첫 번째 인자로 받는 모듈 수준 함수이다.
"""

from pdf.base_pdf import SajuPDF


# ── 프리미엄·기본 공용 분석 섹션 ─────────────────────────────────────────────

def draw_analysis_section(pdf: SajuPDF, title: str, content: str) -> None:
    """
    단일 AI 분석 텍스트 섹션 렌더링.

    Args:
        pdf:     SajuPDF 인스턴스
        title:   섹션 제목 (예: "타고난 본질과 성격")
        content: AI 생성 마크다운 텍스트
    """
    pdf._start_content_page(title)
    pdf._render_markdown(content, x=20, width=170)


# ── 기본 리포트 전용 ──────────────────────────────────────────────────────────

def draw_this_year_section(
    pdf: SajuPDF, content: str, target_year: int = None
) -> None:
    """기본 리포트 — 신년 총평 페이지."""
    year_str = f"{target_year}년" if target_year else "올해"
    pdf._start_content_page(f"{year_str} 간략 총평")
    pdf._render_markdown(content, x=20, width=170)


def draw_summary_section(
    pdf: SajuPDF, content: str, target_year: int = None
) -> None:
    """기본 리포트 — 전반 운세 요약 페이지."""
    year_str = f"{target_year}년 " if target_year else ""
    pdf._start_content_page(f"{year_str}전반 운세")
    pdf._render_markdown(content, x=20, width=170)


# ── 월별·연간 운세 서술 ───────────────────────────────────────────────────────

def draw_monthly_section(
    pdf: SajuPDF, monthly: dict, target_year: int = None
) -> None:
    """
    월별 운세 텍스트 섹션 렌더링.

    월운 키: "YYYY-MM" 형식 (예: "2026-03")
    첫 번째 월만 섹션 번호 자동 증가, 이후 페이지는 같은 섹션으로 처리한다.
    """
    month_names = [
        "1월","2월","3월","4월","5월","6월",
        "7월","8월","9월","10월","11월","12월",
    ]

    def _sort_key(k: str) -> tuple:
        parts = k.split("-")
        return (int(parts[0]), int(parts[1]))

    first = True
    for ym_key, content in sorted(monthly.items(), key=lambda x: _sort_key(x[0])):
        parts  = ym_key.split("-")
        yr, mn = int(parts[0]), int(parts[1])
        pdf._start_content_page(
            f"{yr}년 {month_names[mn - 1]} 운세",
            auto_number=first,
        )
        first = False
        pdf._render_markdown(content, x=20, width=170)
        pdf.ln(4)


def draw_yearly_section(pdf: SajuPDF, yearly: dict) -> None:
    """
    연간 운세 텍스트 섹션 렌더링.

    연운 키: "YYYY" 형식 (예: "2026")
    첫 번째 연도만 섹션 번호 자동 증가, 이후 페이지는 같은 섹션으로 처리한다.
    """
    first = True
    for year_key, content in sorted(yearly.items(), key=lambda x: int(x[0])):
        pdf._start_content_page(
            f"{year_key}년 연간 운세",
            auto_number=first,
        )
        first = False
        pdf._render_markdown(content, x=20, width=170)
        pdf.ln(4)
