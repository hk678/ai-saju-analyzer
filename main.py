"""
AI 사주 리포트 자동화 시스템 - 메인 실행 파일
사용법:
    python main.py
    또는 API 키를 환경변수로 설정:
    export GEMINI_API_KEY=""
    python main.py
"""

import os
import sys
import json
import shutil
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(__file__))

from saju_calculator import calculate_saju, get_seun, get_wolun
from visualizer import draw_element_chart, draw_sipsung_chart, draw_daewun_flow
from gemini_analyzer import generate_premium_report, generate_basic_report
from pdf_generator import generate_pdf
from word_generator import generate_word


def get_user_input() -> dict:
    """사용자 정보 입력받기"""
    print("\n" + "="*60)
    print("   ✦ AI 사주 리포트 자동화 시스템 ✦")
    print("="*60 + "\n")

    name   = input("이름을 입력하세요: ").strip() or "홍길동"
    birth  = input("생년월일을 입력하세요 (예: 1990-05-15): ").strip() or "1990-05-15"
    hour   = input("태어난 시각 - 시 (예: 10, 모르면 엔터): ").strip() or "10"
    minute = input("태어난 시각 - 분 (예: 30, 모르면 엔터): ").strip() or "0"
    gender = input("성별을 입력하세요 (남/여): ").strip() or "남"
    rtype  = input("리포트 유형 (basic/premium, 기본값 basic): ").strip() or "basic"

    current_year = datetime.now().year
    year_input = input(
        f"운세 기준 연도 (엔터: {current_year}년 / 다른 연도 예: {current_year+1}): "
    ).strip()
    if year_input.isdigit() and 2000 <= int(year_input) <= 2100:
        target_year = int(year_input)
    else:
        target_year = current_year

    try:
        y, m, d = map(int, birth.split("-"))
        h  = int(hour)
        mi = int(minute)
    except Exception:
        print("날짜 형식 오류. 기본값으로 진행합니다.")
        y, m, d, h, mi = 1990, 5, 15, 10, 0

    return {
        "name": name,
        "year": y, "month": m, "day": d,
        "hour": h, "minute": mi,
        "gender": gender,
        "report_type": rtype,
        "target_year": target_year,
    }


def _attach_seun_wolun(saju_data: dict, target_year: int, seun_years: int = 10) -> dict:
    """
    saju_data에 세운/월운 데이터를 추가한다.

    세운: target_year 부터 seun_years 개년치 리스트
    월운: target_year 의 12개월 리스트

    신살 계산 시 년지·일지 이중 기준 + 일간 기준 적용.
    """
    d_stem   = saju_data["일간정보"]["일간"]
    y_branch = saju_data["사주원국"]["연주"]["지지"]
    d_branch = saju_data["사주원국"]["일주"]["지지"]

    saju_data["세운"] = [
        get_seun(target_year + i, d_stem, y_branch, d_branch)
        for i in range(seun_years)
    ]
    saju_data["월운"] = [
        get_wolun(target_year, m, d_stem, y_branch, d_branch)
        for m in range(1, 13)
    ]
    return saju_data


