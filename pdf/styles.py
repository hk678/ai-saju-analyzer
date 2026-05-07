"""
PDF 스타일 상수 및 폰트 경로 (Styles).

색상 팔레트와 폰트 경로를 단일 위치에서 관리한다.
pdf/ 하위 모듈 전체가 이 모듈에서 import하여 사용한다.
"""

import os
import sys
from datetime import datetime

# stdout UTF-8 보정 (Windows)
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# ── 폰트 경로 ─────────────────────────────────────────────────────────────────
# fonts/ 디렉토리는 프로젝트 루트(fortune_teller/의 부모)에 위치한다.
FONT_DIR = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "fonts")
)

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

ELEMENT_COLORS: dict[str, tuple] = {
    "목": C_WOOD,  "화": C_FIRE,  "토": C_EARTH,
    "금": C_METAL, "수": C_WATER,
    "木": C_WOOD,  "火": C_FIRE,  "土": C_EARTH,
    "金": C_METAL, "水": C_WATER,
}

# ── 날짜 헬퍼 ─────────────────────────────────────────────────────────────────

def today_str() -> str:
    """현재 날짜를 'YYYY. MM. DD.' 형식으로 반환."""
    now = datetime.now()
    return f"{now.year}. {now.month:02d}. {now.day:02d}."
