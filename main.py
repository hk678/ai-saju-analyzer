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

    # ── 월운 시작 월 ──────────────────────────────────────────────────────
    current_month = datetime.now().month if target_year == current_year else 1
    month_input = input(
        f"월운 시작 월 (엔터: {current_month}월부터 / 1~12 직접 입력): "
    ).strip()
    if month_input.isdigit() and 1 <= int(month_input) <= 12:
        start_month = int(month_input)
    else:
        start_month = current_month

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
        "start_month": start_month,
        "yajasi": yajasi,
    }


def _attach_seun_wolun(saju_data: dict, target_year: int,
                       start_month: int = 1,
                       seun_years: int = 10) -> dict:
    """
    saju_data에 세운/월운 데이터를 추가한다.

    세운: target_year 부터 seun_years 개년치 리스트
    월운: start_month 부터 12개월 (연도 경계를 넘길 수 있음)
    """
    d_stem   = saju_data["일간정보"]["일간"]
    y_branch = saju_data["사주원국"]["연주"]["지지"]
    d_branch = saju_data["사주원국"]["일주"]["지지"]

    saju_data["세운"] = [
        get_seun(target_year + i, d_stem, y_branch, d_branch)
        for i in range(seun_years)
    ]

    wolun = []
    for i in range(12):
        offset = start_month - 1 + i
        m = offset % 12 + 1
        y = target_year + offset // 12
        wolun.append(get_wolun(y, m, d_stem, y_branch, d_branch))
    saju_data["월운"] = wolun

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

    target_year = user_info.get("target_year", datetime.now().year)
    start_month = user_info.get("start_month", 1)
    saju_data = _attach_seun_wolun(saju_data, target_year,
                                   start_month=start_month, seun_years=10)

    # 월운 종료 시점 계산 (로그용)
    end_offset = start_month - 1 + 11
    end_month  = end_offset % 12 + 1
    end_year   = target_year + end_offset // 12

    print(f"\n  ✅ 사주 원국: "
          f"연{saju_data['사주원국']['연주']['간지']} "
          f"월{saju_data['사주원국']['월주']['간지']} "
          f"일{saju_data['사주원국']['일주']['간지']} "
          f"시{saju_data['사주원국']['시주']['간지']}")
    print(f"  ✅ 일간: {saju_data['일간정보']['일간']} "
          f"({saju_data['일간정보']['오행']}) / {saju_data['일간정보']['신강신약']}")
    print(f"  ✅ 대운수: {saju_data['대운수']}")
    print(f"  ✅ 세운 {target_year}~{target_year+9} ({len(saju_data['세운'])}개) 계산 완료")
    print(f"  ✅ 월운 {target_year}년 {start_month}월 ~ {end_year}년 {end_month}월 계산 완료")

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
        saju_data = _attach_seun_wolun(saju_data, target_year,
                                       start_month=start_month, seun_years=10)

        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(saju_data, f, ensure_ascii=False, indent=2)

        print(f"\n  ✅ 수정된 사주 원국: "
              f"연{saju_data['사주원국']['연주']['간지']} "
              f"월{saju_data['사주원국']['월주']['간지']} "
              f"일{saju_data['사주원국']['일주']['간지']} "
              f"시{saju_data['사주원국']['시주']['간지']}")
        print(f"  💾 수정된 데이터 저장: {json_path}")

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
    rtype = user_info["report_type"]
    analysis_filename = "analysis_basic.json" if rtype == "basic" else "analysis_premium.json"
    analysis_path = out_dir / analysis_filename
    progress_path = out_dir / "analysis_progress.json"

    print(f"\n🤖 [2/3] AI 분석 생성 중 ({rtype.upper()})...")
    if not api_keys_str:
        print("  ⚠️  GEMINI_API_KEYS가 없습니다. 샘플 텍스트로 대체합니다.")
        analysis = _get_sample_analysis(saju_data)
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
            analysis = _get_sample_analysis(saju_data)

    with open(analysis_path, "w", encoding="utf-8") as f:
        json.dump(analysis, f, ensure_ascii=False, indent=2)
    print(f"  💾 분석 결과 저장: {analysis_path}")

    # ── Step 3: 문서 생성 ──────────────────────────────────────────────────
    print("\n📄 [3/3] 문서 생성 중...")

    prefix = "[기본]" if rtype == "basic" else "[프리미엄]"
    pdf_path = str(out_dir / f"{prefix} 사주리포트_{user_info['name']}님.pdf")
    try:
        generate_pdf(saju_data, analysis, pdf_path,
                    report_type=rtype, target_year=target_year)
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

    # 타입별 파일 우선 로드, 없으면 legacy analysis.json fallback
    typed_filename = "analysis_basic.json" if report_type == "basic" else "analysis_premium.json"
    typed_path = out_dir / typed_filename
    legacy_path = out_dir / "analysis.json"

    if typed_path.exists():
        analysis_load_path = typed_path
    elif legacy_path.exists():
        print(f"  ⚠️  {typed_filename} 없음 → analysis.json 으로 대체합니다.")
        analysis_load_path = legacy_path
    else:
        print(f"❌ 분석 파일을 찾을 수 없습니다: {typed_path}")
        return

    with open(analysis_load_path, encoding="utf-8") as f:
        analysis = json.load(f)
    print(f"  📂 분석 파일 로드: {analysis_load_path.name}")

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


