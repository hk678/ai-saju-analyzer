"""
운세 데이터 테이블 페이지 빌더 (Pages Fortune).

세운표 / 월운표 / 대운표 등 표(Table) 형식의 데이터 페이지를 담당한다.
모든 함수는 SajuPDF 인스턴스를 첫 번째 인자로 받는 모듈 수준 함수이다.
"""

from pdf.base_pdf import SajuPDF
from pdf.styles import (
    C_CHARCOAL, C_GOLD, C_WHITE,
    C_TEXT_DARK, C_TEXT_MID, C_TEXT_LIGHT,
    C_CARD_BORDER, C_FIRE,
    ELEMENT_COLORS,
)


# ── 내부 헬퍼 ─────────────────────────────────────────────────────────────────

def _ganji(pillar: dict) -> str:
    return pillar["간지"]["천간"] + pillar["간지"]["지지"]

def _gan_elem(pillar: dict) -> str:  return pillar["천간"]["오행"]
def _gan_ss(pillar: dict) -> str:    return pillar["천간"]["십성"]["값"]
def _ji_elem(pillar: dict) -> str:   return pillar["지지"]["오행"]
def _ji_ss(pillar: dict) -> str:     return pillar["지지"]["십성"]["값"]
def _ji_12(pillar: dict) -> str:     return pillar["지지"]["12운성"]

def _ji_sal(pillar: dict) -> str:
    sal = pillar["지지"]["신살"]
    return "/".join(sal) if sal else "-"


def _draw_table_header(
    pdf: SajuPDF,
    headers: list[str],
    col_ws: list[float],
    table_x: float = 17,
    row_h: float = 9,
) -> None:
    """헤더 행 렌더링 (어두운 배경 + 골드 텍스트)."""
    pdf._fill(C_CHARCOAL)
    total_w = sum(col_ws)
    pdf.rect(table_x, pdf.get_y(), total_w, row_h, style="F")
    pdf.set_font("KR-Light", "", 8)
    pdf._text_color(C_GOLD)
    cx = table_x
    for hw, hd in zip(col_ws, headers):
        pdf.set_xy(cx, pdf.get_y())
        pdf.cell(hw, row_h, hd, align="C")
        cx += hw
    pdf.ln(row_h)


def _draw_data_row(
    pdf: SajuPDF,
    row_vals: list[str],
    col_ws: list[float],
    elem_col_idxs: set[int],
    sal_col_idx: int,
    row_idx: int,
    table_x: float = 17,
    row_h: float = 9,
) -> None:
    """데이터 행 렌더링. 오행 열은 색상 강조, 신살 열은 붉은 색상 처리."""
    ry = pdf.get_y()
    bg = (248, 248, 252) if row_idx % 2 == 0 else (255, 255, 255)
    pdf._fill(bg)
    pdf._stroke(C_CARD_BORDER)
    pdf.set_line_width(0.15)
    total_w = sum(col_ws)
    pdf.rect(table_x, ry, total_w, row_h, style="FD")

    cx = table_x
    for ci, (hw, rv) in enumerate(zip(col_ws, row_vals)):
        pdf.set_xy(cx, ry)
        if ci in elem_col_idxs:
            pdf._text_color(ELEMENT_COLORS.get(rv, C_TEXT_MID))
            pdf.set_font("KR", "B", 8)
        elif ci == sal_col_idx:
            pdf._text_color(C_FIRE if rv not in ("-", "") else C_TEXT_LIGHT)
            pdf.set_font("KR", "", 8)
        else:
            pdf._text_color(C_TEXT_DARK)
            pdf.set_font("KR", "", 8)
        pdf.cell(hw, row_h, rv, align="C")
        cx += hw
    pdf.ln(row_h)


# ── 세운표 ────────────────────────────────────────────────────────────────────

