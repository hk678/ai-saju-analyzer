"""
실행 모드 핸들러 (Modes).

모드 2: 문서만 재생성   (regenerate_docu_only)
모드 3: AI 분석 재실행  (reanalyze_from_existing)
모드 4: 프리미엄 부분 재호출 (rerun_partial_premium)
"""

import json
import traceback
from datetime import datetime
from pathlib import Path

from analysis.gemini_client import make_key_pool, load_db
from analysis.report_generator import generate_premium_report, generate_basic_report
from analysis.sections_premium import (
    analyze_personality, analyze_wealth, analyze_career,
    analyze_love, analyze_health, analyze_lucky_charm,
    analyze_relationships, analyze_fortune_peaks,
    analyze_monthly_fortune, analyze_yearly_fortune,
)
from pdf.generator import generate_pdf
from app.progress import (
    load_progress, progress_has,
    merge_progress_into_results, build_item_index,
)


# ── 모드 2: 문서만 재생성 ─────────────────────────────────────────────────────

def regenerate_docu_only(out_dir: str, report_type: str = "basic") -> None:
    """기존 saju_data.json + analysis JSON → PDF 재생성."""
    out_dir = Path(out_dir)
    print("\n🔁 문서 재생성 모드")

    prefix = "[기본]" if report_type == "basic" else "[프리미엄]"

    with open(out_dir / "saju_data.json", encoding="utf-8") as f:
        saju_data = json.load(f)

    # 타입별 파일 우선 로드, 없으면 legacy analysis.json 폴백
    typed_filename = "analysis_basic.json" if report_type == "basic" else "analysis_premium.json"
    typed_path     = out_dir / typed_filename
    legacy_path    = out_dir / "analysis.json"

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

    seun_list   = saju_data.get("세운", [])
    target_year = seun_list[0]["연도"] if seun_list else datetime.now().year
    name        = saju_data["기본정보"]["이름"]

    pdf_path = str(out_dir / f"{prefix} 사주리포트_{name}님.pdf")
    try:
        generate_pdf(saju_data, analysis, pdf_path,
                     report_type=report_type, target_year=target_year)
        print(f"✅ PDF 재생성 완료: {pdf_path}")
    except Exception as e:
        print(f"❌ PDF 생성 실패: {e}")
        traceback.print_exc()


# ── 모드 3: AI 분석 재실행 ───────────────────────────────────────────────────

def reanalyze_from_existing(out_dir: str, api_keys_str: str) -> None:
    """
    기존 saju_data.json을 재사용해 AI 분석만 다시 실행 후 PDF 생성.

    - 사주 재계산 없음
    - 리포트 타입을 새로 선택 가능 (기본 ↔ 프리미엄 전환)
    - 결과는 analysis_basic.json / analysis_premium.json 으로 저장
    """
    out_dir   = Path(out_dir)
    saju_path = out_dir / "saju_data.json"

    if not saju_path.exists():
        print(f"\n❌ saju_data.json 을 찾을 수 없습니다: {saju_path}")
        return

    with open(saju_path, encoding="utf-8") as f:
        saju_data = json.load(f)

    name        = saju_data["기본정보"]["이름"]
    seun_list   = saju_data.get("세운", [])
    target_year = seun_list[0]["연도"] if seun_list else datetime.now().year
    ori         = saju_data["사주원국"]

    print(f"\n✅ 사주 데이터 로드 완료: {name} 님")
    print(
        f"   원국: 연{ori['연주']['간지']} 월{ori['월주']['간지']} "
        f"일{ori['일주']['간지']} 시{ori['시주']['간지']}"
    )
    print(f"   기준 연도: {target_year}년")

    rtype_input   = input("\n리포트 유형 선택 (1: 기본, 2: 프리미엄 / 기본값 1): ").strip()
    rtype         = "premium" if rtype_input == "2" else "basic"
    prefix        = "[기본]" if rtype == "basic" else "[프리미엄]"
    analysis_path = out_dir / f"analysis_{rtype}.json"
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

    pdf_path = str(out_dir / f"{prefix} 사주리포트_{name}님.pdf")
    print("\n📄 PDF 생성 중...")
    try:
        generate_pdf(saju_data, analysis, pdf_path,
                     report_type=rtype, target_year=target_year)
        print(f"✅ PDF 생성 완료: {pdf_path}")
    except Exception as e:
        print(f"❌ PDF 생성 오류: {e}")
        traceback.print_exc()


# ── 모드 4: 프리미엄 부분 재호출 ─────────────────────────────────────────────