def _get_api_keys() -> str:
    """환경변수에서 API 키 로드, 없으면 직접 입력받기"""
    api_keys_str = os.environ.get("GEMINI_API_KEYS", "")
    if not api_keys_str:
        print("\n⚠️  GEMINI_API_KEYS 환경변수가 설정되지 않았습니다.")
        manual = input("   Gemini API 키를 콤마로 구분해 입력하세요 (없으면 엔터): ").strip()
        api_keys_str = manual
    return api_keys_str


def reanalyze_from_existing(out_dir: str, api_keys_str: str):
    """
    모드 3: 기존 saju_data.json을 재사용해 AI 분석만 다시 실행 후 PDF 생성.
    - 사주 재계산 없음
    - 리포트 타입을 새로 선택 가능 (기본 ↔ 프리미엄 전환)
    - 결과는 analysis_basic.json / analysis_premium.json 으로 저장
      (기존 analysis.json 은 건드리지 않음)
    """
    out_dir = Path(out_dir)
    saju_path = out_dir / "saju_data.json"

    if not saju_path.exists():
        print(f"\n❌ saju_data.json 을 찾을 수 없습니다: {saju_path}")
        return

    with open(saju_path, encoding="utf-8") as f:
        saju_data = json.load(f)

    name = saju_data["기본정보"]["이름"]
    seun_list = saju_data.get("세운", [])
    target_year = seun_list[0]["연도"] if seun_list else datetime.now().year

    print(f"\n✅ 사주 데이터 로드 완료: {name} 님")
    print(f"   원국: "
          f"연{saju_data['사주원국']['연주']['간지']} "
          f"월{saju_data['사주원국']['월주']['간지']} "
          f"일{saju_data['사주원국']['일주']['간지']} "
          f"시{saju_data['사주원국']['시주']['간지']}")
    print(f"   기준 연도: {target_year}년")

    print("\n리포트 유형 선택:")
    rtype_input = input("  1: 기본, 2: 프리미엄 (기본값 1): ").strip()
    rtype = "premium" if rtype_input == "2" else "basic"
    prefix = "[기본]" if rtype == "basic" else "[프리미엄]"

    # 분석 결과 저장 경로 (기존 analysis.json 덮어쓰지 않음)
    analysis_filename = f"analysis_basic.json" if rtype == "basic" else "analysis_premium.json"
    analysis_path = out_dir / analysis_filename
    progress_path = out_dir / "analysis_progress.json" if rtype == "premium" else None

    print(f"\n🤖 AI 분석 시작 ({rtype.upper()})...")

    try:
        if rtype == "premium":
            analysis = generate_premium_report(
                api_keys_str, saju_data, target_year,
                progress_save_path=str(progress_path),
            )
        else:
            analysis = generate_basic_report(api_keys_str, saju_data, target_year)
    except Exception as e:
        print(f"\n❌ AI 분석 오류: {e}")
        return

    with open(analysis_path, "w", encoding="utf-8") as f:
        json.dump(analysis, f, ensure_ascii=False, indent=2)
    print(f"\n💾 분석 결과 저장: {analysis_path}")

    # PDF 생성
    pdf_path = str(out_dir / f"{prefix} 사주리포트_{name}님.pdf")
    print("\n📄 PDF 생성 중...")
    try:
        generate_pdf(saju_data, analysis, pdf_path,
                     report_type=rtype, target_year=target_year)
        print(f"✅ PDF 생성 완료: {pdf_path}")
    except Exception as e:
        print(f"❌ PDF 생성 오류: {e}")
        import traceback; traceback.print_exc()


