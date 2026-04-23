"""
PDF 생성 모듈 (fpdf2 기반 - Windows 호환)
"""

import os
import re
import json
import sys
from datetime import datetime
from fpdf import FPDF
from fpdf.enums import XPos, YPos

if sys.stdout.encoding and sys.stdout.encoding.lower() not in ('utf-8', 'utf8'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# ── 색상 팔레트 ───────────────────────────────────────────────────────────────
C_CHARCOAL    = (44,  62,  80)
C_GOLD        = (212, 175, 55)
C_OFFWHITE    = (248, 248, 248)
C_WHITE       = (255, 255, 255)
C_TEXT_DARK   = (51,  51,  51)
C_TEXT_MID    = (100, 116, 139)
C_TEXT_LIGHT  = (148, 163, 184)
C_CARD_BG     = (255, 255, 255)
C_CARD_BORDER = (226, 232, 240)
C_ACCENT      = (74,  85, 104)

C_WOOD  = (129, 199, 132)
C_FIRE  = (239, 154, 154)
C_EARTH = (255, 224, 130)
C_METAL = (238, 238, 238)
C_WATER = (144, 164, 174)

ELEMENT_COLORS = {
    "목": C_WOOD,  "화": C_FIRE,  "토": C_EARTH,
    "금": C_METAL, "수": C_WATER,
    "木": C_WOOD,  "火": C_FIRE,  "土": C_EARTH,
    "金": C_METAL, "水": C_WATER,
}

FONT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts")


# ── 날짜 헬퍼 ─────────────────────────────────────────────────────────────────
def _today_str() -> str:
    now = datetime.now()
    return f"{now.year}. {now.month:02d}. {now.day:02d}."


# ── 유틸 ──────────────────────────────────────────────────────────────────────
def strip_markdown(text: str) -> str:
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
    text = re.sub(r'\*(.+?)\*',     r'\1', text)
    text = re.sub(r'^#{1,6}\s+',    '',    text, flags=re.MULTILINE)
    return text.strip()


def parse_markdown_blocks(text: str):
    blocks = []
    for line in text.split('\n'):
        stripped = line.strip()
        if re.match(r'^-{2,}$', stripped) or re.match(r'^_{2,}$', stripped) or re.match(r'^\*{2,}$', stripped):
            continue
        if line.startswith('### '):
            blocks.append(('h3', line[4:].strip()))
        elif line.startswith('## '):
            blocks.append(('h2', line[3:].strip()))
        elif line.startswith('# '):
            blocks.append(('h1', line[2:].strip()))
        elif line.startswith('- ') or line.startswith('* '):
            blocks.append(('bullet', line[2:].strip()))
        elif line.startswith('**') and line.endswith('**') and len(line) > 4:
            blocks.append(('bold_line', line[2:-2].strip()))
        elif stripped == '':
            blocks.append(('blank', ''))
        else:
            blocks.append(('text', stripped))
    return blocks


def _pillar_ganji(pillar: dict) -> str:
    return pillar["간지"]["천간"] + pillar["간지"]["지지"]

def _pillar_ji_elem(pillar: dict) -> str:
    return pillar["지지"]["오행"]

def _pillar_ji_ss(pillar: dict) -> str:
    return pillar["지지"]["십성"]["값"]

def _pillar_ji_12(pillar: dict) -> str:
    return pillar["지지"]["12운성"]

def _pillar_ji_sal(pillar: dict) -> str:
    sal = pillar["지지"]["신살"]
    return "/".join(sal) if sal else "-"

def _pillar_gan_ss(pillar: dict) -> str:
    return pillar["천간"]["십성"]["값"]

def _pillar_gan_elem(pillar: dict) -> str:
    return pillar["천간"]["오행"]


# ── 신강신약 한자 제거 헬퍼 ───────────────────────────────────────────────────
def _clean_strength(text: str) -> str:
    return re.sub(r'\([^)]*\)', '', text).strip()


# ── 메인 PDF 클래스 ──────────────────────────────────────────────────────────
class SajuPDF(FPDF):

    def __init__(self):
        super().__init__(orientation='P', unit='mm', format='A4')
        self.set_auto_page_break(auto=False)
        self._register_fonts()
        self.set_margins(0, 0, 0)
        self._page_num_enabled = False
        self._section_counter = 0
        self._current_section_title = ''

    def _register_fonts(self):
        self.add_font('KR',       '',  os.path.join(FONT_DIR, 'NanumGothic.ttf'))
        self.add_font('KR',       'B', os.path.join(FONT_DIR, 'NanumGothicBold.ttf'))
        self.add_font('KR-Light', '',  os.path.join(FONT_DIR, 'NanumGothicLight.ttf'))
        self.add_font('KR-Med',   '',  os.path.join(FONT_DIR, 'NanumGothic.ttf'))

    def header(self): pass

    def footer(self):
        if not self._page_num_enabled:
            return
        if self.page <= 2:
            return
        self.set_y(-14)
        self.set_font('KR-Light', '', 9)
        self.set_text_color(*C_TEXT_LIGHT)
        self.cell(0, 8, f'- {self.page - 2} -', align='C')

    # ── 헬퍼 ──────────────────────────────────────────────────────────────────
    def _fill(self, rgb):           self.set_fill_color(*rgb)
    def _stroke(self, rgb):         self.set_draw_color(*rgb)
    def _text_color(self, rgb):     self.set_text_color(*rgb)

    def get_text_color(self, bg):
        return (90, 90, 90)

    def _rounded_rect_v2(self, x, y, w, h, r=4):
        try:
            self.rect(x, y, w, h, style='FD', round_corners=True, corner_radius=r)
        except TypeError:
            self.rect(x, y, w, h, style='FD')

    def _divider(self, x, y, w, color=C_GOLD, thickness=0.5):
        self.set_draw_color(*color)
        self.set_line_width(thickness)
        self.line(x, y, x + w, y)
        self.set_line_width(0.2)

    def _section_title(self, title: str, x=20):
        y = self.get_y()
        self.set_xy(x, y)
        self.set_font('KR', 'B', 17)
        self._text_color(C_CHARCOAL)
        self.cell(0, 8, title, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        bar_y = self.get_y() + 1
        self._fill(C_GOLD); self._stroke(C_GOLD)
        self.rect(x, bar_y, 30, 2, style='F')
        self.ln(6)

    # ── 마크다운 렌더러 ───────────────────────────────────────────────────────
    def _render_markdown(self, text: str, x=20, width=170, line_h=15):
        PAGE_BOTTOM  = 235
        CHARS_PER_LINE = 33

        blocks = parse_markdown_blocks(text)
        self.set_left_margin(x)
        self.set_right_margin(210 - x - width)

        def _new_content_page():
            self.add_page()
            self._fill(C_OFFWHITE)
            self.rect(0, 0, 210, 297, style='F')
            if self._current_section_title:
                # 연속 페이지: 번호 카운트 없이 현재 번호 재사용
                self._draw_section_header(
                    self._current_section_title,
                    section_num=self._section_counter
                )
            self.set_left_margin(x)
            self.set_right_margin(210 - x - width)

        def _estimate_lines(content: str, chars_per_line: int = 30) -> int:
            if not content:
                return 1
            return max(1, (len(content) // chars_per_line) + 1)

        _just_broke_page = [False]

        def _new_content_page_tracked():
            _new_content_page()
            _just_broke_page[0] = True

        def _ensure_space(needed_mm: float):
            if _just_broke_page[0]:
                _just_broke_page[0] = False
                return
            if self.get_y() + needed_mm > PAGE_BOTTOM:
                _new_content_page_tracked()

        def _draw_text_flowing(full_text: str, is_bullet: bool = False):
            _just_broke_page[0] = False
            self.set_font('KR', '', 18)
            text_w = (width - 8) if is_bullet else width

            def _count_wrapped_lines(s: str) -> int:
                total = 0
                for raw_line in s.split('\n'):
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

            def _split_to_fit(s: str, avail_lines: int):
                sentence_ends = [i + 1 for i, ch in enumerate(s) if ch in '.。!！?？']
                if not sentence_ends:
                    return s, ''
                best_cut = None
                for end_idx in sentence_ends:
                    chunk = s[:end_idx]
                    if _count_wrapped_lines(chunk) <= avail_lines:
                        best_cut = end_idx
                    else:
                        break
                if best_cut is None:
                    best_cut = sentence_ends[0]
                return s[:best_cut], s[best_cut:].lstrip()

            remaining = full_text
            while remaining:
                avail_lines = max(1, int((PAGE_BOTTOM - self.get_y()) // line_h))
                total_lines = _count_wrapped_lines(remaining)
                if total_lines <= avail_lines:
                    chunk = remaining
                    remaining = ''
                else:
                    chunk, remaining = _split_to_fit(remaining, avail_lines)

                self.set_font('KR', '', 18)
                self._text_color(C_TEXT_DARK)

                if is_bullet:
                    self._fill(C_GOLD)
                    self.ellipse(x + 1, self.get_y() + 4.5, 3, 3, style='F')
                    self.set_x(x + 8)
                    self.multi_cell(width - 8, line_h, chunk,
                                    new_x=XPos.LMARGIN, new_y=YPos.NEXT)
                else:
                    self.set_x(x)
                    self.multi_cell(width, line_h, chunk,
                                    new_x=XPos.LMARGIN, new_y=YPos.NEXT)

                if remaining:
                    _new_content_page_tracked()
                    _just_broke_page[0] = False

        for btype, content in blocks:

            if btype == 'blank':
                _just_broke_page[0] = False
                if self.get_y() + 5 <= PAGE_BOTTOM:
                    self.ln(5)

            elif btype == 'h1':
                content = strip_markdown(content)
                lines = _estimate_lines(content, 25)
                _ensure_space(6 + lines * line_h + 3)
                self.ln(6)
                self.set_font('KR', 'B', 18)
                self._text_color(C_CHARCOAL)
                self.set_x(x)
                self.multi_cell(width, line_h, content, align='L',
                                new_x=XPos.LMARGIN, new_y=YPos.NEXT)
                self.ln(3)

            elif btype == 'h2':
                content = strip_markdown(content)
                lines = _estimate_lines(content, 25)
                _ensure_space(5 + lines * line_h + 3)
                self.ln(5)
                self._fill(C_GOLD)
                self.rect(x, self.get_y() + 2, 4, line_h - 4, style='F')
                self.set_font('KR', 'B', 18)
                self._text_color(C_CHARCOAL)
                self.set_x(x + 10)
                self.multi_cell(width - 10, line_h, content, align='L',
                                new_x=XPos.LMARGIN, new_y=YPos.NEXT)
                self.ln(3)

            elif btype == 'h3':
                content = strip_markdown(content)
                lines = _estimate_lines(content, 28)
                _ensure_space(10 + lines * line_h + 2)
                self.ln(10)
                self.set_font('KR', 'B', 18)
                self._text_color(C_ACCENT)
                self.set_x(x)
                self.multi_cell(width, line_h, content, align='L',
                                new_x=XPos.LMARGIN, new_y=YPos.NEXT)
                self.ln(3)

            elif btype == 'bold_line':
                content = strip_markdown(content)
                _just_broke_page[0] = False
                lines = _estimate_lines(content, 28)
                _ensure_space(lines * line_h + 2)
                self.set_font('KR', 'B', 18)
                self._text_color(C_CHARCOAL)
                self.set_x(x)
                self.multi_cell(width, line_h, content.lstrip(),
                                new_x=XPos.LMARGIN, new_y=YPos.NEXT)
                self.ln(2)

            elif btype == 'bullet':
                _draw_text_flowing(strip_markdown(content), is_bullet=True)
                self.ln(1)

            else:  # text
                _draw_text_flowing(strip_markdown(content))

        self.set_left_margin(0)
        self.set_right_margin(0)

    # ══════════════════════════════════════════════════════════════════════════
    # 1. 표지
    # ══════════════════════════════════════════════════════════════════════════
    def add_cover(self, saju_data: dict, today: str):
        self.add_page()
        name   = saju_data['기본정보']['이름']
        birth  = saju_data['기본정보'].get('생년월일', '')
        gender = saju_data['기본정보']['성별']
        ilju   = saju_data['사주원국']['일주']['간지']
        strength_raw = saju_data['일간정보']['신강신약']
        strength = _clean_strength(strength_raw)

        self._fill(C_CHARCOAL)
        self.rect(0, 0, 210, 297, style='F')

        for alpha, size in [(15, 120), (8, 80)]:
            self.set_fill_color(min(255, C_CHARCOAL[0]+alpha),
                                min(255, C_CHARCOAL[1]+alpha),
                                min(255, C_CHARCOAL[2]+alpha))
            self.ellipse(150, -20, size, size, style='F')

        self._fill(C_GOLD)
        self.rect(0, 0, 210, 3, style='F')

        badge_y = 50
        self.set_font('KR-Light', '', 14)
        self._text_color(C_GOLD)
        self.set_x(0); self.set_y(badge_y)
        self.cell(210, 6, '*  사주명리 전문 분석 리포트  *', align='C')

        self.set_font('KR', 'B', 72)
        self._text_color(C_WHITE)
        self.set_y(badge_y + 14)
        self.cell(210, 40, '命', align='C')

        self.set_font('KR-Light', '', 14)
        self._text_color((180, 180, 200))
        self.set_y(badge_y + 54)
        self.cell(210, 8, '나의 운명을 읽는 지혜', align='C')

        self._divider(60, badge_y + 66, 90, C_GOLD, 0.8)

        self.set_font('KR', 'B', 28)
        self._text_color(C_GOLD)
        self.set_y(badge_y + 74)
        self.cell(210, 14, f'{name} 님', align='C')

        self.set_font('KR-Light', '', 12)
        self._text_color((210, 210, 225))
        self.set_y(badge_y + 90)
        self.cell(210, 8, f'생년월일: {birth}     성별: {gender}', align='C')

        box_x, box_w, box_h = 70, 70, 42
        box_y = badge_y + 108
        self.set_fill_color(60, 80, 100)
        self.set_draw_color(*C_GOLD)
        self.set_line_width(0.8)
        self._rounded_rect_v2(box_x, box_y, box_w, box_h, 5)
        self.set_line_width(0.2)

        self.set_font('KR-Light', '', 12)
        self._text_color(C_GOLD)
        self.set_xy(box_x, box_y + 4)
        self.cell(box_w, 5, '일주 (핵심 기둥)', align='C')

        self.set_font('KR', 'B', 28)
        self._text_color(C_WHITE)
        self.set_xy(box_x, box_y + 10)
        self.cell(box_w, 20, ilju, align='C')

        self.set_font('KR', '', 12)
        self._text_color((180, 200, 220))
        self.set_xy(box_x, box_y + 32)
        self.cell(box_w, 7, strength, align='C')

        self.set_font('KR-Light', '', 9)
        self._text_color((100, 100, 120))
        self.set_y(280)
        self.cell(210, 6, f'{today}   |   사주 분석', align='C')

        self._fill(C_GOLD)
        self.rect(0, 294, 210, 3, style='F')

    # ══════════════════════════════════════════════════════════════════════════
    # 2. 목차
    # ══════════════════════════════════════════════════════════════════════════
    def add_toc(self, toc_entries: list):
        self.add_page()
        self._fill(C_OFFWHITE)
        self.rect(0, 0, 210, 297, style='F')

        self._fill(C_CHARCOAL)
        self.rect(0, 0, 210, 42, style='F')
        self._fill(C_GOLD)
        self.rect(0, 42, 210, 2, style='F')

        self.set_font('KR-Light', '', 10)
        self._text_color(C_GOLD)
        self.set_xy(0, 14)
        self.cell(210, 6, 'TABLE OF CONTENTS', align='C')

        self.set_font('KR', 'B', 22)
        self._text_color(C_WHITE)
        self.set_xy(0, 22)
        self.cell(210, 10, '목   차', align='C')

        start_y = 60
        for i, entry in enumerate(toc_entries):
            title = entry[0]

            item_y = start_y + i * 20
            if item_y > 270:
                break

            if i % 2 == 0:
                self._fill((240, 242, 245))
                self.rect(20, item_y - 1, 170, 16, style='F')

            self._fill(C_CHARCOAL)
            self.ellipse(22, item_y + 1, 12, 12, style='F')
            self.set_font('KR', 'B', 17)
            self._text_color(C_GOLD)
            self.set_xy(22, item_y + 3)
            self.cell(12, 8, str(i + 1), align='C')

            self.set_font('KR-Med', '', 17)
            self._text_color(C_CHARCOAL)
            self.set_xy(38, item_y + 3)
            self.cell(150, 8, title)

        self._divider(20, 278, 170, C_GOLD, 0.5)
        self.set_font('KR-Light', '', 9)
        self._text_color(C_TEXT_LIGHT)
        self.set_xy(0, 281)
        self.cell(210, 6, '사주 분석 시스템', align='C')

    # ══════════════════════════════════════════════════════════════════════════
    # 3. 섹션 페이지 헤더
    # ══════════════════════════════════════════════════════════════════════════
    def _draw_section_header(self, section_title: str, section_num: int = 0):
        self._fill(C_CHARCOAL)
        self.rect(0, 0, 210, 28, style='F')
        self._fill(C_GOLD)
        self.rect(0, 28, 210, 1.5, style='F')
        display_title = f"{section_num}. {section_title}" if section_num > 0 else section_title
        self.set_font('KR', 'B', 16)
        self._text_color(C_WHITE)
        self.set_xy(20, 9)
        self.cell(150, 10, display_title)
        self.set_font('KR-Light', '', 14)
        self._text_color(C_GOLD)
        self.set_xy(150, 10)
        self.cell(40, 8, '사주 분석', align='R')
        self.set_y(45)

    def _start_content_page(self, section_title: str, auto_number: bool = True):
        self._current_section_title = section_title
        if auto_number:
            self._section_counter += 1
        self.add_page()
        self._fill(C_OFFWHITE)
        self.rect(0, 0, 210, 297, style='F')
        self._draw_section_header(section_title, section_num=self._section_counter)
        self.set_left_margin(20)
        self.set_right_margin(20)

    # ══════════════════════════════════════════════════════════════════════════
    # 4-A. 사주 원국 페이지 (프리미엄용 전체 데이터)
    # ══════════════════════════════════════════════════════════════════════════
    def add_saju_chart(self, saju_data: dict):
        self._start_content_page('사주 원국 및 기본 데이터')

        pillars  = ['연주', '월주', '일주', '시주']
        card_w, card_h = 38, 52
        start_x = 17
        gap = 4

        for i, p in enumerate(pillars):
            px = start_x + i * (card_w + gap)
            py = self.get_y()
            data   = saju_data['사주원국'][p]
            stem   = data['천간']
            branch = data['지지']
            is_day = (p == '일주')

            if is_day:
                self._fill(C_CHARCOAL); self._stroke(C_GOLD)
                self.set_line_width(1.0)
            else:
                self._fill(C_WHITE); self._stroke(C_CARD_BORDER)
                self.set_line_width(0.3)
            self._rounded_rect_v2(px, py, card_w, card_h, 4)
            self.set_line_width(0.2)

            self.set_font('KR-Light', '', 8)
            self._text_color(C_GOLD if is_day else C_TEXT_LIGHT)
            self.set_xy(px, py + 5)
            self.cell(card_w, 5, p, align='C')

            self.set_font('KR', 'B', 24)
            self._text_color(C_WHITE if is_day else C_CHARCOAL)
            self.set_xy(px, py + 12)
            self.cell(card_w, 14, stem, align='C')

            self._divider(px + 6, py + 26, card_w - 12,
                          C_GOLD if is_day else C_CARD_BORDER, 0.3)

            self.set_font('KR', 'B', 24)
            self._text_color(C_WHITE if is_day else C_CHARCOAL)
            self.set_xy(px, py + 28)
            self.cell(card_w, 14, branch, align='C')

            if is_day:
                self.set_font('KR-Light', '', 7)
                self._text_color(C_GOLD)
                self.set_xy(px, py + 44)
                self.cell(card_w, 6, '일주', align='C')

        self.set_y(self.get_y() + card_h + 8)

        strength_display = _clean_strength(saju_data['일간정보']['신강신약'])
        info_items = [
            ('일간 (나의 본질)',
             f"{saju_data['일간정보']['일간']} ({saju_data['일간정보']['오행']} · {saju_data['일간정보'].get('음양', '')})"),
            ('신강/신약', strength_display),
            ('음력 생년월일', saju_data['기본정보'].get('음력', '')),
            ('신살', ', '.join(saju_data.get('신살', ['없음']))),
        ]
        iw, ih = 82, 20
        for idx, (label, val) in enumerate(info_items):
            ix = 17 + (idx % 2) * (iw + 7)
            iy = self.get_y() + (idx // 2) * (ih + 4)
            self._fill(C_WHITE); self._stroke(C_CARD_BORDER)
            self.set_line_width(0.2)
            self._rounded_rect_v2(ix, iy, iw, ih, 3)
            self.set_font('KR-Light', '', 8)
            self._text_color(C_TEXT_LIGHT)
            self.set_xy(ix + 4, iy + 3)
            self.cell(iw - 8, 5, label)
            self.set_font('KR', '', 10)
            self._text_color(C_CHARCOAL)
            self.set_xy(ix + 4, iy + 10)
            self.cell(iw - 8, 7, val)

        self.set_y(self.get_y() + 2 * (ih + 4) + 6)

        self.set_font('KR', 'B', 11)
        self._text_color(C_CHARCOAL)
        self.set_x(17)
        self.cell(0, 6, '오행 분포', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.ln(1)

        elements = saju_data['오행분포']
        total = max(sum(elements.values()), 1)
        bar_x = 17
        ew, eg = 32, 4
        for ei, ek in enumerate(['목', '화', '토', '금', '수']):
            val   = elements.get(ek, 0)
            ex    = bar_x + ei * (ew + eg)
            ey    = self.get_y()
            color = ELEMENT_COLORS.get(ek, C_TEXT_MID)
            self._fill((220, 225, 230))
            self.rect(ex, ey, ew, 10, style='F')
            if val > 0:
                bar_fill_w = int(ew * val / max(total, 8))
                self._fill(color)
                self.rect(ex, ey, max(bar_fill_w, 3), 10, style='F')
            self.set_font('KR', 'B', 9)
            self._text_color(C_WHITE)
            self.set_xy(ex + 2, ey + 1)
            self.cell(ew - 4, 8, f'{ek}  {val}')

        self.set_y(self.get_y() + 16)

        if '십성' in saju_data:
            self.set_font('KR', 'B', 11)
            self._text_color(C_CHARCOAL)
            self.set_x(17)
            self.cell(0, 6, '십성 구성', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            self.ln(1)

            sipsung = saju_data['십성']
            cols    = list(sipsung.items())
            tw      = 171
            cw      = tw // max(len(cols), 1)

            self._fill(C_CHARCOAL)
            self.rect(17, self.get_y(), tw, 9, style='F')
            self.set_font('KR-Light', '', 8)
            self._text_color(C_GOLD)
            for ci, (pos, _) in enumerate(cols):
                self.set_xy(17 + ci * cw, self.get_y())
                self.cell(cw, 9, pos, align='C')
            self.ln(9)

            self._fill(C_WHITE); self._stroke(C_CARD_BORDER)
            self.rect(17, self.get_y(), tw, 10, style='FD')
            self.set_font('KR', '', 9)
            self._text_color(C_CHARCOAL)
            for ci, (_, val) in enumerate(cols):
                self.set_xy(17 + ci * cw, self.get_y())
                self.cell(cw, 10, val, align='C')
            self.ln(14)

        if '대운' in saju_data:
            if self.get_y() > 220:
                self._start_content_page('사주 원국 및 기본 데이터')

            self.set_font('KR', 'B', 11)
            self._text_color(C_CHARCOAL)
            self.set_x(17)
            self.cell(0, 6, '대운 흐름', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            self.ln(1)

            headers  = ['시기',    '간지', '천간오행', '지지오행', '12운성', '신살']
            col_ws   = [38,        22,      22,         22,         22,        43]

            self._fill(C_CHARCOAL)
            self.rect(17, self.get_y(), 171, 9, style='F')
            self.set_font('KR-Light', '', 8)
            self._text_color(C_GOLD)
            cx = 17
            for hw, hd in zip(col_ws, headers):
                self.set_xy(cx, self.get_y())
                self.cell(hw, 9, hd, align='C')
                cx += hw
            self.ln(9)

            for di, d in enumerate(saju_data['대운'][:8]):
                ry = self.get_y()
                if ry > 268:
                    self._start_content_page('사주 원국 및 기본 데이터')
                    ry = self.get_y()
                bg = (248, 248, 252) if di % 2 == 0 else C_WHITE
                self._fill(bg); self._stroke(C_CARD_BORDER)
                self.set_line_width(0.15)
                self.rect(17, ry, 171, 9, style='FD')

                ganji    = _pillar_ganji(d)
                ji_elem  = _pillar_ji_elem(d)
                gan_elem = _pillar_gan_elem(d)
                ji_12    = _pillar_ji_12(d)
                sal      = _pillar_ji_sal(d)

                row_vals = [
                    f"{d['시작나이']}~{d['시작나이']+9}세",
                    ganji, gan_elem, ji_elem, ji_12, sal,
                ]
                cx = 17
                for ci, (hw, rv) in enumerate(zip(col_ws, row_vals)):
                    self.set_xy(cx, ry)
                    if ci in (2, 3):
                        ec = ELEMENT_COLORS.get(rv, C_TEXT_MID)
                        self._text_color(ec)
                        self.set_font('KR', 'B', 9)
                    elif ci == 5:
                        self._text_color(C_FIRE if rv != '-' else C_TEXT_LIGHT)
                        self.set_font('KR', '', 8)
                    else:
                        self._text_color(C_TEXT_DARK)
                        self.set_font('KR', '', 9)
                    self.cell(hw, 9, rv, align='C')
                    cx += hw
                self.ln(9)

    # ══════════════════════════════════════════════════════════════════════════
    # 4-B. 사주 원국 (기본/프리미엄 공용)
    # ══════════════════════════════════════════════════════════════════════════
    def add_saju_intro(self, saju_data: dict):
        """
        레이아웃:
          [상단] 만세력 표 — 시주·일주·월주·연주 4열
                 행 순서: 라벨 / 십성(천간) / 천간 한자 / 지지 한자 / 십성(지지) / 12운성
          [하단] 오행 분포 — 세로 나열, 한자 원형 아이콘 + 한글명 + 가로 바 + 레이블(균형/과다/부족)
        """
        self._start_content_page('사주 원국')

        origin   = saju_data['사주원국']
        sipsung  = saju_data.get('십성', {})
        i12      = saju_data.get('십이운성', {})

        # 열 순서: 시주 → 일주 → 월주 → 연주
        PILLAR_ORDER = ['시주', '일주', '월주', '연주']
        PILLAR_LABEL = {
            '시주': '시주',
            '일주': '일주',
            '월주': '월주',
            '연주': '연주',
        }
        # 십성 키 매핑 (최상위 십성 dict 기준)
        SS_GAN = {'시주': '시간', '일주': None,  '월주': '월간', '연주': '연간'}
        SS_JI  = {'시주': '시지', '일주': '일지', '월주': '월지', '연주': '연지'}
        # 십이운성 키 매핑
        I12_KEY = {'시주': '시지', '일주': '일지', '월주': '월지', '연주': '연지'}

        # ── 천간/지지 오행 색상 매핑 ──────────────────────────────────────
        GAN_COLOR = {
            '甲': C_WOOD,  '乙': C_WOOD,
            '丙': C_FIRE,  '丁': C_FIRE,
            '戊': C_EARTH, '己': C_EARTH,
            '庚': C_METAL, '辛': C_METAL,
            '壬': C_WATER, '癸': C_WATER,
        }
        JI_COLOR = {
            '寅': C_WOOD,  '卯': C_WOOD,
            '巳': C_FIRE,  '午': C_FIRE,
            '申': C_METAL, '酉': C_METAL,
            '亥': C_WATER, '子': C_WATER,
            '辰': C_EARTH, '丑': C_EARTH, '未': C_EARTH, '戌': C_EARTH,
        }

        # ── 만세력 표 ─────────────────────────────────────────────────────
        LBL_W  = 28          # 왼쪽 행 라벨 열 너비
        COL_W  = 40          # 각 주 열 너비
        GAP    = 2
        TABLE_W = LBL_W + 4 * COL_W + 4 * GAP
        TABLE_X = (210 - TABLE_W) / 2
        TOP_Y   = self.get_y()

        ROW_H_LABEL  = 12    # 주 라벨 행
        ROW_H_SS     = 14    # 십성 행
        ROW_H_HANJA  = 22    # 천간·지지 한자 행
        ROW_H_I12    = 14    # 12운성 행

        def _col_x(ci: int) -> float:
            return TABLE_X + LBL_W + GAP + ci * (COL_W + GAP)

        # ── 헤더 행: 주 라벨 ─────────────────────────────────────────────
        cy = TOP_Y
        # 왼쪽 라벨 셀 (빈칸)
        self._fill(C_CHARCOAL)
        self.rect(TABLE_X, cy, LBL_W, ROW_H_LABEL, style='F')

        for ci, pkey in enumerate(PILLAR_ORDER):
            cx     = _col_x(ci)
            is_day = (pkey == '일주')
            # 배경: 모든 열 동일하게 C_CHARCOAL
            self._fill(C_CHARCOAL)
            self._stroke(C_CHARCOAL)
            self.set_line_width(0.2)
            self.rect(cx, cy, COL_W, ROW_H_LABEL, style='F')   # 배경만 채움(테두리 없음)

            if is_day:
                # 금색 테두리: 4면 전체
                self._stroke(C_GOLD)
                self.set_line_width(1.0)
                self.line(cx,           cy,                cx + COL_W, cy)                # 상단
                self.line(cx,           cy,                cx,          cy + ROW_H_LABEL) # 좌
                self.line(cx + COL_W,   cy,                cx + COL_W,  cy + ROW_H_LABEL) # 우
                self.line(cx,           cy + ROW_H_LABEL,  cx + COL_W,  cy + ROW_H_LABEL) # 하단
                self.set_line_width(0.2)

            self.set_font('KR', '', 13)   # 헤더 라벨 폰트
            self._text_color(C_GOLD if is_day else (180, 190, 205))
            self.set_xy(cx, cy + 1.5)
            self.cell(COL_W, ROW_H_LABEL - 2, PILLAR_LABEL[pkey], align='C')

        cy += ROW_H_LABEL

        # ── 행 그리기 헬퍼 ───────────────────────────────────────────────
        def _draw_row(row_h: float, row_label: str,
                      values: list, font_size: float = 9,
                      bold: bool = False, value_colors: list = None):
            """
            row_label    : 왼쪽 라벨
            values       : 4개 값 리스트 (시·일·월·연 순)
            value_colors : 각 열 텍스트 색상 (None이면 기본)
            """
            nonlocal cy
            # 왼쪽 라벨 셀
            self._fill((235, 237, 243))
            self._stroke(C_CARD_BORDER)
            self.set_line_width(0.15)
            self.rect(TABLE_X, cy, LBL_W, row_h, style='FD')
            self.set_font('KR', '', 13)   # 라벨 폰트
            self._text_color(C_TEXT_MID)
            self.set_xy(TABLE_X, cy + (row_h - 11) / 2)
            self.cell(LBL_W, 11, row_label, align='C')

            for ci, (pkey, val) in enumerate(zip(PILLAR_ORDER, values)):
                cx     = _col_x(ci)
                is_day = (pkey == '일주')
                # 한자 행 여부 판단
                is_hanja_row = (font_size >= 20)

                # 배경 설정
                if is_hanja_row and value_colors:
                    fill_color = value_colors[ci]   # 오행 색을 배경으로
                else:
                    fill_color = (245, 246, 250) if ci % 2 == 0 else C_WHITE
                self._fill(fill_color)
                self._stroke(C_CARD_BORDER)
                self.set_line_width(0.15)
                self.rect(cx, cy, COL_W, row_h, style='FD')
                self.set_line_width(0.2)

                # 텍스트 색상
                if is_hanja_row and value_colors:
                    tc = self.get_text_color(fill_color)
                else:
                    tc = C_TEXT_DARK
                fstyle = 'B' if bold else ''
                self.set_font('KR', fstyle, font_size)
                self._text_color(tc)
                self.set_xy(cx, cy + (row_h - font_size * 0.4) / 2)
                self.cell(COL_W, font_size * 0.4 + 1, val, align='C')

            cy += row_h

        # 십성(천간) 행
        ss_gan_vals = [
            sipsung.get(SS_GAN[p], '일간') if SS_GAN[p] else '일간(나)'
            for p in PILLAR_ORDER
        ]
        _draw_row(ROW_H_SS, '십성\n(천간)', ss_gan_vals, font_size=15)

        # 천간 한자 행 — 오행 색상 적용
        gan_vals   = [origin[p]['천간'] for p in PILLAR_ORDER]
        gan_colors = [GAN_COLOR.get(v, C_TEXT_DARK) for v in gan_vals]
        _draw_row(ROW_H_HANJA, '천  간', gan_vals, font_size=23, bold=True,
                  value_colors=gan_colors)

        # 지지 한자 행 — 오행 색상 적용
        ji_vals   = [origin[p]['지지'] for p in PILLAR_ORDER]
        ji_colors = [JI_COLOR.get(v, C_TEXT_DARK) for v in ji_vals]
        _draw_row(ROW_H_HANJA, '지  지', ji_vals, font_size=23, bold=True,
                  value_colors=ji_colors)

        # 십성(지지) 행
        ss_ji_vals = [sipsung.get(SS_JI[p], '') for p in PILLAR_ORDER]
        _draw_row(ROW_H_SS, '십성\n(지지)', ss_ji_vals, font_size=15)

        # 12운성 행
        i12_vals = [i12.get(I12_KEY[p], '-') for p in PILLAR_ORDER]
        _draw_row(ROW_H_I12, '12운성', i12_vals, font_size=15)

        # 일주 컬럼 전체 테두리
        day_col_index = 1
        cx = _col_x(day_col_index)

        table_height = (
            ROW_H_LABEL +
            ROW_H_SS +
            ROW_H_HANJA +
            ROW_H_HANJA +
            ROW_H_SS +
            ROW_H_I12
        )

        self._stroke(C_GOLD)
        self.set_line_width(1.2)
        self.rect(cx, TOP_Y, COL_W, table_height)
        self.set_line_width(0.2)

        self.set_y(cy + 16)

        # ── 오행 분포 (세로 나열) ─────────────────────────────────────────
        ELEM_META = [
            ('목', '木', '나무', C_WOOD),
            ('화', '火', '불',   C_FIRE),
            ('토', '土', '흙',   C_EARTH),
            ('금', '金', '금',   C_METAL),
            ('수', '水', '물',   C_WATER),
        ]
        elements = saju_data.get('오행분포', {})
        total    = max(sum(elements.values()), 1)

        # 개수 → (상태 레이블, 채우기 비율) 매핑
        def _elem_status(val: int):
            if val == 0:   return ('부족', 0.00)
            elif val == 1: return ('약함', 0.20)
            elif val == 2: return ('균형', 0.40)
            elif val == 3: return ('강함', 0.60)
            elif val == 4: return ('과다', 0.80)
            else:          return ('극단', 1.00)

        # 섹션 제목
        self.set_font('KR', 'B', 17)
        self._text_color(C_CHARCOAL)
        self.set_x(TABLE_X)
        self.cell(0, 9, '오행 분포도', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.ln(8)

        ICON_R   = 8      # 원형 아이콘 반지름
        TABLE_X += 6   # 전체 오른쪽 이동
        ICON_D   = ICON_R * 2
        NAME_W   = 16      # 한글명 너비
        BAR_X0   = TABLE_X + ICON_D + 6 + NAME_W + 3
        COUNT_W  = 22      # 개수 텍스트 너비
        BAR_MAXW = (TABLE_X + TABLE_W) - BAR_X0 - COUNT_W - 4
        ROW_GAP  = 4       # 행 간격
        ROW_H_E  = ICON_D + ROW_GAP

        for ek, hanja, name_kr, color in ELEM_META:
            val   = elements.get(ek, 0)
            status_label, fill_ratio = _elem_status(val)
            bar_w = int(BAR_MAXW * fill_ratio)
            ey    = self.get_y()

            # 원형 아이콘
            self._fill(color)
            self._stroke(color)
            self.set_line_width(0)
            self.ellipse(TABLE_X, ey, ICON_D, ICON_D, style='F')
            self.set_line_width(0.2)
            # 아이콘 한자
            self.set_font('KR', 'B', 15)
            tc = self.get_text_color(color)
            self._text_color(tc)
            self.set_xy(TABLE_X, ey + ICON_R - 6)
            self.cell(ICON_D, 12, hanja, align='C')

            # 한글 이름
            self.set_font('KR', '', 15)
            self._text_color(C_TEXT_DARK)
            self.set_xy(TABLE_X + ICON_D + 4, ey + ICON_R - 6)
            self.cell(NAME_W, 12, name_kr)

            # 바 배경 (회색)
            self._fill((225, 228, 233))
            self._stroke((225, 228, 233))
            self.set_line_width(0)
            self._rounded_rect_v2(BAR_X0, ey + 3, BAR_MAXW, ICON_D - 6, 3)
            self.set_line_width(0.2)

            # 바 채움 (비율 기반)
            if bar_w > 0:
                self._fill(color)
                self._stroke(color)
                self.set_line_width(0)
                self._rounded_rect_v2(BAR_X0, ey + 3, bar_w, ICON_D - 6, 3)
                self.set_line_width(0.2)

            # 상태 레이블
            self.set_font('KR', 'B', 14)
            if bar_w > 0:
                tc = self.get_text_color(color)
            else:
                tc = C_TEXT_MID
            self._text_color(tc)
            self.set_xy(BAR_X0 + 6, ey + ICON_R - 5.5)
            self.cell(max(bar_w - 6, 26), 11, status_label)

            # 개수 (바 오른쪽)
            self.set_font('KR', '', 15)
            self._text_color(C_TEXT_MID)
            self.set_xy(BAR_X0 + BAR_MAXW + 5, ey + ICON_R - 6)
            self.cell(COUNT_W, 12, f'{val}개')

            self.set_y(ey + ROW_H_E)

        self.ln(4)

    # ══════════════════════════════════════════════════════════════════════════
    # 5. 분석 섹션 (각 챕터는 반드시 새 페이지 시작)
    # ══════════════════════════════════════════════════════════════════════════
    def add_analysis_section(self, title: str, content: str):
        self._start_content_page(title)
        self._render_markdown(content, x=20, width=170)

    # ══════════════════════════════════════════════════════════════════════════
    # 6. 세운(年運) 데이터 테이블 섹션
    # ══════════════════════════════════════════════════════════════════════════
    def add_seun_section(self, seun_list: list):
        if not seun_list:
            return
        self._start_content_page('세운(年運) 데이터')

        headers = ['연도', '간지', '천간오행', '천간십성', '지지오행', '지지십성', '12운성', '신살']
        col_ws  = [20,     18,      20,         24,          20,         24,          20,        25]

        def _draw_header():
            self._fill(C_CHARCOAL)
            self.rect(17, self.get_y(), 171, 9, style='F')
            self.set_font('KR-Light', '', 8)
            self._text_color(C_GOLD)
            cx = 17
            for hw, hd in zip(col_ws, headers):
                self.set_xy(cx, self.get_y())
                self.cell(hw, 9, hd, align='C')
                cx += hw
            self.ln(9)

        _draw_header()

        for di, seun in enumerate(seun_list):
            ry = self.get_y()
            if ry > 268:
                self._start_content_page('세운(年運) 데이터')
                _draw_header()
                ry = self.get_y()

            bg = (248, 248, 252) if di % 2 == 0 else C_WHITE
            self._fill(bg); self._stroke(C_CARD_BORDER)
            self.set_line_width(0.15)
            self.rect(17, ry, 171, 9, style='FD')

            row_vals = [
                str(seun["연도"]),
                _pillar_ganji(seun),
                _pillar_gan_elem(seun),
                _pillar_gan_ss(seun),
                _pillar_ji_elem(seun),
                _pillar_ji_ss(seun),
                _pillar_ji_12(seun),
                _pillar_ji_sal(seun),
            ]
            cx = 17
            for ci, (hw, rv) in enumerate(zip(col_ws, row_vals)):
                self.set_xy(cx, ry)
                if ci in (2, 4):
                    self._text_color(ELEMENT_COLORS.get(rv, C_TEXT_MID))
                    self.set_font('KR', 'B', 8)
                elif ci == 7:
                    self._text_color(C_FIRE if rv != '-' else C_TEXT_LIGHT)
                    self.set_font('KR', '', 8)
                else:
                    self._text_color(C_TEXT_DARK)
                    self.set_font('KR', '', 8)
                self.cell(hw, 9, rv, align='C')
                cx += hw
            self.ln(9)

    # ══════════════════════════════════════════════════════════════════════════
    # 7. 월운(月運) 데이터 테이블 섹션
    # ══════════════════════════════════════════════════════════════════════════
    def add_wolun_section(self, wolun_list: list):
        if not wolun_list:
            return
        year = wolun_list[0]["연도"]
        self._start_content_page(f'{year}년 월운(月運) 데이터')

        headers = ['월',  '간지', '천간오행', '천간십성', '지지오행', '지지십성', '12운성', '신살']
        col_ws  = [14,    18,      20,         24,          20,         24,          20,        31]

        self._fill(C_CHARCOAL)
        self.rect(17, self.get_y(), 171, 9, style='F')
        self.set_font('KR-Light', '', 8)
        self._text_color(C_GOLD)
        cx = 17
        for hw, hd in zip(col_ws, headers):
            self.set_xy(cx, self.get_y())
            self.cell(hw, 9, hd, align='C')
            cx += hw
        self.ln(9)

        month_kr = ["1월","2월","3월","4월","5월","6월",
                    "7월","8월","9월","10월","11월","12월"]

        for di, wolun in enumerate(wolun_list):
            ry = self.get_y()
            if ry > 268:
                self._start_content_page(f'{year}년 월운(月運) 데이터')
                self._fill(C_CHARCOAL)
                self.rect(17, self.get_y(), 171, 9, style='F')
                self.set_font('KR-Light', '', 8)
                self._text_color(C_GOLD)
                cx = 17
                for hw, hd in zip(col_ws, headers):
                    self.set_xy(cx, self.get_y())
                    self.cell(hw, 9, hd, align='C')
                    cx += hw
                self.ln(9)
                ry = self.get_y()

            bg = (248, 248, 252) if di % 2 == 0 else C_WHITE
            self._fill(bg); self._stroke(C_CARD_BORDER)
            self.set_line_width(0.15)
            self.rect(17, ry, 171, 9, style='FD')

            row_vals = [
                month_kr[wolun["월"] - 1],
                _pillar_ganji(wolun),
                _pillar_gan_elem(wolun),
                _pillar_gan_ss(wolun),
                _pillar_ji_elem(wolun),
                _pillar_ji_ss(wolun),
                _pillar_ji_12(wolun),
                _pillar_ji_sal(wolun),
            ]
            cx = 17
            for ci, (hw, rv) in enumerate(zip(col_ws, row_vals)):
                self.set_xy(cx, ry)
                if ci in (2, 4):
                    self._text_color(ELEMENT_COLORS.get(rv, C_TEXT_MID))
                    self.set_font('KR', 'B', 8)
                elif ci == 7:
                    self._text_color(C_FIRE if rv != '-' else C_TEXT_LIGHT)
                    self.set_font('KR', '', 8)
                else:
                    self._text_color(C_TEXT_DARK)
                    self.set_font('KR', '', 8)
                self.cell(hw, 9, rv, align='C')
                cx += hw
            self.ln(9)

    # ══════════════════════════════════════════════════════════════════════════
    # 8. 월별 운세 — 월별 반드시 새 페이지
    # ══════════════════════════════════════════════════════════════════════════
    def add_monthly_section(self, monthly: dict, target_year: int = None):
        year_str = f"{target_year}년 " if target_year else "올해 "
        month_names = ['1월','2월','3월','4월','5월','6월',
                    '7월','8월','9월','10월','11월','12월']

        first = True
        for month_key, content in monthly.items():
            mn = month_names[int(month_key) - 1]
            # 첫 월만 번호 증가, 이후 월은 같은 번호 유지
            self._start_content_page(f'{year_str}{mn} 운세', auto_number=first)
            first = False
            self._render_markdown(content, x=20, width=170)
            self.ln(4)
            
    # ══════════════════════════════════════════════════════════════════════════
    # 9. 향후 10년 연간 운세 — 연도별 반드시 새 페이지
    # ══════════════════════════════════════════════════════════════════════════
    def add_yearly_section(self, yearly: dict):
        first = True
        for year_key, content in yearly.items():
            # 첫 연도만 번호 증가, 이후 연도는 같은 번호 유지
            self._start_content_page(f'{year_key}년 연간 운세', auto_number=first)
            first = False
            self._render_markdown(content, x=20, width=170)
            self.ln(4)

    # ══════════════════════════════════════════════════════════════════════════
    # 10. 올해 운세 / 요약 (기본 리포트용)
    # ══════════════════════════════════════════════════════════════════════════
    def add_this_year_section(self, content: str, target_year: int = None):
        year_str = f"{target_year}년" if target_year else "올해"
        self._start_content_page(f'{year_str} 간략 총평')
        self._render_markdown(content, x=20, width=170)

    def add_summary_section(self, content: str, target_year: int = None):
        year_str = f"{target_year}년 " if target_year else ""
        self._start_content_page(f'{year_str}전반 운세')
        self._render_markdown(content, x=20, width=170)

    # ══════════════════════════════════════════════════════════════════════════
    # 11. 마지막 페이지
    # ══════════════════════════════════════════════════════════════════════════
    def add_epilogue(self, name: str, today: str):
        self.add_page()
        self._fill(C_CHARCOAL)
        self.rect(0, 0, 210, 297, style='F')

        self._fill(C_GOLD)
        self.rect(0, 0, 210, 3, style='F')

        self.set_fill_color(55, 75, 95)
        self.ellipse(-30, 180, 140, 140, style='F')
        self.set_fill_color(50, 70, 90)
        self.ellipse(130, -20, 100, 100, style='F')

        qx, qy, qw, qh = 25, 70, 160, 140
        self.set_fill_color(55, 72, 90)
        self.set_draw_color(*C_GOLD)
        self.set_line_width(0.6)
        self._rounded_rect_v2(qx, qy, qw, qh, 6)
        self.set_line_width(0.2)

        self.set_font('KR', 'B', 48)
        self._text_color(C_GOLD)
        self.set_xy(qx + 8, qy + 4)
        self.cell(20, 18, '"')

        quote_lines = [
            '사주는 운명의 설계도입니다.',
            '',
            '하지만 그 설계도를',
            '어떻게 활용하느냐는',
            '오직 당신의 선택과',
            '의지에 달려 있습니다.',
            '',
            f'{name} 님의 삶에',
            '작은 빛이 되기를 바랍니다.',
        ]
        self.set_font('KR', '', 16)
        self._text_color((210, 215, 228))
        ty = qy + 28
        for line in quote_lines:
            self.set_xy(qx, ty)
            self.cell(qw, 10, line, align='C')
            ty += 10

        self.set_font('KR', 'B', 48)
        self._text_color(C_GOLD)
        self.set_xy(qx + qw - 30, qy + qh - 22)
        self.cell(20, 18, '"')

        self._divider(55, 228, 100, C_GOLD, 0.5)
        self.set_font('KR', '', 13)
        self._text_color(C_TEXT_LIGHT)
        self.set_xy(0, 233)
        self.cell(210, 8, '— 사주 분석 시스템 —', align='C')
        self.set_font('KR-Light', '', 12)
        self.set_xy(0, 242)
        self.cell(210, 8, today, align='C')

        self._fill(C_GOLD)
        self.rect(0, 294, 210, 3, style='F')


# ══════════════════════════════════════════════════════════════════════════════
# 퍼블릭 API
# ══════════════════════════════════════════════════════════════════════════════

def generate_pdf(saju_data: dict, analysis: dict,
                 output_path: str,
                 chart_paths: dict = None,
                 report_type: str = "premium",
                 target_year: int = None) -> str:
    # chart_paths는 하위 호환성을 위해 파라미터로 유지하되 사용하지 않음

    today = _today_str()
    pdf   = SajuPDF()

    if target_year is None:
        seun_list = saju_data.get("세운", [])
        target_year = seun_list[0]["연도"] if seun_list else datetime.now().year

    year_str = f"{target_year}년"
    name = saju_data['기본정보']['이름']

    # ── 표지 ──
    pdf.add_cover(saju_data, today)

    if report_type == "basic":
        # ══ 기본 리포트 흐름 ══
        toc_entries = [
            ('사주 원국',),
            ('타고난 성격과 기질',),
            ('전반 운세',),
            (f'{year_str} 간략 총평',),
        ]
        pdf.add_toc(toc_entries)
        pdf._section_counter = 0
        pdf._page_num_enabled = True

        pdf.add_saju_intro(saju_data)

        if analysis.get("personality"):
            pdf.add_analysis_section('타고난 성격과 기질', analysis["personality"])

        if analysis.get("summary"):
            pdf.add_summary_section(analysis["summary"], target_year)

        if analysis.get("this_year"):
            pdf.add_this_year_section(analysis["this_year"], target_year)

    else:
        # ══ 프리미엄 리포트 흐름 ══
        section_configs = [
            ("personality",    "타고난 본질과 성격"),
            ("wealth",         "재물운 상세 분석"),
            ("career",         "직업·직장운 상세 분석"),
            ("love",           "연애·결혼운 상세 분석"),
            ("relationships",  "인간관계·가족운 상세 분석"),
            ("health",         "건강운 상세 분석"),
            ("lucky_charm",    "맞춤형 개운 가이드"),
            ("lifetime",       "평생 총운"),
        ]

        toc_entries = [('사주 원국',)]
        for key, title in section_configs:
            if analysis.get(key):
                toc_entries.append((title,))
        if analysis.get("monthly"):
            toc_entries.append((f'{year_str} 월별 운세',))
        if analysis.get("yearly"):
            toc_entries.append(('향후 10년 연간 운세',))

        pdf.add_toc(toc_entries)
        pdf._section_counter = 0
        pdf._page_num_enabled = True

        pdf.add_saju_intro(saju_data)

        for key, title in section_configs:
            content = analysis.get(key, "")
            if content:
                pdf.add_analysis_section(title, content)

        if analysis.get("monthly"):
            pdf.add_monthly_section(analysis["monthly"], target_year)

        if analysis.get("yearly"):
            pdf.add_yearly_section(analysis["yearly"])

    # 마무리
    pdf.add_epilogue(name, today)

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    pdf_bytes = pdf.output()
    with open(output_path, 'wb') as f:
        f.write(pdf_bytes)
    print(f"  PDF 생성 완료: {output_path}")
    return output_path


if __name__ == "__main__":
    print("pdf_generator 모듈 로드 완료")