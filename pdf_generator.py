"""
PDF 생성 모듈 (fpdf2 기반 - Windows 호환)
- HTML 디자인(골드/차콜/화이트 팔레트, glass-card 스타일) 반영
- NanumGothic 폰트로 한국어/한자 완전 지원
- 표지 → 목차 → 사주원국 → 분석섹션들 → 마지막 페이지

[수정 사항 v4]
Bug Fix:
  1. 목차 페이지 번호 제거 (숫자 셀 + 점선 삭제)
  2. 폰트 사이즈 전반 2pt 상향 조정
  3. add_cover()의 '생년월일시' → '생년월일' 키 오류 수정
  4. 신강신약 한자(身弱/身強) KR-Light 폰트 누락 → KR 폰트로 변경
  5. TSI subset 경고 무시 (fpdf2 내부 이슈, 기능에 영향 없음)

[수정 사항 v5]
  8. 고아 제목(orphan heading) 방지 강화:
     - h1/h2/h3 _ensure_space 후행 보장치 48mm → 96mm 로 상향
       (제목 뒤 최소 8줄 분량의 본문이 같은 페이지에 오도록 강제)
     - bold_line도 뒤에 본문 48mm 보장 추가
     - 이로써 "제목만 있고 내용은 다음 페이지" 현상 제거

[수정 사항 v4 - 신규]
  6. 폰트 계층 구조 수정:
     - h1/h2 (번호 달린 섹션 제목): 18pt Bold → 가장 큼
     - bold_line ([대괄호] 소제목): 17pt Bold → 섹션 제목보다 작고 본문보다 큼
     - bullet/text (본문): 16pt → 가장 작음
  7. 헤더 누락 페이지 수정:
     - _render_markdown 내 모든 페이지 넘김(_new_content_page) 시 헤더 출력
     - add_saju_chart, add_seun_section, add_wolun_section 등 테이블 섹션도
       페이지 넘김 시 헤더 재출력하도록 통일
     - add_epilogue는 독립 디자인 페이지로 헤더 없음 유지
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

C_WOOD  = (47,  133, 90)
C_FIRE  = (197, 48,  48)
C_EARTH = (116, 66,  16)
C_METAL = (113, 128, 150)
C_WATER = (26,  54,  93)

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
        # --- 구분선은 완전히 무시
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
        # [수정 v5] auto page break 비활성화 — multi_cell 도중 헤더 없는 빈 페이지 생성 방지
        # 대신 _render_markdown 에서 블록별로 필요 높이를 계산해 수동 페이지 넘김
        self.set_auto_page_break(auto=False)
        self._register_fonts()
        self.set_margins(0, 0, 0)
        self._page_num_enabled = False
        self._current_section_icon  = ''
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
    def _render_markdown(self, text: str, x=20, width=170, line_h=12):
        """
        폰트 계층 (수정 v4):
          h1/h2  : 번호 달린 섹션 제목 → 18pt Bold  (가장 큼)
          h3     : 소소제목              → 18pt Bold
          bold_line: [대괄호] 소제목   → 17pt Bold  (h1/h2보다 작고 본문보다 큼)
          bullet/text: 본문             → 16pt       (가장 작음)

        [수정 v5] auto_page_break=False 이므로, 각 블록을 그리기 직전에
        필요 높이를 추정하고 부족하면 _new_content_page() 를 호출한다.
        이렇게 하면 multi_cell 도중 fpdf2 가 헤더 없는 빈 페이지를 만드는 문제가 사라진다.
        """
        PAGE_BOTTOM = 275  # 여백을 고려한 실질 하단 (mm)

        blocks = parse_markdown_blocks(text)
        self.set_left_margin(x)
        self.set_right_margin(210 - x - width)

        def _new_content_page():
            """현재 섹션 헤더를 유지하며 새 페이지 시작"""
            self.add_page()
            self._fill(C_OFFWHITE)
            self.rect(0, 0, 210, 297, style='F')
            if self._current_section_icon:
                self._draw_section_header(
                    self._current_section_icon,
                    self._current_section_title
                )
            self.set_left_margin(x)
            self.set_right_margin(210 - x - width)

        def _estimate_lines(content: str, chars_per_line: int = 30) -> int:
            """텍스트가 몇 줄로 wrapping 될지 대략 추정"""
            if not content:
                return 1
            return max(1, (len(content) // chars_per_line) + 1)

        def _ensure_space(needed_mm: float):
            """현재 Y 에서 needed_mm 만큼 공간이 없으면 새 페이지"""
            if self.get_y() + needed_mm > PAGE_BOTTOM:
                _new_content_page()

        for btype, content in blocks:

            if btype == 'blank':
                # blank 는 높이가 작으므로 여유 있을 때만 추가
                if self.get_y() + 5 <= PAGE_BOTTOM:
                    self.ln(5)

            elif btype == 'h1':
                lines = _estimate_lines(content, 25)
                # 제목 높이 + 본문 최소 8줄(96mm) — 고아 제목 방지 (강화)
                _ensure_space(6 + lines * 13 + 3 + 96)
                self.ln(6)
                self.set_font('KR', 'B', 18)
                self._text_color(C_CHARCOAL)
                self.set_x(x)
                self.multi_cell(width, 13, content, align='L', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
                self.ln(3)

            elif btype == 'h2':
                lines = _estimate_lines(content, 25)
                # 제목 높이 + 본문 최소 8줄(96mm) — 고아 제목 방지 (강화)
                _ensure_space(5 + lines * 13 + 3 + 96)
                self.ln(5)
                self._fill(C_GOLD)
                self.rect(x, self.get_y(), 5, 11, style='F')
                self.set_font('KR', 'B', 18)
                self._text_color(C_CHARCOAL)
                self.set_x(x + 10)
                self.multi_cell(width - 10, 13, content, align='L', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
                self.ln(3)

            elif btype == 'h3':
                lines = _estimate_lines(content, 28)
                # 제목 높이 + 본문 최소 8줄(96mm) — 고아 제목 방지 (강화)
                _ensure_space(10 + lines * 10 + 2 + 96)
                self.ln(10)
                self.set_font('KR', 'B', 18)
                self._text_color(C_ACCENT)
                self.set_x(x)
                self.multi_cell(width, 10, content, align='L', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
                self.ln(2)

            elif btype == 'bold_line':
                lines = _estimate_lines(content, 28)
                # bold_line도 뒤에 본문 최소 3줄 보장
                _ensure_space(lines * 11 + 2 + 48)
                self.set_font('KR', 'B', 17)
                self._text_color(C_CHARCOAL)
                self.set_x(x)
                self.multi_cell(width, 11, content.lstrip(), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
                self.ln(2)

            elif btype == 'bullet':
                lines = _estimate_lines(content, 28)
                _ensure_space(lines * line_h + 1)
                self.set_font('KR', '', 16)
                self._text_color(C_TEXT_DARK)
                self._fill(C_GOLD)
                self.ellipse(x + 1, self.get_y() + 4.5, 3, 3, style='F')
                self.set_x(x + 8)
                self.multi_cell(width - 8, line_h, strip_markdown(content),
                                new_x=XPos.LMARGIN, new_y=YPos.NEXT)
                self.ln(1)

            else:  # text
                lines = _estimate_lines(content, 28)
                _ensure_space(lines * line_h)
                self.set_font('KR', '', 16)
                self._text_color(C_TEXT_DARK)
                self.set_x(x)
                self.multi_cell(width, line_h, strip_markdown(content),
                                new_x=XPos.LMARGIN, new_y=YPos.NEXT)

        self.set_left_margin(0)
        self.set_right_margin(0)

    # ══════════════════════════════════════════════════════════════════════════
    # 1. 표지
    # ══════════════════════════════════════════════════════════════════════════
    def add_cover(self, saju_data: dict, today: str):
        self.add_page()
        name   = saju_data['기본정보']['이름']
        birth  = saju_data['기본정보'].get('생년월일', saju_data['기본정보'].get('생년월일시', ''))
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
            icon, title = entry[0], entry[1]

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
            self.cell(150, 8, f'{icon}  {title}')

        self._divider(20, 278, 170, C_GOLD, 0.5)
        self.set_font('KR-Light', '', 9)
        self._text_color(C_TEXT_LIGHT)
        self.set_xy(0, 281)
        self.cell(210, 6, '사주 분석 시스템  ·  Individual Destiny Map', align='C')

    # ══════════════════════════════════════════════════════════════════════════
    # 3. 섹션 페이지 헤더
    # ══════════════════════════════════════════════════════════════════════════
    def _draw_section_header(self, section_icon: str, section_title: str):
        """헤더 바만 그림 (페이지 추가 없이) — 연속 페이지 재출력에 사용"""
        self._fill(C_CHARCOAL)
        self.rect(0, 0, 210, 28, style='F')
        self._fill(C_GOLD)
        self.rect(0, 28, 210, 1.5, style='F')
        self.set_font('KR', 'B', 16)
        self._text_color(C_WHITE)
        self.set_xy(20, 9)
        self.cell(150, 10, f'{section_icon}  {section_title}')
        self.set_font('KR-Light', '', 14)
        self._text_color(C_GOLD)
        self.set_xy(150, 10)
        self.cell(40, 8, '사주 분석', align='R')
        self.set_y(45)

    def _start_content_page(self, section_icon: str, section_title: str):
        self._current_section_icon  = section_icon
        self._current_section_title = section_title
        self.add_page()
        self._fill(C_OFFWHITE)
        self.rect(0, 0, 210, 297, style='F')
        self._draw_section_header(section_icon, section_title)

    # ══════════════════════════════════════════════════════════════════════════
    # 4. 사주 원국 페이지
    # ══════════════════════════════════════════════════════════════════════════
    def add_saju_chart(self, saju_data: dict):
        self._start_content_page('[분석]', '사주 원국 및 기본 데이터')

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
             f"{saju_data['일간정보']['일간']} ({saju_data['일간정보']['오행']} · {saju_data['일간정보']['음양']})"),
            ('신강/신약', strength_display),
            ('음력 생년월일', saju_data['기본정보']['음력']),
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
            # [수정 v4] 대운 테이블이 페이지를 넘칠 경우 헤더 포함 새 페이지
            if self.get_y() > 220:
                self._start_content_page('[분석]', '사주 원국 및 기본 데이터')

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
                    # [수정 v4] 헤더 포함 새 페이지
                    self._start_content_page('[분석]', '사주 원국 및 기본 데이터')
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
    # 5. 분석 섹션
    # ══════════════════════════════════════════════════════════════════════════
    def add_analysis_section(self, icon: str, title: str, content: str):
        self._start_content_page(icon, title)
        self._render_markdown(content, x=20, width=170)

    # ══════════════════════════════════════════════════════════════════════════
    # 6. 세운(年運) 데이터 테이블 섹션
    # ══════════════════════════════════════════════════════════════════════════
    def add_seun_section(self, seun_list: list):
        if not seun_list:
            return
        self._start_content_page('[세운]', '세운(年運) 데이터')

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
                # [수정 v4] 헤더 포함 새 페이지
                self._start_content_page('[세운]', '세운(年運) 데이터')
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
        self._start_content_page('[월운]', f'{year}년 월운(月運) 데이터')

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
                # [수정 v4] 헤더 포함 새 페이지
                self._start_content_page('[월운]', f'{year}년 월운(月運) 데이터')
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
    # 8. 연간 운세 (AI 분석 텍스트)
    # ══════════════════════════════════════════════════════════════════════════
    def add_yearly_section(self, yearly: dict):
        self._start_content_page('[운세]', '향후 10년 연간 운세')

        for year_key, content in yearly.items():
            if self.get_y() > 250:
                self._start_content_page('[운세]', '향후 10년 연간 운세 (계속)')

            self._fill(C_CHARCOAL)
            self.rect(20, self.get_y(), 170, 13, style='F')
            self._fill(C_GOLD)
            self.rect(20, self.get_y(), 3, 13, style='F')
            self.set_font('KR', 'B', 12)
            self._text_color(C_WHITE)
            self.set_xy(26, self.get_y() + 2)
            self.cell(160, 9, f'{year_key}년 운세')
            self.ln(17)

            self._render_markdown(content, x=20, width=170)
            self.ln(4)

    # ══════════════════════════════════════════════════════════════════════════
    # 9. 월별 운세 (AI 분석 텍스트)
    # ══════════════════════════════════════════════════════════════════════════
    def add_monthly_section(self, monthly: dict, target_year: int = None):
        year_str = f"{target_year}년 " if target_year else "올해 "
        self._start_content_page('[월운]', f'{year_str}월별 운세')
        month_names = ['1월','2월','3월','4월','5월','6월',
                       '7월','8월','9월','10월','11월','12월']

        for month_key, content in monthly.items():
            mn = month_names[int(month_key) - 1]
            if self.get_y() > 255:
                self._start_content_page('[월운]', f'{year_str}월별 운세 (계속)')

            self._fill((240, 242, 248)); self._stroke(C_CARD_BORDER)
            self.set_line_width(0.3)
            self.rect(20, self.get_y(), 170, 10, style='FD')
            self._fill(C_GOLD)
            self.rect(20, self.get_y(), 3, 10, style='F')
            self.set_font('KR', 'B', 11)
            self._text_color(C_CHARCOAL)
            self.set_xy(26, self.get_y() + 1)
            self.cell(160, 8, mn)
            self.ln(14)

            self._render_markdown(content, x=20, width=170, line_h=12)
            self.ln(3)

    # ══════════════════════════════════════════════════════════════════════════
    # 10. 올해 운세 / 요약
    # ══════════════════════════════════════════════════════════════════════════
    def add_this_year_section(self, content: str, target_year: int = None):
        year_str = f"{target_year}년" if target_year else "올해"
        self._start_content_page('[운세]', f'{year_str} 운세')
        self._render_markdown(content, x=20, width=170)

    def add_summary_section(self, content: str, target_year: int = None):
        year_str = f"{target_year}년 " if target_year else ""
        self._start_content_page('[분석]', f'{year_str}분야별 운세 요약')
        self._render_markdown(content, x=20, width=170)

    # ══════════════════════════════════════════════════════════════════════════
    # 11. 마지막 페이지
    # [수정 v4] 마지막 페이지 인용문 폰트를 16pt로 명시 (헤더 없는 독립 디자인 유지)
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
        # [수정 v4] 본문과 동일한 16pt 폰트 적용
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
        self.cell(210, 8, '— AI 사주 분석 시스템 —', align='C')
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

    today = _today_str()
    pdf   = SajuPDF()

    # target_year 미지정 시 세운 데이터에서 자동 추출
    if target_year is None:
        seun_list = saju_data.get("세운", [])
        target_year = seun_list[0]["연도"] if seun_list else datetime.now().year

    year_str = f"{target_year}년"

    section_configs = [
        ("personality",  "[성격]", "타고난 본질과 성격"),
        ("wealth",       "[재물]", "재물운 상세 분석"),
        ("career",       "[직업]", "직업·직장운 상세 분석"),
        ("love",         "[애정]", "연애·결혼운 상세 분석"),
        ("health",       "[건강]", "건강운 상세 분석"),
        ("lucky_charm",  "[개운]", "맞춤형 개운 가이드"),
    ]

    toc_entries = []
    # toc_entries.append(('[분석]', '사주 원국 및 기본 데이터'))

    # has_seun  = bool(saju_data.get("세운"))
    # has_wolun = bool(saju_data.get("월운"))
    # if has_seun:
    #     toc_entries.append(('[세운]', '세운(年運) 데이터'))
    # if has_wolun:
    #     toc_entries.append(('[월운]', '월운(月運) 데이터'))

    for key, icon, title in section_configs:
        if analysis.get(key):
            toc_entries.append((icon, title))

    if analysis.get("this_year"):
        toc_entries.append(('[운세]', f'{year_str} 운세'))
    if analysis.get("summary"):
        toc_entries.append(('[분석]', f'{year_str} 분야별 운세 요약'))
    if analysis.get("yearly"):
        toc_entries.append(('[운세]', '향후 10년 연간 운세'))
    if analysis.get("monthly"):
        toc_entries.append(('[월운]', f'{year_str} 월별 운세'))

    toc_entries.append(('[마무리]', '맺음말'))

    pdf.add_cover(saju_data, today)
    pdf.add_toc(toc_entries)
    pdf._page_num_enabled = True

    # pdf.add_saju_chart(saju_data)

    # if has_seun:
    #     pdf.add_seun_section(saju_data["세운"])
    # if has_wolun:
    #     pdf.add_wolun_section(saju_data["월운"])

    for key, icon, title in section_configs:
        content = analysis.get(key, "")
        if content:
            pdf.add_analysis_section(icon, title, content)

    if analysis.get("this_year"):
        pdf.add_this_year_section(analysis["this_year"], target_year)
    if analysis.get("summary"):
        pdf.add_summary_section(analysis["summary"], target_year)
    if analysis.get("yearly"):
        pdf.add_yearly_section(analysis["yearly"])
    if analysis.get("monthly"):
        pdf.add_monthly_section(analysis["monthly"], target_year)

    pdf.add_epilogue(saju_data['기본정보']['이름'], today)

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    pdf_bytes = pdf.output()
    with open(output_path, 'wb') as f:
        f.write(pdf_bytes)
    print(f"  PDF 생성 완료: {output_path}")
    return output_path


# ── 단독 실행 테스트 ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys
    sys.path.insert(0, os.path.dirname(__file__))
    from saju_calculator import calculate_saju, get_seun, get_wolun
    from datetime import datetime

    dummy_saju = calculate_saju("홍길동", 1995, 12, 13, 23, "남", 0)
    today_year = datetime.now().year
    d_stem     = dummy_saju["일간정보"]["일간"]
    y_branch   = dummy_saju["사주원국"]["연주"]["지지"]

    dummy_saju["세운"] = [get_seun(today_year + i, d_stem, y_branch) for i in range(10)]
    dummy_saju["월운"] = [get_wolun(today_year, m, d_stem, y_branch) for m in range(1, 13)]

    dummy_analysis = {
        "personality": "## 타고난 본질\n\n일간 **戊土**는 대지를 상징합니다.\n\n### 핵심 기질\n- 강한 책임감\n- 포용력",
        "wealth":      "## 재물운\n\n안정적인 재물 흐름이 예상됩니다.",
        "summary":     "## 요약\n\n### 재물운\n상승세입니다.\n\n### 건강운\n과로 주의.",
        "this_year":   "## 올해 운세\n\n좋은 기운이 들어오는 해입니다.",
    }

    out = "/tmp/saju_test/test_report.pdf"
    os.makedirs("/tmp/saju_test", exist_ok=True)
    generate_pdf(dummy_saju, dummy_analysis, out)
    print(f"테스트 완료: {out}")