"""
전체 파이프라인 실행 (Pipeline).

담당 기능:
  - _attach_seun_wolun() : saju_data에 세운·월운 추가
  - run_pipeline()       : 만세력 계산 → AI 분석 → PDF 생성
  - _print_origin()      : 사주원국 콘솔 출력 (중복 제거용 헬퍼)
"""

import json
import traceback
from datetime import datetime
from pathlib import Path

from core.saju_calculator import calculate_saju, get_seun, get_wolun
from analysis.report_generator import generate_premium_report, generate_basic_report
from pdf.generator import generate_pdf
from app.user_input import correct_pillars
from app.sample_data import get_sample_analysis


# ── 내부 헬퍼 ─────────────────────────────────────────────────────────────────

def _print_origin(saju_data: dict) -> None:
    """사주원국 및 일간 정보를 콘솔에 출력."""
    ori = saju_data["사주원국"]
    print(
        f"\n  ✅ 사주 원국: "
        f"연{ori['연주']['간지']} 월{ori['월주']['간지']} "
        f"일{ori['일주']['간지']} 시{ori['시주']['간지']}"
    )
    print(
        f"  ✅ 일간: {saju_data['일간정보']['일간']} "
        f"({saju_data['일간정보']['오행']}) / {saju_data['일간정보']['신강신약']}"
    )
    print(f"  ✅ 대운수: {saju_data['대운수']}")


def attach_seun_wolun(
    saju_data: dict,
    target_year: int,
    start_month: int = 1,
    seun_years:  int = 10,
) -> dict:
    """
    saju_data에 세운·월운 데이터를 추가한다.

    세운: target_year 부터 seun_years 개년치
    월운: start_month 부터 12개월 (연도 경계를 넘길 수 있음)
    """
    d_stem   = saju_data["일간정보"]["일간"]
    y_branch = saju_data["사주원국"]["연주"]["지지"]
    d_branch = saju_data["사주원국"]["일주"]["지지"]

    saju_data["세운"] = [
        get_seun(target_year + i, d_stem, y_branch, d_branch)
        for i in range(seun_years)
    ]

    wolun_list = []
    for i in range(12):
        offset = start_month - 1 + i
        m = offset % 12 + 1
        y = target_year + offset // 12
        wolun_list.append(get_wolun(y, m, d_stem, y_branch, d_branch))
    saju_data["월운"] = wolun_list

    return saju_data


# ── 전체 파이프라인 ───────────────────────────────────────────────────────────

def run_pipeline(user_info: dict, api_keys_str: str) -> tuple[str, str | None]:
    """
    전체 파이프라인 실행.

    단계: 만세력 계산 → JSON 저장 → (사용자 확인·간지 수정) → AI 분석 → PDF 생성

    Returns:
        (출력 디렉토리 경로, PDF 경로 또는 None)
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir   = Path(f"outputs/saju_{user_info['name']}_{timestamp}")
    out_dir.mkdir(parents=True, exist_ok=True)
    print(f"\n📁 출력 디렉토리: {out_dir}")

    # ── Step 1: 만세력 계산 ──────────────────────────────────────────────────
    print("\n🔢 [1/3] 만세력 계산 중...")
    saju_data = calculate_saju(
        user_info["name"],
        user_info["year"], user_info["month"], user_info["day"],
        user_info["hour"], user_info["gender"],
        user_info.get("minute", 0),
        user_info.get("yajasi", False),
    )

    target_year = user_info.get("target_year", datetime.now().year)
    start_month = user_info.get("start_month", 1)
    saju_data   = attach_seun_wolun(saju_data, target_year,
                                    start_month=start_month, seun_years=10)

    end_offset  = start_month - 1 + 11
    end_month   = end_offset % 12 + 1
    end_year    = target_year + end_offset // 12

    _print_origin(saju_data)
    print(f"  ✅ 세운 {target_year}~{target_year + 9} ({len(saju_data['세운'])}개) 계산 완료")
    print(f"  ✅ 월운 {target_year}년 {start_month}월 ~ {end_year}년 {end_month}월 계산 완료")

    # JSON 저장
    json_path = out_dir / "saju_data.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(saju_data, f, ensure_ascii=False, indent=2)
    print(f"\n  💾 사주 데이터 저장: {json_path}")

    # ── 사용자 확인 / 간지 수정 루프 ─────────────────────────────────────────
    print("\n" + "-" * 60)
    print(f"  📂 {json_path} 를 열어 사주 데이터를 확인하세요.")
    print("-" * 60)
    answer = input(
        "  계속 진행하시겠습니까? (엔터: 계속 / c: 간지 수정 / n: 중단): "
    ).strip().lower()

    if answer == "n":
        print("\n⛔ 사용자 요청으로 중단되었습니다.")
        print(f"   저장된 JSON: {json_path}")
        print("   이후 단계만 실행하려면 모드 2(PDF 재생성)를 이용하세요.\n")
        return str(out_dir), None

    while answer == "c":
        saju_data = correct_pillars(saju_data)
        saju_data = attach_seun_wolun(saju_data, target_year,
                                      start_month=start_month, seun_years=10)
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(saju_data, f, ensure_ascii=False, indent=2)

        _print_origin(saju_data)
        print(f"  💾 수정된 데이터 저장: {json_path}")
        print("\n" + "-" * 60)
        print(f"  📂 {json_path} 를 열어 사주 데이터를 확인하세요.")
        print("-" * 60)
        answer = input(
            "  계속 진행하시겠습니까? (엔터: 계속 / c: 간지 수정 / n: 중단): "
        ).strip().lower()

        if answer == "n":
            print("\n⛔ 사용자 요청으로 중단되었습니다.")
            print(f"   저장된 JSON: {json_path}")
            print("   이후 단계만 실행하려면 모드 2(PDF 재생성)를 이용하세요.\n")
            return str(out_dir), None

    # ── Step 2: AI 분석 ─────────────────────────────────────────────────────
    rtype             = user_info["report_type"]
    analysis_filename = "analysis_basic.json" if rtype == "basic" else "analysis_premium.json"
    analysis_path     = out_dir / analysis_filename
    progress_path     = out_dir / "analysis_progress.json"

    print(f"\n🤖 [2/3] AI 분석 생성 중 ({rtype.upper()})...")
    if not api_keys_str:
        print("  ⚠️  GEMINI_API_KEYS가 없습니다. 샘플 텍스트로 대체합니다.")
        analysis = get_sample_analysis(saju_data)
    else:
        try:
            if rtype == "premium":
                analysis = generate_premium_report(
                    api_keys_str, saju_data, target_year,
                    progress_save_path=str(progress_path),
                )
            else:
                analysis = generate_basic_report(api_keys_str, saju_data, target_year)
        except Exception as e:
            print(f"  ⚠️  AI 분석 오류: {e}")
            analysis = get_sample_analysis(saju_data)

    with open(analysis_path, "w", encoding="utf-8") as f:
        json.dump(analysis, f, ensure_ascii=False, indent=2)
    print(f"  💾 분석 결과 저장: {analysis_path}")

    # ── Step 3: PDF 생성 ────────────────────────────────────────────────────
    print("\n📄 [3/3] 문서 생성 중...")
    prefix   = "[기본]" if rtype == "basic" else "[프리미엄]"
    pdf_path = str(out_dir / f"{prefix} 사주리포트_{user_info['name']}님.pdf")
    try:
        generate_pdf(saju_data, analysis, pdf_path,
                     report_type=rtype, target_year=target_year)
    except Exception as e:
        print(f"  ⚠️  PDF 생성 오류: {e}")
        traceback.print_exc()

    return str(out_dir), pdf_path