# ── 프리미엄 항목 번호 매핑 ────────────────────────────────────────────────────
def _build_item_index(saju_data: dict) -> list[dict]:
    """
    전체 프리미엄 API 호출 항목을 번호 순서대로 리스트로 반환.
    각 항목: {"no": int, "label": str, "key": str}
      key 형식: "personality" / "monthly.2026-05" / "yearly.2026"
    """
    seun_list  = saju_data.get("세운", [])
    wolun_list = saju_data.get("월운", [])

    basic_sections = [
        ("personality",   "성격/본질 분석"),
        ("wealth",        "재물운 분석"),
        ("career",        "직업/직장운 분석"),
        ("love",          "연애/결혼운 분석"),
        ("health",        "건강운 분석"),
        ("lucky_charm",   "개운 가이드"),
        ("relationships", "인간관계·가족운 분석"),
        ("fortune_peaks", "인생 상승기·저운 분석"),
    ]

    items = []
    no = 1
    for key, label in basic_sections:
        items.append({"no": no, "label": label, "key": key})
        no += 1

    # 월운: wolun 객체의 연도/월을 직접 읽어 라벨 생성 (연도 경계 대응)
    for idx, wolun in enumerate(wolun_list):
        yr = wolun["연도"]
        m  = wolun["월"]
        ym_str = f"{yr}-{m:02d}"
        items.append({"no": no, "label": f"{yr}년 {m}월 월운", "key": f"monthly.{ym_str}"})
        no += 1

    for seun in seun_list:
        yr = seun["연도"]
        items.append({"no": no, "label": f"{yr}년 세운", "key": f"yearly.{yr}"})
        no += 1

    return items


def _load_progress(out_dir: Path) -> dict:
    """analysis_progress.json 로드. 없으면 빈 dict 반환."""
    p = out_dir / "analysis_progress.json"
    if p.exists():
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    return {}


def _progress_has(progress: dict, key: str) -> bool:
    """progress dict에서 key 항목이 이미 저장돼 있는지 확인."""
    if "." in key:
        section, sub = key.split(".", 1)
        # JSON 로드 시 키는 항상 str → str로 통일 조회
        return bool(progress.get(section, {}).get(sub))
    return bool(progress.get(key))


def _merge_progress_into_results(results: dict, progress: dict, keys_to_load: set) -> dict:
    """progress에서 keys_to_load 에 해당하는 항목을 results 에 병합."""
    for key in keys_to_load:
        if "." in key:
            section, sub = key.split(".", 1)
            # str 키로 통일
            if section not in results:
                results[section] = {}
            results[section][sub] = progress[section][sub]
        else:
            results[key] = progress[key]
    return results


