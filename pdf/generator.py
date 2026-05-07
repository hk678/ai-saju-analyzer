"""
PDF 생성 진입점 (Generator).

generate_pdf() 하나만 공개한다.
페이지 렌더링 로직은 pages_common / pages_analysis / pages_fortune 에 위임하고,
이 모듈은 빌더 함수를 순서대로 호출하는 오케스트레이터 역할만 수행한다.
"""

import os
from datetime import datetime

from pdf.base_pdf import SajuPDF
from pdf.styles import today_str
from pdf.pages_common import (
    draw_cover_page,
    draw_toc_page,
    draw_saju_intro_page,
    draw_epilogue_page,
)
from pdf.pages_analysis import (
    draw_analysis_section,
    draw_this_year_section,
    draw_summary_section,
    draw_monthly_section,
    draw_yearly_section,
)

def generate_pdf(
    saju_data:   dict,
    analysis:    dict,
    output_path: str,
    chart_paths: dict = None,   # 하위 호환성 유지 (미사용)
    report_type: str  = "premium",
    target_year: int  = None,
) -> str:
    """
    사주 리포트 PDF 생성.

    페이지 순서:
      [기본]
        표지 → 원국표 → 목차 → 성격 → 전반운세 → 신년총평 → 에필로그

      [프리미엄]
        표지 → 원국표 → 목차 → 8개분석 → 월별운세 → 연간운세
             → (세운표 → 월운표 → 대운표) → 에필로그

    Args:
        saju_data:    calculate_saju() 결과 + "세운"/"월운" 키 포함
        analysis:     generate_*_report() 결과
        output_path:  출력 파일 경로 (.pdf)
        report_type:  "basic" 또는 "premium"
        target_year:  기준 연도 (None이면 세운 첫 연도 또는 현재 연도)

    Returns:
        output_path
    """
    today = today_str()
    pdf   = SajuPDF()

    if target_year is None:
        seun_list   = saju_data.get("세운", [])
        target_year = seun_list[0]["연도"] if seun_list else datetime.now().year

    year_str = f"{target_year}년"
    name     = saju_data["기본정보"]["이름"]

    # ── 표지 ────────────────────────────────────────────────────────────────
    draw_cover_page(pdf, saju_data, today)

    # ── 원국표 (기본·프리미엄 공용) ─────────────────────────────────────────
    draw_saju_intro_page(pdf, saju_data)

    if report_type == "basic":
        # ── 기본 리포트 ───────────────────────────────────────────────────
        toc_entries = [
            ("타고난 성격과 기질",),
            ("전반 운세",),
            (f"{year_str} 간략 총평",),
        ]
        draw_toc_page(pdf, toc_entries)
        pdf._section_counter  = 0
        pdf._page_num_enabled = True

        if analysis.get("personality"):
            draw_analysis_section(pdf, "타고난 성격과 기질", analysis["personality"])
        if analysis.get("summary"):
            draw_summary_section(pdf, analysis["summary"], target_year)
        if analysis.get("this_year"):
            draw_this_year_section(pdf, analysis["this_year"], target_year)

    else:
        # ── 프리미엄 리포트 ───────────────────────────────────────────────
        section_configs = [
            ("personality",   "타고난 본질과 성격"),
            ("wealth",        "재물운 상세 분석"),
            ("career",        "직업·직장운 상세 분석"),
            ("love",          "연애·결혼운 상세 분석"),
            ("relationships", "인간관계·가족운 상세 분석"),
            ("health",        "건강운 상세 분석"),
            ("lucky_charm",   "맞춤형 개운 가이드"),
            ("fortune_peaks", "인생의 상승기와 저운의 시기"),
        ]

        # 목차 항목 조립
        toc_entries = [
            (title,) for key, title in section_configs if analysis.get(key)
        ]

        monthly = analysis.get("monthly", {})
        yearly  = analysis.get("yearly",  {})

        if monthly:
            ym_keys = sorted(
                monthly.keys(),
                key=lambda k: (int(k.split("-")[0]), int(k.split("-")[1])),
            )
            mn_kr = [
                "1월","2월","3월","4월","5월","6월",
                "7월","8월","9월","10월","11월","12월",
            ]
            fy, fm = int(ym_keys[0].split("-")[0]), int(ym_keys[0].split("-")[1])
            ly, lm = int(ym_keys[-1].split("-")[0]), int(ym_keys[-1].split("-")[1])
            toc_entries.append(
                (f"{fy}년 {mn_kr[fm - 1]} ~ {ly}년 {mn_kr[lm - 1]} 월별 운세",)
            )

        if yearly:
            toc_entries.append(("향후 10년 연간 운세",))

        draw_toc_page(pdf, toc_entries)
        pdf._section_counter  = 0
        pdf._page_num_enabled = True

        # 8개 분석 섹션
        for key, title in section_configs:
            content = analysis.get(key, "")
            if content:
                draw_analysis_section(pdf, title, content)

        # 월별·연간 운세 서술
        if monthly:
            draw_monthly_section(pdf, monthly, target_year)
        if yearly:
            draw_yearly_section(pdf, yearly)


    # ── 에필로그 ─────────────────────────────────────────────────────────────
    draw_epilogue_page(pdf, name, today)

    # ── 파일 저장 ────────────────────────────────────────────────────────────
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    pdf_bytes = pdf.output()
    with open(output_path, "wb") as f:
        f.write(pdf_bytes)
    print(f"  PDF 생성 완료: {output_path}")
    return output_path
