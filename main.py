"""
AI 사주 리포트 자동화 시스템 — 진입점.

모드 선택만 담당하며 모든 실행 로직은 app/ 레이어에 위임한다.
"""

from dotenv import load_dotenv

from app.user_input import get_user_input, get_api_keys
from app.pipeline import run_pipeline
from app.modes import regenerate_docu_only, reanalyze_from_existing, rerun_partial_premium


def main() -> None:
    load_dotenv()

    print("\n모드 선택:")
    print("  1: 전체 실행 (사주 계산 → AI 분석 → PDF)")
    print("  2: 문서만 재생성 (기존 analysis.json → PDF)")
    print("  3: AI 분석 재실행 (기존 사주 데이터 재사용, 타입 변경 가능)")
    print("  4: 프리미엄 부분 재호출 (중단된 분석 이어하기 / 특정 항목만 재호출)")
    mode = input("\n  선택 > ").strip()

    if mode == "2":
        rtype_input = input("\n리포트 유형 (1: 기본, 2: 프리미엄 / 기본값 1): ").strip()
        rtype       = "premium" if rtype_input == "2" else "basic"
        path        = input("기존 output 폴더 경로 입력: ").strip()
        regenerate_docu_only(path, rtype)
        return

    if mode == "3":
        path         = input("\n기존 output 폴더 경로 입력: ").strip()
        api_keys_str = get_api_keys()
        reanalyze_from_existing(path, api_keys_str)
        return

    if mode == "4":
        path         = input("\n기존 output 폴더 경로 입력: ").strip()
        api_keys_str = get_api_keys()
        rerun_partial_premium(path, api_keys_str)
        return

    # 모드 1: 전체 실행
    api_keys_str = get_api_keys()
    if not api_keys_str:
        print("\n⚠️  API 키 없이 샘플 PDF만 생성합니다.\n")

    user_info = get_user_input()
    run_pipeline(user_info, api_keys_str)


if __name__ == "__main__":
    main()
