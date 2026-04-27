"""
AI 사주 리포트 자동화 시스템 - 메인 실행 파일
"""

import os
import sys
import json
import shutil
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(__file__))

from saju_calculator import (
    calculate_saju, get_seun, get_wolun,
    recalculate_from_pillars,
    STEMS, STEMS_KR, BRANCHES, BRANCHES_KR,
)
from gemini_analyzer import generate_premium_report, generate_basic_report
from pdf_generator import generate_pdf


def get_user_input() -> dict:
    """사용자 정보 입력받기"""
    print("\n" + "="*60)
    print("   ✦ AI 사주 리포트 자동화 시스템 ✦")
    print("="*60 + "\n")

    name   = input("이름: ").strip() or "홍길동"
    birth  = input("생년월일 (예: 1990-05-15): ").strip() or "1990-05-15"
    hour   = input("태어난 시각 - 시 (예: 05, 모르면 엔터): ").strip() or "10"
    minute = input("태어난 시각 - 분 (예: 30, 모르면 엔터): ").strip() or "0"

    # ── 자시(23:30~01:29) 범위일 때 야자시 여부 추가 질문 ──────────────────
    yajasi = False
    try:
        h_check  = int(hour)
        mi_check = int(minute)
        total_check = h_check * 60 + mi_check
        is_jasi = total_check >= 23 * 60 + 30 or total_check < 1 * 60 + 30
    except ValueError:
        is_jasi = False

    if is_jasi:
        print("\n  ⏰ 입력하신 시각이 자시(子時, 23:30~01:29) 범위입니다.")
        print("     야자시(夜子時) 적용 여부에 따라 일주·시주가 달라집니다.")
        print("     - 야자시 적용  : 23:30 이후를 다음날로 간주 (현대 명리)")
        print("     - 야자시 미적용: 자정(00:00) 기준 날짜 전환 (전통 방식)")
        ya_input = input("  야자시를 적용하시겠습니까? (y: 적용 / 엔터: 미적용): ").strip().lower()
        yajasi = (ya_input == "y")

    gender = input("\n성별 (남/여): ").strip() or "남"
    rtype_input = input("리포트 유형 (1: 기본, 2: 프리미엄 (기본값 1)): ").strip()
    rtype = "premium" if rtype_input == "2" else "basic"

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
        "yajasi": yajasi,
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


def _correct_pillars(saju_data: dict) -> dict:
    """
    사주 원국 8글자를 사용자가 직접 수정하고 모든 파생 데이터를 재계산한다.

    천간: 甲갑 乙을 丙병 丁정 戊무 己기 庚경 辛신 壬임 癸계
    지지: 子자 丑축 寅인 卯묘 辰진 巳사 午오 未미 申신 酉유 戌술 亥해
    """
    STEM_DISPLAY   = "  甲갑 乙을 丙병 丁정 戊무 己기 庚경 辛신 壬임 癸계"
    BRANCH_DISPLAY = "  子자 丑축 寅인 卯묘 辰진 巳사 午오 未미 申신 酉유 戌술 亥해"

    # 독음 → 한자 매핑
    kr_to_stem   = dict(zip(STEMS_KR,   STEMS))
    kr_to_branch = dict(zip(BRANCHES_KR, BRANCHES))

    def _pick(label: str, mapping: dict, display: str, current_char: str) -> str:
        """독음 입력 → 한자 반환. 엔터 입력 시 현재값 유지."""
        while True:
            raw = input(f"    {label} [{current_char}] (엔터: 유지)\n"
                        f"{display}\n    > ").strip().lower()
            if raw == "":
                return current_char
            if raw in mapping:
                return mapping[raw]
            print(f"    ⚠️  '{raw}' 을 인식할 수 없습니다. 다시 입력하세요.")

    orig = saju_data["사주원국"]
    pillar_labels = [("연주", "연"), ("월주", "월"), ("일주", "일"), ("시주", "시")]

    print("\n" + "="*60)
    print("  📝 사주 원국 수정")
    print("  수정할 주(柱)를 선택하세요. 여러 개 선택 가능합니다.")
    print("  예) 1 3  또는  전체  또는  엔터(건너뜀)")
    print("  1: 연주  2: 월주  3: 일주  4: 시주")
    print("="*60)

    sel_raw = input("  선택 > ").strip()
    if sel_raw == "" :
        print("  수정 없이 계속합니다.")
        return saju_data

    if "전체" in sel_raw:
        targets = {1, 2, 3, 4}
    else:
        targets = set()
        for ch in sel_raw.split():
            if ch.isdigit() and 1 <= int(ch) <= 4:
                targets.add(int(ch))

    if not targets:
        print("  선택값이 없습니다. 수정 없이 계속합니다.")
        return saju_data

    new_pillars = {}
    for idx, (key, short) in enumerate(pillar_labels, start=1):
        if idx not in targets:
            # 수정 대상 아님 → 기존값 그대로
            new_pillars[key] = (orig[key]["천간"], orig[key]["지지"])
            continue

        cur_stem   = orig[key]["천간"]
        cur_branch = orig[key]["지지"]
        print(f"\n  ── {key} (현재: {cur_stem}{cur_branch}) ──")

        new_stem   = _pick(f"{short}주 천간", kr_to_stem,   STEM_DISPLAY,   cur_stem)
        new_branch = _pick(f"{short}주 지지", kr_to_branch, BRANCH_DISPLAY, cur_branch)
        new_pillars[key] = (new_stem, new_branch)

        print(f"  → {key}: {new_stem}{new_branch}")

    return recalculate_from_pillars(
        existing_data = saju_data,
        y_stem   = new_pillars["연주"][0], y_branch = new_pillars["연주"][1],
        m_stem   = new_pillars["월주"][0], m_branch = new_pillars["월주"][1],
        d_stem   = new_pillars["일주"][0], d_branch = new_pillars["일주"][1],
        h_stem   = new_pillars["시주"][0], h_branch = new_pillars["시주"][1],
    )


