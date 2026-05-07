"""
공통 페이지 빌더 (Pages Common).

표지 / 목차 / 사주원국표+오행분포도 / 에필로그 페이지를 담당한다.
SajuPDF 인스턴스를 첫 번째 인자로 받는 모듈 수준 함수로만 구성한다.
"""

import re
from fpdf.enums import XPos, YPos

from pdf.base_pdf import SajuPDF
from pdf.styles import (
    today_str,
    C_CHARCOAL, C_GOLD, C_OFFWHITE, C_WHITE,
    C_TEXT_DARK, C_TEXT_MID, C_TEXT_LIGHT,
    C_CARD_BORDER, C_ACCENT,
    C_FIRE, C_WOOD, C_EARTH, C_METAL, C_WATER,
    ELEMENT_COLORS,
)


# ── 내부 헬퍼 ─────────────────────────────────────────────────────────────────

def _clean_strength(text: str) -> str:
    return re.sub(r'\([^)]*\)', '', text).strip()


# ── 표지 ──────────────────────────────────────────────────────────────────────

def draw_cover_page(pdf: SajuPDF, saju_data: dict, today: str) -> None:
    """표지 페이지 렌더링."""
    pdf.add_page()
    name     = saju_data["기본정보"]["이름"]
    birth    = saju_data["기본정보"].get("생년월일", "")
    gender   = saju_data["기본정보"]["성별"]
    ilju     = saju_data["사주원국"]["일주"]["간지"]
    strength = _clean_strength(saju_data["일간정보"]["신강신약"])

    # 배경
    pdf._fill(C_CHARCOAL)
    pdf.rect(0, 0, 210, 297, style="F")

    # 장식 원
    for alpha, size in [(15, 120), (8, 80)]:
        pdf.set_fill_color(
            min(255, C_CHARCOAL[0] + alpha),
            min(255, C_CHARCOAL[1] + alpha),
            min(255, C_CHARCOAL[2] + alpha),
        )
        pdf.ellipse(150, -20, size, size, style="F")

    # 상단 골드 바
    pdf._fill(C_GOLD)
    pdf.rect(0, 0, 210, 3, style="F")

    badge_y = 50

    # 부제목
    pdf.set_font("KR-Light", "", 14)
    pdf._text_color(C_GOLD)
    pdf.set_x(0); pdf.set_y(badge_y)
    pdf.cell(210, 6, "*  사주명리 전문 분석 리포트  *", align="C")

    # 命 한자
    pdf.set_font("KR", "B", 72)
    pdf._text_color(C_WHITE)
    pdf.set_y(badge_y + 14)
    pdf.cell(210, 40, "命", align="C")

    # 슬로건
    pdf.set_font("KR-Light", "", 14)
    pdf._text_color((180, 180, 200))
    pdf.set_y(badge_y + 54)
    pdf.cell(210, 8, "나의 운명을 읽는 지혜", align="C")

    # 구분선
    pdf._divider(60, badge_y + 66, 90, C_GOLD, 0.8)

    # 이름
    pdf.set_font("KR", "B", 28)
    pdf._text_color(C_GOLD)
    pdf.set_y(badge_y + 74)
    pdf.cell(210, 14, f"{name} 님", align="C")

    # 생년월일·성별
    pdf.set_font("KR-Light", "", 12)
    pdf._text_color((210, 210, 225))
    pdf.set_y(badge_y + 90)
    pdf.cell(210, 8, f"생년월일: {birth}     성별: {gender}", align="C")

    # 일주 박스
    box_x, box_w, box_h = 70, 70, 42
    box_y = badge_y + 108
    pdf.set_fill_color(60, 80, 100)
    pdf.set_draw_color(*C_GOLD)
    pdf.set_line_width(0.8)
    pdf._rounded_rect_v2(box_x, box_y, box_w, box_h, 5)
    pdf.set_line_width(0.2)

    pdf.set_font("KR-Light", "", 12)
    pdf._text_color(C_GOLD)
    pdf.set_xy(box_x, box_y + 4)
    pdf.cell(box_w, 5, "일주 (핵심 기둥)", align="C")

    pdf.set_font("KR", "B", 28)
    pdf._text_color(C_WHITE)
    pdf.set_xy(box_x, box_y + 10)
    pdf.cell(box_w, 20, ilju, align="C")

    pdf.set_font("KR", "", 12)
    pdf._text_color((180, 200, 220))
    pdf.set_xy(box_x, box_y + 32)
    pdf.cell(box_w, 7, strength, align="C")

    # 하단 날짜
    pdf.set_font("KR-Light", "", 9)
    pdf._text_color((100, 100, 120))
    pdf.set_y(280)
    pdf.cell(210, 6, f"{today}   |   사주 분석", align="C")

    # 하단 골드 바
    pdf._fill(C_GOLD)
    pdf.rect(0, 294, 210, 3, style="F")


