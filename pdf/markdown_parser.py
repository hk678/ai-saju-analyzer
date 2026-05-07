"""
마크다운 파서 (Markdown Parser).

AI가 반환한 마크다운 텍스트를 fpdf2 렌더링에 적합한
블록 리스트로 변환한다.
"""

import re


def strip_markdown(text: str) -> str:
    """마크다운 강조·헤더 기호를 제거하고 단일 줄로 반환."""
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
    text = re.sub(r'\*(.+?)\*',     r'\1', text)
    text = re.sub(r'^#{1,6}\s+',    '',    text, flags=re.MULTILINE)
    text = text.replace('\n', ' ').replace('\r', '')
    return text.strip()


def parse_markdown_blocks(text: str) -> list[tuple[str, str]]:
    """
    마크다운 텍스트를 (블록타입, 내용) 튜플 리스트로 변환.

    블록타입:
        'h1' / 'h2' / 'h3' — 헤더
        'bullet'            — 목록 항목
        'bold_line'         — 굵은 라인
        'blank'             — 빈 줄
        'text'              — 일반 텍스트
    """
    blocks: list[tuple[str, str]] = []

    for line in text.split("\n"):
        stripped = line.strip()

        # 수평선(---, ___, ***) 무시
        if (
            re.match(r'^-{2,}$', stripped)
            or re.match(r'^_{2,}$', stripped)
            or re.match(r'^\*{2,}$', stripped)
        ):
            continue

        if line.startswith("### "):
            blocks.append(("h3",        line[4:].strip()))
        elif line.startswith("## "):
            blocks.append(("h2",        line[3:].strip()))
        elif line.startswith("# "):
            blocks.append(("h1",        line[2:].strip()))
        elif line.startswith("- ") or line.startswith("* "):
            blocks.append(("bullet",    line[2:].strip()))
        elif stripped.startswith("**") and stripped.endswith("**") and len(stripped) > 4:
            blocks.append(("bold_line", stripped[2:-2].strip()))
        elif stripped == "":
            blocks.append(("blank",     ""))
        else:
            blocks.append(("text",      stripped))

    return blocks