def rerun_partial_premium(out_dir: str, api_keys_str: str):
    """
    모드 4: 프리미엄 분석 부분 재호출.
    """
    out_dir = Path(out_dir)
    saju_path = out_dir / "saju_data.json"
    progress_path = out_dir / "analysis_progress.json"

    if not saju_path.exists():
        print(f"\n❌ saju_data.json 을 찾을 수 없습니다: {saju_path}")
        return

    with open(saju_path, encoding="utf-8") as f:
        saju_data = json.load(f)

    existing_progress = _load_progress(out_dir)
    items = _build_item_index(saju_data)

    seun_list   = saju_data.get("세운", [])
    wolun_list  = saju_data.get("월운", [])
    target_year = seun_list[0]["연도"] if seun_list else datetime.now().year

    # ── 현재 완료 현황 출력 ──────────────────────────────────────────────────
    print("\n" + "="*65)
    print("  📋 프리미엄 분석 항목 현황")
    print("="*65)
    done_keys = set()
    missing_keys = set()
    for item in items:
        done = _progress_has(existing_progress, item["key"])
        status = "✅" if done else "❌"
        print(f"  {item['no']:>3}. {status} {item['label']}")
        if done:
            done_keys.add(item["key"])
        else:
            missing_keys.add(item["key"])

    total = len(items)
    done_count = len(done_keys)
    print("="*65)
    print(f"  완료: {done_count}/{total}개  |  미완료: {len(missing_keys)}개")
    print("="*65)

    # ── 재호출 범위 선택 ────────────────────────────────────────────────────
    print("\n재호출 방식 선택:")
    print("  a: 미완료 항목 전체 자동 재호출")
    print("  n: 번호로 직접 지정  (예: 27  /  16-30  /  5 12 27)")
    print("  q: 취소")
    sel = input("\n  선택 > ").strip().lower()

    if sel == "q" or sel == "":
        print("  취소합니다.")
        return

    target_keys: set = set()

    if sel == "a":
        target_keys = missing_keys
        if not target_keys:
            print("\n✅ 미완료 항목이 없습니다. 모든 항목이 완료됐습니다.")
        else:
            print(f"\n  미완료 {len(target_keys)}개 항목을 재호출합니다.")
    else:
        nos: set[int] = set()
        parts = sel.replace(",", " ").split()
        for part in parts:
            if "-" in part:
                try:
                    a, b = part.split("-", 1)
                    nos.update(range(int(a), int(b) + 1))
                except ValueError:
                    print(f"  ⚠️  '{part}' 파싱 실패, 무시합니다.")
            elif part.isdigit():
                nos.add(int(part))
            else:
                print(f"  ⚠️  '{part}' 인식 불가, 무시합니다.")

        no_map = {item["no"]: item for item in items}
        invalid = nos - set(no_map.keys())
        if invalid:
            print(f"  ⚠️  범위를 벗어난 번호: {sorted(invalid)} — 무시합니다.")

        for no in nos:
            if no in no_map:
                target_keys.add(no_map[no]["key"])

        if not target_keys:
            print("  유효한 항목이 없습니다. 취소합니다.")
            return

        label_list = [no_map[no]["label"] for no in sorted(nos) if no in no_map]
        print(f"\n  재호출 대상 ({len(target_keys)}개):")
        for lbl in label_list:
            print(f"    - {lbl}")

    confirm = input("\n  위 항목을 API 재호출하시겠습니까? (엔터: 실행 / n: 취소): ").strip().lower()
    if confirm == "n":
        print("  취소합니다.")
        return

    results = {}
    skip_keys = done_keys - target_keys
    _merge_progress_into_results(results, existing_progress, skip_keys)

    if "monthly" not in results:
        results["monthly"] = {}
    if "yearly" not in results:
        results["yearly"] = {}

    print(f"\n🤖 AI 부분 재호출 시작 ({len(target_keys)}개 항목)...")

    try:
        from gemini_analyzer import (
            _make_key_pool, load_db,
            analyze_personality, analyze_wealth, analyze_career,
            analyze_love, analyze_health, analyze_lucky_charm,
            analyze_relationships, analyze_fortune_peaks,
            analyze_monthly_fortune, analyze_yearly_fortune,
        )

        pool = _make_key_pool(api_keys_str)
        db   = load_db()

        # 연도-월 → wolun 객체 매핑
        wolun_by_ym = {f"{w['연도']}-{w['월']:02d}": w for w in wolun_list}
        seun_map     = {str(s["연도"]): s for s in seun_list}

        _SECTION_FN = {
            "personality":   lambda: analyze_personality(pool, saju_data, db),
            "wealth":        lambda: analyze_wealth(pool, saju_data, db),
            "career":        lambda: analyze_career(pool, saju_data, db),
            "love":          lambda: analyze_love(pool, saju_data, db),
            "health":        lambda: analyze_health(pool, saju_data, db),
            "lucky_charm":   lambda: analyze_lucky_charm(pool, saju_data, db),
            "relationships": lambda: analyze_relationships(pool, saju_data, db),
            "fortune_peaks": lambda: analyze_fortune_peaks(pool, saju_data, db),
        }

        done_in_run = 0
        for item in items:
            key = item["key"]
            if key not in target_keys:
                continue

            print(f"\n  🔄 [{done_in_run+1}/{len(target_keys)}] {item['label']} 호출 중...")

            if key in _SECTION_FN:
                results[key] = _SECTION_FN[key]()
            elif key.startswith("monthly."):
                ym_str = key.split(".", 1)[1]    # "2026-05" 형식
                wolun = wolun_by_ym[ym_str]
                results["monthly"][ym_str] = analyze_monthly_fortune(pool, saju_data, wolun)
            elif key.startswith("yearly."):
                yr_str = key.split(".")[1]       # "2026" 등 문자열
                results["yearly"][yr_str] = analyze_yearly_fortune(pool, saju_data, seun_map[yr_str])

            with open(progress_path, "w", encoding="utf-8") as f:
                json.dump(results, f, ensure_ascii=False, indent=2)

            done_in_run += 1
            print(f"  ✅ {item['label']} 완료 (저장: {progress_path.name})")

    except Exception as e:
        print(f"\n❌ 부분 재호출 중 오류: {e}")
        import traceback; traceback.print_exc()
        print(f"   중단 전까지의 결과는 {progress_path} 에 저장돼 있습니다.")
        return

    print(f"\n✅ 부분 재호출 완료 ({done_in_run}개 항목 갱신)")

    all_keys  = {item["key"] for item in items}
    now_done  = {item["key"] for item in items if _progress_has(results, item["key"])}
    remaining = all_keys - now_done

    if remaining:
        print(f"\n⚠️  아직 미완료 항목이 {len(remaining)}개 있습니다.")
        for item in items:
            if item["key"] in remaining:
                print(f"    ❌ {item['no']}. {item['label']}")
        gen_pdf = input("\n  미완료 항목이 있어도 PDF를 생성하시겠습니까? (y: 생성 / 엔터: 건너뜀): ").strip().lower()
    else:
        print("\n🎉 모든 항목 완료!")
        gen_pdf = input("  PDF를 생성하시겠습니까? (엔터: 생성 / n: 건너뜀): ").strip().lower()
        if gen_pdf != "n":
            gen_pdf = "y"

    if gen_pdf == "y":
        analysis_path = out_dir / "analysis_premium.json"
        with open(analysis_path, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print(f"  💾 분석 결과 저장: {analysis_path}")

        name = saju_data["기본정보"]["이름"]
        pdf_path = str(out_dir / f"[프리미엄] 사주리포트_{name}님.pdf")
        print("\n📄 PDF 생성 중...")
        try:
            generate_pdf(saju_data, results, pdf_path,
                         report_type="premium", target_year=target_year)
            print(f"✅ PDF 생성 완료: {pdf_path}")
        except Exception as e:
            print(f"❌ PDF 생성 오류: {e}")
            import traceback; traceback.print_exc()


if __name__ == "__main__":
    load_dotenv()

    print("\n모드 선택:")
    print("  1: 전체 실행 (사주 계산 → AI 분석 → PDF)")
    print("  2: 문서만 재생성 (기존 analysis.json → PDF)")
    print("  3: AI 분석 재실행 (기존 사주 데이터 재사용, 타입 변경 가능)")
    print("  4: 프리미엄 부분 재호출 (중단된 분석 이어하기 / 특정 항목만 재호출)")
    mode = input("\n  선택 > ").strip()

    if mode == "2":
        print("\n리포트 유형 선택:")
        rtype_input = input("  1: 기본, 2: 프리미엄 (기본값 1): ").strip()
        rtype = "premium" if rtype_input == "2" else "basic"
        path = input("\n기존 output 폴더 경로 입력: ").strip()
        regenerate_docu_only(path, rtype)
        exit()

    if mode == "3":
        path = input("\n기존 output 폴더 경로 입력: ").strip()
        api_keys_str = _get_api_keys()
        reanalyze_from_existing(path, api_keys_str)
        exit()

    if mode == "4":
        path = input("\n기존 output 폴더 경로 입력: ").strip()
        api_keys_str = _get_api_keys()
        rerun_partial_premium(path, api_keys_str)
        exit()

    # 모드 1: 전체 실행
    api_keys_str = _get_api_keys()
    if not api_keys_str:
        print("\n⚠️  API 키 없이 샘플 PDF만 생성합니다.\n")

    user_info = get_user_input()
    run_pipeline(user_info, api_keys_str)