# ── 목차 ──────────────────────────────────────────────────────────────────────

def draw_toc_page(pdf: SajuPDF, toc_entries: list) -> None:
    """
    목차 페이지 렌더링.

    Args:
        toc_entries: [("섹션 제목",), ...] 형태의 리스트
    """
    pdf.add_page()
    pdf._toc_page = pdf.page

    pdf._fill(C_OFFWHITE)
    pdf.rect(0, 0, 210, 297, style="F")

    # 헤더
    pdf._fill(C_CHARCOAL)
    pdf.rect(0, 0, 210, 42, style="F")
    pdf._fill(C_GOLD)
    pdf.rect(0, 42, 210, 2, style="F")

    pdf.set_font("KR-Light", "", 10)
    pdf._text_color(C_GOLD)
    pdf.set_xy(0, 14)
    pdf.cell(210, 6, "TABLE OF CONTENTS", align="C")

    pdf.set_font("KR", "B", 22)
    pdf._text_color(C_WHITE)
    pdf.set_xy(0, 22)
    pdf.cell(210, 10, "목   차", align="C")

    # 항목
    start_y = 60
    for i, entry in enumerate(toc_entries):
        title  = entry[0]
        item_y = start_y + i * 20
        if item_y > 270:
            break

        if i % 2 == 0:
            pdf._fill((240, 242, 245))
            pdf.rect(20, item_y - 1, 170, 16, style="F")

        # 번호 뱃지
        pdf._fill(C_CHARCOAL)
        pdf.ellipse(22, item_y + 1, 12, 12, style="F")
        pdf.set_font("KR", "B", 17)
        pdf._text_color(C_GOLD)
        pdf.set_xy(22, item_y + 3)
        pdf.cell(12, 8, str(i + 1), align="C")

        pdf.set_font("KR-Med", "", 17)
        pdf._text_color(C_CHARCOAL)
        pdf.set_xy(38, item_y + 3)
        pdf.cell(150, 8, title)

    pdf._divider(20, 278, 170, C_GOLD, 0.5)
    pdf.set_font("KR-Light", "", 9)
    pdf._text_color(C_TEXT_LIGHT)
    pdf.set_xy(0, 281)
    pdf.cell(210, 6, "사주 분석 시스템", align="C")


# ── 사주 원국표 + 오행 분포도 ─────────────────────────────────────────────────