def draw_seun_table(pdf: SajuPDF, seun_list: list) -> None:
    """
    세운(年運) 데이터 테이블 페이지 렌더링.

    Args:
        pdf:       SajuPDF 인스턴스
        seun_list: get_seun() 반환값 리스트
    """
    if not seun_list:
        return

    TABLE_X  = 17
    ROW_H    = 9
    HEADERS  = ["연도", "간지", "천간오행", "천간십성", "지지오행", "지지십성", "12운성", "신살"]
    COL_WS   = [20,     18,      20,         24,          20,         24,          20,        25]
    ELEM_IDX = {2, 4}   # 천간오행, 지지오행
    SAL_IDX  = 7

    def _render_header() -> None:
        pdf._start_content_page("세운(年運) 데이터")
        _draw_table_header(pdf, HEADERS, COL_WS, TABLE_X, ROW_H)

    _render_header()

    for di, seun in enumerate(seun_list):
        if pdf.get_y() > 268:
            _render_header()

        row_vals = [
            str(seun["연도"]),
            _ganji(seun),
            _gan_elem(seun), _gan_ss(seun),
            _ji_elem(seun),  _ji_ss(seun),
            _ji_12(seun),    _ji_sal(seun),
        ]
        _draw_data_row(pdf, row_vals, COL_WS, ELEM_IDX, SAL_IDX, di, TABLE_X, ROW_H)


# ── 월운표 ────────────────────────────────────────────────────────────────────

def draw_wolun_table(pdf: SajuPDF, wolun_list: list) -> None:
    """
    월운(月運) 데이터 테이블 페이지 렌더링.

    연도가 바뀔 때 새 페이지로 자동 분리한다.

    Args:
        pdf:        SajuPDF 인스턴스
        wolun_list: get_wolun() 반환값 리스트
    """
    if not wolun_list:
        return

    TABLE_X   = 17
    ROW_H     = 9
    HEADERS   = ["월",  "간지", "천간오행", "천간십성", "지지오행", "지지십성", "12운성", "신살"]
    COL_WS    = [14,    18,      20,         24,          20,         24,          20,        31]
    ELEM_IDX  = {2, 4}
    SAL_IDX   = 7
    MONTH_KR  = [
        "1월","2월","3월","4월","5월","6월",
        "7월","8월","9월","10월","11월","12월",
    ]

    def _render_header(year: int) -> None:
        pdf._start_content_page(f"{year}년 월운(月運) 데이터")
        _draw_table_header(pdf, HEADERS, COL_WS, TABLE_X, ROW_H)

    current_year = wolun_list[0]["연도"]
    _render_header(current_year)

    for di, wolun in enumerate(wolun_list):
        yr = wolun["연도"]
        if yr != current_year:
            current_year = yr
            _render_header(current_year)
        elif pdf.get_y() > 268:
            _render_header(current_year)

        row_vals = [
            MONTH_KR[wolun["월"] - 1],
            _ganji(wolun),
            _gan_elem(wolun), _gan_ss(wolun),
            _ji_elem(wolun),  _ji_ss(wolun),
            _ji_12(wolun),    _ji_sal(wolun),
        ]
        _draw_data_row(pdf, row_vals, COL_WS, ELEM_IDX, SAL_IDX, di, TABLE_X, ROW_H)


# ── 대운표 ────────────────────────────────────────────────────────────────────

def draw_daewun_table(pdf: SajuPDF, saju_data: dict) -> None:
    """
    대운(大運) 데이터 테이블 페이지 렌더링.

    원국 데이터와 대운 10개를 한 페이지에 표시한다.

    Args:
        pdf:       SajuPDF 인스턴스
        saju_data: calculate_saju() 반환값
    """
    daewun_list = saju_data.get("대운", [])
    if not daewun_list:
        return

    TABLE_X  = 17
    ROW_H    = 9
    HEADERS  = ["나이", "간지", "천간오행", "천간십성", "지지오행", "지지십성", "12운성", "신살"]
    COL_WS   = [20,     18,      20,         24,          20,         24,          20,        25]
    ELEM_IDX = {2, 4}
    SAL_IDX  = 7

    pdf._start_content_page("대운(大運) 흐름")
    _draw_table_header(pdf, HEADERS, COL_WS, TABLE_X, ROW_H)

    for di, dw in enumerate(daewun_list):
        if pdf.get_y() > 268:
            pdf._start_content_page("대운(大運) 흐름")
            _draw_table_header(pdf, HEADERS, COL_WS, TABLE_X, ROW_H)

        next_age = (
            daewun_list[di + 1]["시작나이"]
            if di + 1 < len(daewun_list)
            else dw["시작나이"] + 10
        )
        age_str = f"{dw['시작나이']}~{next_age - 1}세"

        row_vals = [
            age_str,
            _ganji(dw),
            _gan_elem(dw), _gan_ss(dw),
            _ji_elem(dw),  _ji_ss(dw),
            _ji_12(dw),    _ji_sal(dw),
        ]
        _draw_data_row(pdf, row_vals, COL_WS, ELEM_IDX, SAL_IDX, di, TABLE_X, ROW_H)