def run_pipeline(user_info: dict, api_keys_str: str):
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
        user_info.get("yajasi", False),
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
    answer = input("  계속 진행하시겠습니까? (엔터: 계속 / c: 간지 수정 / n: 중단): ").strip().lower()
    if answer == "n":
        print("\n⛔ 사용자 요청으로 중단되었습니다.")
        print(f"   저장된 JSON: {json_path}")
        print("   이후 단계만 실행하려면 모드 2(PDF 재생성)를 이용하세요.\n")
        return str(out_dir), None

    while answer == "c":
        saju_data = _correct_pillars(saju_data)

        # 세운/월운을 수정된 간지 기준으로 재계산
        saju_data = _attach_seun_wolun(saju_data, target_year, seun_years=10)

        # JSON 덮어쓰기
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(saju_data, f, ensure_ascii=False, indent=2)

        print(f"\n  ✅ 수정된 사주 원국: "
              f"연{saju_data['사주원국']['연주']['간지']} "
              f"월{saju_data['사주원국']['월주']['간지']} "
              f"일{saju_data['사주원국']['일주']['간지']} "
              f"시{saju_data['사주원국']['시주']['간지']}")
        print(f"  💾 수정된 데이터 저장: {json_path}")

        # 수정 후 재확인 대기
        print("\n" + "-"*60)
        print(f"  📂 {json_path} 를 열어 사주 데이터를 확인하세요.")
        print("-"*60)
        answer = input("  계속 진행하시겠습니까? (엔터: 계속 / c: 간지 수정 / n: 중단): ").strip().lower()
        if answer == "n":
            print("\n⛔ 사용자 요청으로 중단되었습니다.")
            print(f"   저장된 JSON: {json_path}")
            print("   이후 단계만 실행하려면 모드 2(PDF 재생성)를 이용하세요.\n")
            return str(out_dir), None

    # ── Step 2: AI 분석 ─────────────────────────────────────────────────────
    print(f"\n🤖 [2/3] AI 분석 생성 중 ({user_info['report_type'].upper()})...")
    if not api_keys_str:
        print("  ⚠️  GEMINI_API_KEYS가 없습니다. 샘플 텍스트로 대체합니다.")
        analysis = _get_sample_analysis(saju_data)
    else:
        try:
            if user_info["report_type"] == "premium":
                analysis = generate_premium_report(api_keys_str, saju_data, target_year)
            else:
                analysis = generate_basic_report(api_keys_str, saju_data, target_year)
        except Exception as e:
            print(f"  ⚠️  AI 분석 오류: {e}")
            analysis = _get_sample_analysis(saju_data)

    with open(out_dir / "analysis.json", "w", encoding="utf-8") as f:
        json.dump(analysis, f, ensure_ascii=False, indent=2)

    # ── Step 3: 문서 생성 ──────────────────────────────────────────────────
    print("\n📄 [3/3] 문서 생성 중...")

    # PDF 생성
    prefix = "[기본]" if user_info["report_type"] == "basic" else "[프리미엄]"
    pdf_path = str(out_dir / f"{prefix} 사주리포트_{user_info['name']}님.pdf")
    try:
        generate_pdf(saju_data, analysis, pdf_path,
                    report_type=user_info["report_type"], target_year=target_year)
    except Exception as e:
        print(f"  ⚠️  PDF 생성 오류: {e}")
        import traceback; traceback.print_exc()

    return str(out_dir), pdf_path


def regenerate_docu_only(out_dir: str, report_type: str = "basic"):
    out_dir = Path(out_dir)
    print("\n🔁 문서 재생성 모드")

    prefix = "[기본]" if report_type == "basic" else "[프리미엄]"

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

    # PDF 재생성
    pdf_path = str(out_dir / f"{prefix} 사주리포트_{name}님.pdf")
    try:
        generate_pdf(saju_data, analysis, pdf_path, report_type=report_type, target_year=target_year)
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
    mode = input("  1: 전체 실행, 2: 문서만 재생성: ").strip()

    if mode == "2":
        print("\n리포트 유형 선택:")
        rtype_input = input("  1: 기본, 2: 프리미엄 (기본값 1): ").strip()
        rtype = "premium" if rtype_input == "2" else "basic"
        path = input("\n기존 output 폴더 경로 입력: ").strip()
        regenerate_docu_only(path, rtype)
        exit()

    api_keys_str = os.environ.get("GEMINI_API_KEYS", "")
    if not api_keys_str:
        print("\n⚠️  GEMINI_API_KEYS 환경변수가 설정되지 않았습니다.")
        print("   AI 분석 없이 샘플 PDF만 생성합니다.\n")
        manual = input("   Gemini API 키를 콤마로 구분해 입력하세요 (없으면 엔터): ").strip()
        api_keys_str = manual

    user_info = get_user_input()
    run_pipeline(user_info, api_keys_str)