def run_pipeline(user_info: dict, api_key: str):
    """전체 파이프라인 실행"""

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = Path(f"outputs/saju_{user_info['name']}_{timestamp}")
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n📁 출력 디렉토리: {out_dir}")

    # ── Step 1: 만세력 계산 ──────────────────────────────────────────────────
    print("\n🔢 [1/4] 만세력 계산 중...")
    saju_data = calculate_saju(
        user_info["name"],
        user_info["year"], user_info["month"], user_info["day"],
        user_info["hour"], user_info["gender"],
        user_info.get("minute", 0),
    )

    # 세운 / 월운 계산 후 saju_data에 첨부
    target_year = user_info.get("target_year", datetime.now().year)
    saju_data = _attach_seun_wolun(saju_data, target_year, seun_years=10)

    print(f"\n  ✅ 사주 원국: "
          f"연{saju_data['사주원국']['연주']['간지']} "
          f"월{saju_data['사주원국']['월주']['간지']} "
          f"일{saju_data['사주원국']['일주']['간지']} "
          f"시{saju_data['사주원국']['시주']['간지']}")
    print(f"  ✅ 일간: {saju_data['일간정보']['일간']} "
          f"({saju_data['일간정보']['오행']}) / {saju_data['일간정보']['신강신약']}")
    print(f"  ✅ 대운수: {saju_data['대운수']}")
    print(f"  ✅ 세운 {target_year}~{target_year+9} ({len(saju_data['세운'])}개) 계산 완료")
    print(f"  ✅ 월운 {target_year}년 12개월 계산 완료")

    # JSON 저장
    json_path = out_dir / "saju_data.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(saju_data, f, ensure_ascii=False, indent=2)
    print(f"\n  💾 사주 데이터 저장: {json_path}")

    # ── 일시정지: JSON 확인 후 진행 여부 선택 ──────────────────────────────
    print("\n" + "-"*60)
    print(f"  📂 {json_path} 를 열어 사주 데이터를 확인하세요.")
    print("-"*60)
    answer = input("  계속 진행하시겠습니까? (엔터: 계속 / n: 중단): ").strip().lower()
    if answer == "n":
        print("\n⛔ 사용자 요청으로 중단되었습니다.")
        print(f"   저장된 JSON: {json_path}")
        print("   이후 단계만 실행하려면 모드 2(PDF 재생성)를 이용하세요.\n")
        return str(out_dir), None

    # ── Step 2: 차트 생성 ───────────────────────────────────────────────────
    print("\n📊 [2/4] 시각화 차트 생성 중...")
    chart_paths = {}

    try:
        chart_paths["elements"] = str(draw_element_chart(saju_data, str(out_dir / "chart_elements.png")))
        print("  ✅ 오행 분포 차트 완료")
    except Exception as e:
        print(f"  ⚠️  오행 차트 오류: {e}")

    try:
        chart_paths["sipsung"] = str(draw_sipsung_chart(saju_data, str(out_dir / "chart_sipsung.png")))
        print("  ✅ 십성 분포 차트 완료")
    except Exception as e:
        print(f"  ⚠️  십성 차트 오류: {e}")

    try:
        chart_paths["daewun"] = str(draw_daewun_flow(saju_data, str(out_dir / "chart_daewun.png")))
        print("  ✅ 대운 흐름 차트 완료")
    except Exception as e:
        print(f"  ⚠️  대운 차트 오류: {e}")

    # ── Step 3: AI 분석 ─────────────────────────────────────────────────────
    print(f"\n🤖 [3/4] AI 분석 생성 중 ({user_info['report_type'].upper()})...")
    if not api_key:
        print("  ⚠️  GEMINI_API_KEY가 없습니다. 샘플 텍스트로 대체합니다.")
        analysis = _get_sample_analysis(saju_data)
    else:
        try:
            if user_info["report_type"] == "premium":
                analysis = generate_premium_report(api_key, saju_data, target_year)
            else:
                analysis = generate_basic_report(api_key, saju_data, target_year)
        except Exception as e:
            print(f"  ⚠️  AI 분석 오류: {e}")
            analysis = _get_sample_analysis(saju_data)

    with open(out_dir / "analysis.json", "w", encoding="utf-8") as f:
        json.dump(analysis, f, ensure_ascii=False, indent=2)

    # ── Step 4: 문서 생성 ──────────────────────────────────────────────────
    print("\n📄 [4/4] 문서 생성 중...")

    # Word 생성
    # word_path = str(out_dir / f"사주리포트_{user_info['name']}.docx")
    # try:
    #     generate_word(saju_data, analysis, word_path,
    #                 user_info["report_type"], target_year)
    # except Exception as e:
    #     print(f"  ⚠️  Word 생성 오류: {e}")
    #     import traceback; traceback.print_exc()
    
    # return str(out_dir), word_path

    # PDF 생성
    pdf_path = str(out_dir / f"사주리포트_{user_info['name']}.pdf")
    try:
        generate_pdf(saju_data, analysis, pdf_path, chart_paths,
                    user_info["report_type"], target_year)
    except Exception as e:
        print(f"  ⚠️  PDF 생성 오류: {e}")
        import traceback; traceback.print_exc()

    return str(out_dir), pdf_path


