"""
프리미엄 분석 진행 상태 관리 (Progress Manager).

담당 기능:
  - analysis_progress.json 로드
  - key 존재 여부 확인
  - progress → results 병합
  - 전체 항목 인덱스 빌드
"""

import json
from pathlib import Path


def load_progress(out_dir: Path) -> dict:
    """analysis_progress.json 로드. 없으면 빈 dict 반환."""
    p = out_dir / "analysis_progress.json"
    if p.exists():
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    return {}


def progress_has(progress: dict, key: str) -> bool:
    """
    progress dict에 key 항목이 이미 저장돼 있는지 확인.

    key 형식:
      "personality"        → 최상위 키 조회
      "monthly.2026-05"   → progress["monthly"]["2026-05"] 조회
      "yearly.2026"       → progress["yearly"]["2026"] 조회
    """
    if "." in key:
        section, sub = key.split(".", 1)
        return bool(progress.get(section, {}).get(sub))
    return bool(progress.get(key))


def merge_progress_into_results(
    results: dict, progress: dict, keys_to_load: set
) -> dict:
    """progress에서 keys_to_load 에 해당하는 항목을 results 에 병합."""
    for key in keys_to_load:
        if "." in key:
            section, sub = key.split(".", 1)
            if section not in results:
                results[section] = {}
            results[section][sub] = progress[section][sub]
        else:
            results[key] = progress[key]
    return results


def build_item_index(saju_data: dict) -> list[dict]:
    """
    전체 프리미엄 API 호출 항목을 번호 순서대로 리스트로 반환.

    반환 항목 구조:
        {"no": int, "label": str, "key": str}

    key 형식: "personality" / "monthly.2026-05" / "yearly.2026"
    """
    seun_list  = saju_data.get("세운", [])
    wolun_list = saju_data.get("월운", [])

    _BASIC_SECTIONS = [
        ("personality",   "성격/본질 분석"),
        ("wealth",        "재물운 분석"),
        ("career",        "직업/직장운 분석"),
        ("love",          "연애/결혼운 분석"),
        ("health",        "건강운 분석"),
        ("lucky_charm",   "개운 가이드"),
        ("relationships", "인간관계·가족운 분석"),
        ("fortune_peaks", "인생 상승기·저운 분석"),
    ]

    items: list[dict] = []
    no = 1

    for key, label in _BASIC_SECTIONS:
        items.append({"no": no, "label": label, "key": key})
        no += 1

    for wolun in wolun_list:
        yr     = wolun["연도"]
        m      = wolun["월"]
        ym_str = f"{yr}-{m:02d}"
        items.append({"no": no, "label": f"{yr}년 {m}월 월운", "key": f"monthly.{ym_str}"})
        no += 1

    for seun in seun_list:
        yr = seun["연도"]
        items.append({"no": no, "label": f"{yr}년 세운", "key": f"yearly.{yr}"})
        no += 1

    return items
