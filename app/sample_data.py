"""
샘플 분석 데이터 (Sample Data).

GEMINI_API_KEYS 가 없거나 API 호출이 전체 실패했을 때
PDF 생성 테스트를 위한 폴백 텍스트를 반환한다.
"""


def get_sample_analysis(saju_data: dict) -> dict:
    """
    사주 데이터 기반으로 간단한 샘플 분석 딕셔너리 생성.

    실제 AI 분석과 동일한 키 구조를 갖추되,
    내용은 Gemini API 키 설정을 유도하는 안내 문구로 채운다.
    """
    name     = saju_data["기본정보"]["이름"]
    ilju     = saju_data["사주원국"]["일주"]["간지"]
    day_stem = saju_data["일간정보"]["일간"]
    elem     = saju_data["일간정보"]["오행"]
    strength = saju_data["일간정보"]["신강신약"]

    _cta = "> Gemini API 키를 설정하면 상세 분석을 받을 수 있습니다."

    return {
        "personality": (
            f"## {ilju}일주 - 타고난 본질 분석\n\n"
            f"### 핵심 기질\n\n"
            f"{name} 님은 {ilju}일주로 태어나셨습니다. "
            f"{day_stem}은(는) {elem} 오행의 에너지를 품고 있으며, "
            f"이는 당신의 근본적인 성품과 삶의 방향성을 결정짓는 핵심 요소입니다.\n\n"
            f"{strength}의 사주 구조는 당신이 세상을 마주하는 방식에 깊은 영향을 미칩니다.\n\n"
            f"### 심리적 구조\n\n타고난 기질상 논리적 사고와 직관이 균형을 이루고 있습니다.\n\n"
            f"### 대인관계 패턴\n\n인간관계에서는 신뢰를 최우선으로 여깁니다.\n\n"
            f"> Gemini API 키를 설정하면 A4 3장 이상의 상세한 분석을 받을 수 있습니다."
        ),
        "wealth":        f"## 재물운 분석\n\n{name} 님의 오행 구조상 안정적인 재물 흐름이 기대됩니다.\n\n{_cta}",
        "career":        f"## 직업운 분석\n\n{_cta}",
        "love":          f"## 연애운 분석\n\n{_cta}",
        "health":        f"## 건강운 분석\n\n{_cta}",
        "lucky_charm":   f"## 개운 가이드\n\n{_cta}",
        "relationships": f"## 인간관계·가족운\n\n{_cta}",
        "fortune_peaks": f"## 인생의 상승기와 저운\n\n{_cta}",
    }