def rerun_partial_premium(out_dir: str, api_keys_str: str) -> None:
    """
    프리미엄 분석 부분 재호출.

    - analysis_progress.json 에서 완료 항목 파악
    - 미완료 항목 자동 재호출 또는 번호 지정 재호출
    - 완료 후 analysis_premium.json 저장 및 PDF 생성 여부 선택
    """
    out_dir       = Path(out_dir)
    saju_path     = out_dir / "saju_data.json"
    progress_path = out_dir / "analysis_progress.json"

    if not saju_path.exists():
        print(f"\n❌ saju_data.json 을 찾을 수 없습니다: {saju_path}")
        return

    with open(saju_path, encoding="utf-8") as f:
        saju_data = json.load(f)

    existing_progress = load_progress(out_dir)
    items             = build_item_index(saju_data)
    seun_list         = saju_data.get("세운", [])
    wolun_list        = saju_data.get("월운", [])
    target_year       = seun_list[0]["연도"] if seun_list else datetime.now().year

    # ── 현황 출력 ────────────────────────────────────────────────────────────
    print("\n" + "=" * 65)
    print("  📋 프리미엄 분석 항목 현황")
    print("=" * 65)
    done_keys: set    = set()
    missing_keys: set = set()
    for item in items:
        done   = progress_has(existing_progress, item["key"])
        status = "✅" if done else "❌"
        print(f"  {item['no']:>3}. {status} {item['label']}")
        (done_keys if done else missing_keys).add(item["key"])
    total = len(items)
    print("=" * 65)
    print(f"  완료: {len(done_keys)}/{total}개  |  미완료: {len(missing_keys)}개")
    print("=" * 65)

    # ── 재호출 범위 선택 ─────────────────────────────────────────────────────
    print("\n재호출 방식 선택:")
    print("  a: 미완료 항목 전체 자동 재호출")
    print("  n: 번호로 직접 지정  (예: 27  /  16-30  /  5 12 27)")
    print("  q: 취소")
    sel = input("\n  선택 > ").strip().lower()

    if sel in ("q", ""):
        print("  취소합니다.")
        return

    target_keys: set = set()

    if sel == "a":
        target_keys = missing_keys
        if not target_keys:
            print("\n✅ 미완료 항목이 없습니다.")
            return
        print(f"\n  미완료 {len(target_keys)}개 항목을 재호출합니다.")
    else:
        nos: set[int] = set()
        for part in sel.replace(",", " ").split():
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

        no_map  = {item["no"]: item for item in items}
        invalid = nos - set(no_map.keys())
        if invalid:
            print(f"  ⚠️  범위를 벗어난 번호: {sorted(invalid)} — 무시합니다.")

        for no in nos:
            if no in no_map:
                target_keys.add(no_map[no]["key"])

        if not target_keys:
            print("  유효한 항목이 없습니다. 취소합니다.")
            return

        no_map_valid = {item["no"]: item for item in items}
        print(f"\n  재호출 대상 ({len(target_keys)}개):")
        for no in sorted(nos):
            if no in no_map_valid:
                print(f"    - {no_map_valid[no]['label']}")

    confirm = input(
        "\n  위 항목을 API 재호출하시겠습니까? (엔터: 실행 / n: 취소): "
    ).strip().lower()
    if confirm == "n":
        print("  취소합니다.")
        return

    # ── 기존 완료 항목 로드 후 재호출 실행 ──────────────────────────────────
    results: dict = {}
    skip_keys     = done_keys - target_keys
    merge_progress_into_results(results, existing_progress, skip_keys)
    results.setdefault("monthly", {})
    results.setdefault("yearly",  {})

    print(f"\n🤖 AI 부분 재호출 시작 ({len(target_keys)}개 항목)...")

    try:
        pool = make_key_pool(api_keys_str)
        db   = load_db()

        wolun_by_ym = {f"{w['연도']}-{w['월']:02d}": w for w in wolun_list}
        seun_map    = {str(s["연도"]): s for s in seun_list}

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

            print(f"\n  🔄 [{done_in_run + 1}/{len(target_keys)}] {item['label']} 호출 중...")

            if key in _SECTION_FN:
                results[key] = _SECTION_FN[key]()
            elif key.startswith("monthly."):
                ym_str = key.split(".", 1)[1]
                results["monthly"][ym_str] = analyze_monthly_fortune(
                    pool, saju_data, wolun_by_ym[ym_str]
                )
            elif key.startswith("yearly."):
                yr_str = key.split(".")[1]
                results["yearly"][yr_str] = analyze_yearly_fortune(
                    pool, saju_data, seun_map[yr_str]
                )

            # 항목 완료마다 즉시 저장
            with open(progress_path, "w", encoding="utf-8") as f:
                json.dump(results, f, ensure_ascii=False, indent=2)

            done_in_run += 1
            print(f"  ✅ {item['label']} 완료 (저장: {progress_path.name})")

    except Exception as e:
        print(f"\n❌ 부분 재호출 중 오류: {e}")
        traceback.print_exc()
        print(f"   중단 전까지의 결과는 {progress_path} 에 저장돼 있습니다.")
        return

    print(f"\n✅ 부분 재호출 완료 ({done_in_run}개 항목 갱신)")

    # ── 미완료 현황 보고 및 PDF 생성 선택 ────────────────────────────────────
    all_keys  = {item["key"] for item in items}
    now_done  = {item["key"] for item in items if progress_has(results, item["key"])}
    remaining = all_keys - now_done

    if remaining:
        print(f"\n⚠️  아직 미완료 항목이 {len(remaining)}개 있습니다.")
        for item in items:
            if item["key"] in remaining:
                print(f"    ❌ {item['no']}. {item['label']}")
        gen_pdf = input(
            "\n  미완료 항목이 있어도 PDF를 생성하시겠습니까? (y: 생성 / 엔터: 건너뜀): "
        ).strip().lower()
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

        name     = saju_data["기본정보"]["이름"]
        pdf_path = str(out_dir / f"[프리미엄] 사주리포트_{name}님.pdf")
        print("\n📄 PDF 생성 중...")
        try:
            generate_pdf(saju_data, results, pdf_path,
                         report_type="premium", target_year=target_year)
            print(f"✅ PDF 생성 완료: {pdf_path}")
        except Exception as e:
            print(f"❌ PDF 생성 오류: {e}")
            traceback.print_exc()
