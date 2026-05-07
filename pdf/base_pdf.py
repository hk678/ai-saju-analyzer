"""
SajuPDF 기본 클래스 (Base PDF).

폰트 등록, 헤더·푸터, 공통 드로잉 메서드만 포함한다.
페이지별 콘텐츠 빌더는 pages_*.py 에 위치한다.
"""

import os
import re

from fpdf import FPDF
from fpdf.enums import XPos, YPos

from pdf.styles import (
    FONT_DIR,
    C_CHARCOAL, C_GOLD, C_OFFWHITE, C_WHITE,
    C_TEXT_DARK, C_TEXT_MID, C_TEXT_LIGHT,
    C_CARD_BORDER, C_ACCENT,
)
from pdf.markdown_parser import parse_markdown_blocks, strip_markdown


class SajuPDF(FPDF):
    """
    사주 리포트 PDF 기본 클래스.

    폰트 등록 / 헤더·푸터 / 공통 드로잉 / 마크다운 렌더러를 담당한다.
    표지·목차·원국·분석·운세 페이지 빌더는 이 클래스를 인자로 받는
    별도 함수(pages_*.py)에서 구현한다.
    """

    def __init__(self) -> None:
        super().__init__(orientation="P", unit="mm", format="A4")
        self.set_auto_page_break(auto=False)
        self._register_fonts()
        self.set_margins(0, 0, 0)
        self._page_num_enabled      = False
        self._section_counter       = 0
        self._current_section_title = ""
        self._toc_page              = 0

    # ── 폰트 등록 ──────────────────────────────────────────────────────────────

    def _register_fonts(self) -> None:
        self.add_font("KR",       "",  os.path.join(FONT_DIR, "NotoSansKR-Regular.ttf"))
        self.add_font("KR",       "B", os.path.join(FONT_DIR, "NotoSansKR-Bold.ttf"))
        self.add_font("KR-Light", "",  os.path.join(FONT_DIR, "NotoSansKR-Light.ttf"))
        self.add_font("KR-Med",   "",  os.path.join(FONT_DIR, "NotoSansKR-Regular.ttf"))

    # ── 헤더 / 푸터 ──────────────────────────────────────────────────────────

    def header(self) -> None:
        pass

    def footer(self) -> None:
        if not self._page_num_enabled:
            return
        if self.page <= self._toc_page:
            return
        self.set_y(-14)
        self.set_font("KR-Light", "", 9)
        self.set_text_color(*C_TEXT_LIGHT)
        self.cell(0, 8, f"- {self.page - self._toc_page} -", align="C")

    # ── 색상 헬퍼 ────────────────────────────────────────────────────────────

    def _fill(self, rgb: tuple) -> None:
        self.set_fill_color(*rgb)

    def _stroke(self, rgb: tuple) -> None:
        self.set_draw_color(*rgb)

    def _text_color(self, rgb: tuple) -> None:
        self.set_text_color(*rgb)

    def get_text_color(self, bg: tuple) -> tuple:
        """배경색에 관계없이 일관된 텍스트 색상 반환."""
        return (90, 90, 90)

    # ── 도형 드로잉 헬퍼 ─────────────────────────────────────────────────────

    def _rounded_rect_v2(self, x: float, y: float, w: float, h: float, r: float = 4) -> None:
        try:
            self.rect(x, y, w, h, style="FD", round_corners=True, corner_radius=r)
        except TypeError:
            self.rect(x, y, w, h, style="FD")

    def _divider(
        self, x: float, y: float, w: float,
        color: tuple = C_GOLD, thickness: float = 0.5,
    ) -> None:
        self.set_draw_color(*color)
        self.set_line_width(thickness)
        self.line(x, y, x + w, y)
        self.set_line_width(0.2)

    def _section_title(self, title: str, x: float = 20) -> None:
        y = self.get_y()
        self.set_xy(x, y)
        self.set_font("KR", "B", 17)
        self._text_color(C_CHARCOAL)
        self.cell(0, 8, title, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        bar_y = self.get_y() + 1
        self._fill(C_GOLD)
        self._stroke(C_GOLD)
        self.rect(x, bar_y, 30, 2, style="F")
        self.ln(6)

    # ── 섹션 헤더 / 페이지 시작 ──────────────────────────────────────────────

    def _draw_section_header(self, section_title: str, section_num: int = 0) -> None:
        self._fill(C_CHARCOAL)
        self.rect(0, 0, 210, 28, style="F")
        self._fill(C_GOLD)
        self.rect(0, 28, 210, 1.5, style="F")

        display_title = (
            f"{section_num}. {section_title}" if section_num > 0 else section_title
        )
        self.set_font("KR", "B", 16)
        self._text_color(C_WHITE)
        self.set_xy(20, 9)
        self.cell(150, 10, display_title)

        self.set_font("KR-Light", "", 14)
        self._text_color(C_GOLD)
        self.set_xy(150, 10)
        self.cell(40, 8, "사주 분석", align="R")
        self.set_y(45)

    def _start_content_page(
        self, section_title: str, auto_number: bool = True
    ) -> None:
        self._current_section_title = section_title
        if auto_number:
            self._section_counter += 1
        self.add_page()
        self.start_section(
            f"{self._section_counter}. {section_title}" if auto_number else section_title,
            level=0,
        )
        self._fill(C_OFFWHITE)
        self.rect(0, 0, 210, 297, style="F")
        self._draw_section_header(section_title, section_num=self._section_counter)
        self.set_left_margin(20)
        self.set_right_margin(20)

    # ── 마크다운 렌더러 ───────────────────────────────────────────────────────

    def _render_markdown(
        self, text: str, x: float = 20, width: float = 170, line_h: float = 15
    ) -> None:
        PAGE_BOTTOM    = 250
        CHARS_PER_LINE = 33

        blocks = parse_markdown_blocks(text)
        self.set_left_margin(x)
        self.set_right_margin(210 - x - width)

        def _new_content_page() -> None:
            self.add_page()
            self._fill(C_OFFWHITE)
            self.rect(0, 0, 210, 297, style="F")
            if self._current_section_title:
                self._draw_section_header(
                    self._current_section_title,
                    section_num=self._section_counter,
                )
            self.set_left_margin(x)
            self.set_right_margin(210 - x - width)

        def _estimate_lines(content: str, chars_per_line: int = 30) -> int:
            return max(1, (len(content) // chars_per_line) + 1)

        _just_broke_page = [False]

        def _new_content_page_tracked() -> None:
            _new_content_page()
            _just_broke_page[0] = True

        def _ensure_space(needed_mm: float) -> None:
            if _just_broke_page[0]:
                _just_broke_page[0] = False
                return
            if self.get_y() + needed_mm > PAGE_BOTTOM:
                _new_content_page_tracked()

        def _count_wrapped_lines(s: str) -> int:
            total  = 0
            text_w = (width - 8)
            for raw_line in s.split("\n"):
                if not raw_line:
                    total += 1
                    continue
                line_w = 0
                total += 1
                for ch in list(raw_line):
                    cw = self.get_string_width(ch)
                    if line_w + cw > text_w:
                        total += 1
                        line_w = cw
                    else:
                        line_w += cw
            return max(1, total)

        def _split_to_fit(s: str, avail_lines: int) -> tuple[str, str]:
            sentence_ends = [i + 1 for i, ch in enumerate(s) if ch == "."]
            if not sentence_ends:
                return "", s
            best_cut = None
            for end_idx in sentence_ends:
                chunk = s[:end_idx]
                if _count_wrapped_lines(chunk) <= avail_lines:
                    best_cut = end_idx
                else:
                    break
            if best_cut is None:
                return "", s
            return s[:best_cut], s[best_cut:].lstrip()

        def _draw_text_flowing(full_text: str, is_bullet: bool = False) -> None:
            _just_broke_page[0] = False
            full_text = full_text.replace("\n", " ").replace("\r", "").strip()
            self.set_font("KR", "", 18)
            text_w = (width - 8) if is_bullet else width
            remaining = full_text

            while remaining:
                avail_lines = max(1, int((PAGE_BOTTOM - self.get_y()) // line_h))
                total_lines = _count_wrapped_lines(remaining)
                if total_lines <= avail_lines:
                    chunk     = remaining
                    remaining = ""
                else:
                    chunk, remaining = _split_to_fit(remaining, avail_lines)

                if not chunk:
                    _new_content_page_tracked()
                    _just_broke_page[0] = False
                    continue

                self.set_font("KR", "", 18)
                self.set_stretching(95)
                self.set_char_spacing(-0.3)
                self._text_color(C_TEXT_DARK)

                if is_bullet:
                    self._fill(C_GOLD)
                    self.ellipse(x + 1, self.get_y() + 4.5, 3, 3, style="F")
                    self.set_x(x + 8)
                    self.multi_cell(
                        width - 8, line_h, chunk,
                        new_x=XPos.LMARGIN, new_y=YPos.NEXT,
                    )
                else:
                    self.set_x(x)
                    self.multi_cell(
                        width, line_h, chunk,
                        new_x=XPos.LMARGIN, new_y=YPos.NEXT,
                    )

                if remaining:
                    _new_content_page_tracked()
                    _just_broke_page[0] = False
            self.set_char_spacing(0)

        for btype, content in blocks:
            if btype == "blank":
                _just_broke_page[0] = False
                if self.get_y() + 5 <= PAGE_BOTTOM:
                    self.ln(5)

            elif btype == "h1":
                content = strip_markdown(content)
                _ensure_space(6 + _estimate_lines(content, 25) * line_h + 3)
                self.ln(6)
                self.set_font("KR", "B", 18)
                self._text_color(C_CHARCOAL)
                self.set_x(x)
                self.multi_cell(width, line_h, content, align="L",
                                new_x=XPos.LMARGIN, new_y=YPos.NEXT)
                self.ln(3)

            elif btype == "h2":
                content = strip_markdown(content)
                _ensure_space(5 + _estimate_lines(content, 25) * line_h + 3 + line_h * 2)
                self.ln(5)
                self._fill(C_GOLD)
                self.rect(x, self.get_y() + 2, 4, line_h - 4, style="F")
                self.set_font("KR", "B", 18)
                self._text_color(C_CHARCOAL)
                self.set_x(x + 10)
                self.multi_cell(width - 10, line_h, content, align="L",
                                new_x=XPos.LMARGIN, new_y=YPos.NEXT)
                self.ln(3)

            elif btype == "h3":
                content = strip_markdown(content)
                _ensure_space(10 + _estimate_lines(content, 28) * line_h + 2)
                self.ln(10)
                self.set_font("KR", "B", 18)
                self._text_color(C_ACCENT)
                self.set_x(x)
                self.multi_cell(width, line_h, content, align="L",
                                new_x=XPos.LMARGIN, new_y=YPos.NEXT)
                self.ln(3)

            elif btype == "bold_line":
                content = strip_markdown(content)
                _just_broke_page[0] = False
                _ensure_space(_estimate_lines(content, 28) * line_h + 2)
                self.set_font("KR", "B", 18)
                self._text_color(C_CHARCOAL)
                self.set_x(x)
                self.multi_cell(width, line_h, content.lstrip(),
                                new_x=XPos.LMARGIN, new_y=YPos.NEXT)
                self.ln(2)

            elif btype == "bullet":
                _draw_text_flowing(strip_markdown(content), is_bullet=True)
                self.ln(1)

            else:  # text
                _draw_text_flowing(strip_markdown(content))

        self.set_left_margin(0)
        self.set_right_margin(0)