def regenerate_docu_only(out_dir: str):
    out_dir = Path(out_dir)
    print("\n🔁 문서 재생성 모드")

    with open(out_dir / "saju_data.json", encoding="utf-8") as f:
        saju_data = json.load(f)
    with open(out_dir / "analysis.json", encoding="utf-8") as f:
        analysis = json.load(f)

    chart_paths = {
        "elements": str(out_dir / "chart_elements.png"),
        "sipsung":  str(out_dir / "chart_sipsung.png"),
        "daewun":   str(out_dir / "chart_daewun.png"),
    }
    name = saju_data['기본정보']['이름']
    seun_list   = saju_data.get("세운", [])
    target_year = seun_list[0]["연도"] if seun_list else datetime.now().year

    # Word 재생성
    # word_path = str(out_dir / f"사주리포트_{name}.docx")
    # try:
    #     generate_word(saju_data, analysis, word_path, "basic", target_year)
    #     print(f"✅ Word 재생성 완료: {word_path}")
    # except Exception as e:
    #     print(f"❌ Word 생성 실패: {e}")
    #     import traceback; traceback.print_exc()

    # PDF 재생성
    pdf_path = str(out_dir / f"사주리포트_{name}.pdf")
    try:
        generate_pdf(saju_data, analysis, pdf_path, chart_paths, "basic", target_year)
        print(f"✅ PDF 재생성 완료: {pdf_path}")
    except Exception as e:
        print(f"❌ PDF 생성 실패: {e}")
        import traceback; traceback.print_exc()


def _get_sample_analysis(saju_data: dict) -> dict:
    name     = saju_data["기본정보"]["이름"]
    ilju     = saju_data["사주원국"]["일주"]["간지"]
    day_stem = saju_data["일간정보"]["일간"]
    elem     = saju_data["일간정보"]["오행"]
    strength = saju_data["일간정보"]["신강신약"]

    return {
        "personality": f"""## {ilju}일주 - 타고난 본질 분석

### 핵심 기질

{name} 님은 **{ilju}일주**로 태어나셨습니다. {day_stem}은(는) {elem} 오행의 에너지를 품고 있으며, 이는 당신의 근본적인 성품과 삶의 방향성을 결정짓는 핵심 요소입니다.

{strength}의 사주 구조는 당신이 세상을 마주하는 방식에 깊은 영향을 미칩니다.

### 심리적 구조

타고난 기질상 논리적 사고와 직관이 균형을 이루고 있습니다.

### 대인관계 패턴

인간관계에서는 신뢰를 최우선으로 여깁니다.

>  **Gemini API 키를 설정하면 A4 3장 이상의 상세한 분석을 받을 수 있습니다.**""",

        "wealth":      f"## 재물운 분석\n\n{name} 님의 오행 구조상 **안정적인 재물 흐름**이 기대됩니다.\n\n>  Gemini API 키를 설정하면 상세 분석을 받을 수 있습니다.",
        "career":      "## 직업운 분석\n\n>  Gemini API 키를 설정하면 직업운 상세 분석을 받을 수 있습니다.",
        "love":        "## 연애운 분석\n\n>  Gemini API 키를 설정하면 연애운 상세 분석을 받을 수 있습니다.",
        "health":      "## 건강운 분석\n\n>  Gemini API 키를 설정하면 건강운 상세 분석을 받을 수 있습니다.",
        "lucky_charm": "## 개운 가이드\n\n>  Gemini API 키를 설정하면 맞춤형 개운 가이드를 받을 수 있습니다.",
    }


if __name__ == "__main__":
    load_dotenv()

    print("\n모드 선택:")
    print("  1: 전체 실행 (만세력 → AI 분석 → PDF)")
    print("  2: 문서만 재생성 (기존 JSON 사용)")
    mode = input("선택 (1/2): ").strip()

    if mode == "2":
        path = input("기존 output 폴더 경로 입력: ").strip()
        regenerate_docu_only(path)
        exit()

    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        print("\n⚠️  GEMINI_API_KEY 환경변수가 설정되지 않았습니다.")
        print("   AI 분석 없이 샘플 PDF만 생성합니다.\n")
        api_key = input("   Gemini API 키를 입력하세요 (없으면 엔터): ").strip()

    user_info = get_user_input()
    run_pipeline(user_info, api_key)