def draw_saju_intro_page(pdf: SajuPDF, saju_data: dict) -> None:
    """만세력 표 + 오행 분포도 페이지 렌더링 (기본·프리미엄 공용)."""
    pdf._current_section_title = "사주 원국"
    pdf.add_page()
    pdf._fill(C_OFFWHITE)
    pdf.rect(0, 0, 210, 297, style="F")
    pdf._draw_section_header("사주 원국", section_num=0)
    pdf.set_left_margin(20)
    pdf.set_right_margin(20)

    origin  = saju_data["사주원국"]
    sipsung = saju_data.get("십성", {})
    i12     = saju_data.get("십이운성", {})

    PILLAR_ORDER = ["시주", "일주", "월주", "연주"]
    SS_GAN  = {"시주": "시간", "일주": None,  "월주": "월간", "연주": "연간"}
    SS_JI   = {"시주": "시지", "일주": "일지", "월주": "월지", "연주": "연지"}
    I12_KEY = {"시주": "시지", "일주": "일지", "월주": "월지", "연주": "연지"}

    GAN_COLOR = {
        "甲": C_WOOD,  "乙": C_WOOD,
        "丙": C_FIRE,  "丁": C_FIRE,
        "戊": C_EARTH, "己": C_EARTH,
        "庚": C_METAL, "辛": C_METAL,
        "壬": C_WATER, "癸": C_WATER,
    }
    JI_COLOR = {
        "寅": C_WOOD,  "卯": C_WOOD,
        "巳": C_FIRE,  "午": C_FIRE,
        "申": C_METAL, "酉": C_METAL,
        "亥": C_WATER, "子": C_WATER,
        "辰": C_EARTH, "丑": C_EARTH, "未": C_EARTH, "戌": C_EARTH,
    }

    LBL_W   = 28
    COL_W   = 40
    GAP     = 2
    TABLE_W = LBL_W + 4 * COL_W + 4 * GAP
    TABLE_X = (210 - TABLE_W) / 2
    TOP_Y   = pdf.get_y()

    ROW_H_LABEL = 11
    ROW_H_SS    = 12
    ROW_H_HANJA = 20
    ROW_H_I12   = 12
    ROW_H_SAL   = 12

    def _col_x(ci: int) -> float:
        return TABLE_X + LBL_W + GAP + ci * (COL_W + GAP)

    # ── 컬럼 헤더 ────────────────────────────────────────────────────────────
    cy = TOP_Y
    pdf._fill(C_CHARCOAL)
    pdf.rect(TABLE_X, cy, LBL_W, ROW_H_LABEL, style="F")

    for ci, pkey in enumerate(PILLAR_ORDER):
        cx     = _col_x(ci)
        is_day = (pkey == "일주")
        pdf._fill(C_CHARCOAL)
        pdf._stroke(C_CHARCOAL)
        pdf.set_line_width(0.2)
        pdf.rect(cx, cy, COL_W, ROW_H_LABEL, style="F")

        if is_day:
            pdf._stroke(C_GOLD)
            pdf.set_line_width(1.0)
            for lx1, ly1, lx2, ly2 in [
                (cx, cy, cx + COL_W, cy),
                (cx, cy, cx, cy + ROW_H_LABEL),
                (cx + COL_W, cy, cx + COL_W, cy + ROW_H_LABEL),
                (cx, cy + ROW_H_LABEL, cx + COL_W, cy + ROW_H_LABEL),
            ]:
                pdf.line(lx1, ly1, lx2, ly2)
            pdf.set_line_width(0.2)

        pdf.set_font("KR", "", 13)
        pdf._text_color(C_GOLD if is_day else (180, 190, 205))
        pdf.set_xy(cx, cy + 1.5)
        pdf.cell(COL_W, ROW_H_LABEL - 2, pkey, align="C")

    cy += ROW_H_LABEL

    # ── 행 그리기 헬퍼 ───────────────────────────────────────────────────────
    def _draw_row(
        row_h: float, row_label: str, values: list,
        font_size: float = 9, bold: bool = False,
        value_colors: list = None,
    ) -> None:
        nonlocal cy
        # 라벨 셀
        pdf._fill((235, 237, 243))
        pdf._stroke(C_CARD_BORDER)
        pdf.set_line_width(0.15)
        pdf.rect(TABLE_X, cy, LBL_W, row_h, style="FD")
        pdf.set_font("KR", "", 13)
        pdf._text_color(C_TEXT_MID)
        label_parts = row_label.split("\n")
        if len(label_parts) == 2:
            lh2 = 7
            sy  = cy + (row_h - lh2 * 2) / 2
            pdf.set_xy(TABLE_X, sy);         pdf.cell(LBL_W, lh2, label_parts[0], align="C")
            pdf.set_xy(TABLE_X, sy + lh2);   pdf.cell(LBL_W, lh2, label_parts[1], align="C")
        else:
            pdf.set_xy(TABLE_X, cy + (row_h - 11) / 2)
            pdf.cell(LBL_W, 11, row_label, align="C")

        # 데이터 셀
        for ci, (pkey, val) in enumerate(zip(PILLAR_ORDER, values)):
            cx         = _col_x(ci)
            is_hanja   = (font_size >= 20)
            fill_color = (
                value_colors[ci]
                if is_hanja and value_colors
                else ((245, 246, 250) if ci % 2 == 0 else C_WHITE)
            )
            pdf._fill(fill_color)
            pdf._stroke(C_CARD_BORDER)
            pdf.set_line_width(0.15)
            pdf.rect(cx, cy, COL_W, row_h, style="FD")
            pdf.set_line_width(0.2)

            tc = (
                pdf.get_text_color(fill_color)
                if is_hanja and value_colors
                else C_TEXT_DARK
            )
            pdf.set_font("KR", "B" if bold else "", font_size)
            pdf._text_color(tc)
            pdf.set_xy(cx, cy + (row_h - font_size * 0.4) / 2)
            pdf.cell(COL_W, font_size * 0.4 + 1, val, align="C")

        cy += row_h

    # 십성(천간)
    _draw_row(
        ROW_H_SS, "십성(천간)",
        [sipsung.get(SS_GAN[p], "일간") if SS_GAN[p] else "일간(나)" for p in PILLAR_ORDER],
        font_size=15,
    )
    # 천간 한자
    gan_vals = [origin[p]["천간"] for p in PILLAR_ORDER]
    _draw_row(
        ROW_H_HANJA, "천  간", gan_vals,
        font_size=23, bold=True,
        value_colors=[GAN_COLOR.get(v, C_TEXT_DARK) for v in gan_vals],
    )
    # 지지 한자
    ji_vals = [origin[p]["지지"] for p in PILLAR_ORDER]
    _draw_row(
        ROW_H_HANJA, "지  지", ji_vals,
        font_size=23, bold=True,
        value_colors=[JI_COLOR.get(v, C_TEXT_DARK) for v in ji_vals],
    )
    # 십성(지지)
    _draw_row(ROW_H_SS, "십성(지지)", [sipsung.get(SS_JI[p], "") for p in PILLAR_ORDER], font_size=15)
    # 12운성
    _draw_row(ROW_H_I12, "12운성", [i12.get(I12_KEY[p], "-") for p in PILLAR_ORDER], font_size=15)

    # 신살 행
    shinsal_dict = saju_data.get("신살", {})

    def _first_sal(pkey: str) -> str:
        if isinstance(shinsal_dict, dict):
            sals = shinsal_dict.get(pkey, [])
            return sals[0] if sals else "-"
        elif isinstance(shinsal_dict, list):
            return shinsal_dict[0] if shinsal_dict else "-"
        return "-"

    sal_vals   = [_first_sal(p) for p in PILLAR_ORDER]
    sal_colors = [(180, 50, 50) if v != "-" else C_TEXT_LIGHT for v in sal_vals]

    rh = ROW_H_SAL
    pdf._fill((235, 237, 243))
    pdf._stroke(C_CARD_BORDER)
    pdf.set_line_width(0.15)
    pdf.rect(TABLE_X, cy, LBL_W, rh, style="FD")
    pdf.set_font("KR", "", 13)
    pdf._text_color(C_TEXT_MID)
    pdf.set_xy(TABLE_X, cy + (rh - 11) / 2)
    pdf.cell(LBL_W, 11, "신  살", align="C")

    for ci, (pkey, val) in enumerate(zip(PILLAR_ORDER, sal_vals)):
        cx2 = _col_x(ci)
        fill_color = (245, 246, 250) if ci % 2 == 0 else C_WHITE
        pdf._fill(fill_color)
        pdf._stroke(C_CARD_BORDER)
        pdf.set_line_width(0.15)
        pdf.rect(cx2, cy, COL_W, rh, style="FD")
        pdf.set_line_width(0.2)
        pdf.set_font("KR", "", 15)
        pdf._text_color(sal_colors[ci])
        pdf.set_xy(cx2, cy + (rh - 11) / 2)
        pdf.cell(COL_W, 11, val, align="C")

    # 일주 컬럼 골드 외곽선
    table_height = (
        ROW_H_LABEL + ROW_H_SS + ROW_H_HANJA * 2
        + ROW_H_SS + ROW_H_I12 + ROW_H_SAL
    )
    pdf._stroke(C_GOLD)
    pdf.set_line_width(1.2)
    pdf.rect(_col_x(1), TOP_Y, COL_W, table_height)
    pdf.set_line_width(0.2)

    cy += rh
    pdf.set_y(cy + 8)

    # ── 오행 분포도 ───────────────────────────────────────────────────────────
    ELEM_META = [
        ("목", "木", "나무", C_WOOD),
        ("화", "火", "불",   C_FIRE),
        ("토", "土", "흙",   C_EARTH),
        ("금", "金", "금",   C_METAL),
        ("수", "水", "물",   C_WATER),
    ]
    elements = saju_data.get("오행분포", {})

    def _elem_status(val: int) -> tuple[str, float]:
        if val == 0:   return ("부족",  0.00)
        elif val == 1: return ("약함",  0.20)
        elif val == 2: return ("균형",  0.40)
        elif val == 3: return ("강함",  0.60)
        elif val == 4: return ("과다",  0.80)
        else:          return ("극단",  1.00)

    pdf.set_font("KR", "B", 17)
    pdf._text_color(C_CHARCOAL)
    pdf.set_x(TABLE_X)
    pdf.cell(0, 9, "오행 분포도", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(8)

    ICON_R   = 7
    TABLE_X  += 6
    ICON_D   = ICON_R * 2
    NAME_W   = 16
    BAR_X0   = TABLE_X + ICON_D + 6 + NAME_W + 3
    COUNT_W  = 22
    BAR_MAXW = (TABLE_X + TABLE_W) - BAR_X0 - COUNT_W - 4
    ROW_H_E  = ICON_D + 4

    for ek, hanja, name_kr, color in ELEM_META:
        val                  = elements.get(ek, 0)
        status_label, fill_r = _elem_status(val)
        bar_w = int(BAR_MAXW * fill_r)
        ey    = pdf.get_y()

        # 아이콘 원
        pdf._fill(color); pdf._stroke(color); pdf.set_line_width(0)
        pdf.ellipse(TABLE_X, ey, ICON_D, ICON_D, style="F")
        pdf.set_line_width(0.2)
        pdf.set_font("KR", "B", 15)
        pdf._text_color(pdf.get_text_color(color))
        pdf.set_xy(TABLE_X, ey + ICON_R - 6)
        pdf.cell(ICON_D, 12, hanja, align="C")

        # 한글 이름
        pdf.set_font("KR", "", 15)
        pdf._text_color(C_TEXT_DARK)
        pdf.set_xy(TABLE_X + ICON_D + 4, ey + ICON_R - 6)
        pdf.cell(NAME_W, 12, name_kr)

        # 배경 바
        pdf._fill((225, 228, 233)); pdf._stroke((225, 228, 233)); pdf.set_line_width(0)
        pdf._rounded_rect_v2(BAR_X0, ey + 3, BAR_MAXW, ICON_D - 6, 3)
        pdf.set_line_width(0.2)

        # 채움 바
        if bar_w > 0:
            pdf._fill(color); pdf._stroke(color); pdf.set_line_width(0)
            pdf._rounded_rect_v2(BAR_X0, ey + 3, bar_w, ICON_D - 6, 3)
            pdf.set_line_width(0.2)

        # 상태 레이블
        pdf.set_font("KR", "B", 14)
        pdf._text_color(pdf.get_text_color(color) if bar_w > 0 else C_TEXT_MID)
        pdf.set_xy(BAR_X0 + 6, ey + ICON_R - 5.5)
        pdf.cell(max(bar_w - 6, 26), 11, status_label)

        # 개수
        pdf.set_font("KR", "", 15)
        pdf._text_color(C_TEXT_MID)
        pdf.set_xy(BAR_X0 + BAR_MAXW + 5, ey + ICON_R - 6)
        pdf.cell(COUNT_W, 12, f"{val}개")

        pdf.set_y(ey + ROW_H_E)

    pdf.ln(4)


# ── 에필로그 ──────────────────────────────────────────────────────────────────

def draw_epilogue_page(pdf: SajuPDF, name: str, today: str) -> None:
    """마지막(에필로그) 페이지 렌더링."""
    pdf.add_page()
    pdf._fill(C_CHARCOAL)
    pdf.rect(0, 0, 210, 297, style="F")
    pdf._fill(C_GOLD)
    pdf.rect(0, 0, 210, 3, style="F")

    # 장식 원
    pdf.set_fill_color(55, 75, 95)
    pdf.ellipse(-30, 180, 140, 140, style="F")
    pdf.set_fill_color(50, 70, 90)
    pdf.ellipse(130, -20, 100, 100, style="F")

    # 인용문 박스
    qx, qy, qw, qh = 25, 70, 160, 140
    pdf.set_fill_color(55, 72, 90)
    pdf.set_draw_color(*C_GOLD)
    pdf.set_line_width(0.6)
    pdf._rounded_rect_v2(qx, qy, qw, qh, 6)
    pdf.set_line_width(0.2)

    # 여는 따옴표
    pdf.set_font("KR", "B", 48)
    pdf._text_color(C_GOLD)
    pdf.set_xy(qx + 8, qy + 4)
    pdf.cell(20, 18, '"')

    quote_lines = [
        "사주는 운명의 설계도입니다.",
        "",
        "하지만 그 설계도를",
        "어떻게 활용하느냐는",
        "오직 당신의 선택과",
        "의지에 달려 있습니다.",
        "",
        f"{name} 님의 삶에",
        "작은 빛이 되기를 바랍니다.",
    ]
    pdf.set_font("KR", "", 16)
    pdf._text_color((210, 215, 228))
    ty = qy + 28
    for line in quote_lines:
        pdf.set_xy(qx, ty)
        pdf.cell(qw, 10, line, align="C")
        ty += 10

    # 닫는 따옴표
    pdf.set_font("KR", "B", 48)
    pdf._text_color(C_GOLD)
    pdf.set_xy(qx + qw - 30, qy + qh - 22)
    pdf.cell(20, 18, '"')

    pdf._divider(55, 228, 100, C_GOLD, 0.5)
    pdf.set_font("KR", "", 13)
    pdf._text_color(C_TEXT_LIGHT)
    pdf.set_xy(0, 233)
    pdf.cell(210, 8, "— 사주 분석 시스템 —", align="C")

    pdf.set_font("KR-Light", "", 12)
    pdf.set_xy(0, 242)
    pdf.cell(210, 8, today, align="C")

    pdf._fill(C_GOLD)
    pdf.rect(0, 294, 210, 3, style="F")
