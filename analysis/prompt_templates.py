"""
프롬프트 템플릿 모음 (Prompt Templates).

각 함수는 순수하게 프롬프트 문자열만 반환한다.
API 호출 로직을 포함하지 않는다.

공통 제약 블록(COMMON_RESTRICTIONS)을 상수로 추출하여
11개 섹션에서 중복 없이 재사용한다.
"""

import json

from analysis.prompt_builder import build_origin_context, current_year_from_saju

# ── 공통 제약 블록 ────────────────────────────────────────────────────────────
# 모든 섹션 프롬프트에 동일하게 삽입되는 금지 패턴 및 문체 규칙.
# 섹션별로 미묘하게 다른 "대신:" 문구는 각 템플릿에서 직접 작성한다.

COMMON_RESTRICTIONS = """\
※ 영어 단어 사용을 금지하고, 반드시 한국어 표현으로 풀어 쓸 것
※ 외래어 사용 시에도 한글 표현을 우선하며, 불가피한 경우에도 괄호 속 영어 병기는 금지

※ 금지 패턴: "OO(한자)이/가 있어 ~한 경향이 있습니다" 구조로 쓰지 말 것
※ 금지 패턴: "OO의 기운이 강하게 자리 잡고 있어 ~" 로 문장을 시작하지 말 것
※ 금지 패턴: "이는 ~을 의미합니다" "따라서 ~한 사람입니다" 같은 결론 도출 패턴 금지
※ "~해야 합니다", "~경계해야 합니다", "~필요합니다"가 한 단락에 2번 이상 나오지 않도록 할 것"""

_HEADING_RULES = """\
※ 인사말·본인 소개 없이 ## 소제목으로 바로 시작할 것
※ 소제목은 반드시 ## 형식만 사용하고, 소제목에 번호(1. 2. 3. 등)를 절대 붙이지 말 것"""


# ── 프리미엄 섹션 프롬프트 ────────────────────────────────────────────────────

def build_prompt_personality(saju_data: dict, db: dict) -> str:
    """섹션 1: 타고난 본질 및 성격 분석 (A4 3장 이상)"""
    day_stem   = saju_data["일간정보"]["일간"]
    day_branch = saju_data["사주원국"]["일주"]["지지"]
    ilju       = saju_data["사주원국"]["일주"]["간지"]
    full_name  = saju_data["기본정보"]["이름"]

    stem_info   = db.get("천간", {}).get(day_stem, {})
    branch_info = db.get("지지", {}).get(day_branch, {})
    origin_ctx  = build_origin_context(saju_data, current_year_from_saju(saju_data))

    return f"""
[분석 대상 사주 데이터]
이름: {full_name}
생년월일: {saju_data['기본정보']['생년월일']}
성별: {saju_data['기본정보']['성별']}
음력: {saju_data['기본정보'].get('음력', '')}

{origin_ctx}

[일간 참고 데이터]
{day_stem}일간 특성: {json.dumps(stem_info, ensure_ascii=False)}
일지 {day_branch} 특성: {json.dumps(branch_info, ensure_ascii=False)}

[작성 요청]
위 사주 데이터를 바탕으로 '타고난 본질과 성격 분석' 파트를 1,500자(A4 3장) 이상 2,000자 이내 분량으로 작성해주세요.
{_HEADING_RULES}
※ 각 번호의 첫 줄(예: "대인관계 패턴")만 ## 소제목으로 사용할 것
※ "- 작성 내용:" 이후 문장은 소제목이 아니라 본문에서 반드시 풀어서 설명할 것
※ 소제목에는 ':' 또는 추가 설명을 절대 포함하지 말 것
※ 의뢰인 호칭은 반드시 '{full_name} 님'으로만 표기할 것 (성 생략 금지)

{COMMON_RESTRICTIONS}
※ 대신: 이 사람이 실제로 어떤 상황에서 어떻게 행동하는지를 먼저 구체적으로 쓰고,
         사주 근거는 뒤에서 짧게 한 번만 언급하거나 생략할 것

[소제목 및 작성 가이드]
1) 일주(일간+일지)의 핵심 기질
  - 작성 내용: {ilju}일주가 가진 근본적 에너지와 삶의 방식
2) 사주가 형성하는 심리 구조
  - 작성 내용: 신강신약·십성 배치가 만드는 심리적 특성
3) 오행 균형 분석
  - 작성 내용: 강한 오행과 약한 오행이 성격에 미치는 구체적 영향 (원국 신살 포함)
4) 대인관계 패턴
  - 작성 내용: 이 사주 구조가 만들어내는 인간관계 특성
5) 핵심 강점과 성장 과제
  - 작성 내용: 타고난 재능과 자연스럽게 키워가면 좋은 영역
6) 삶의 철학적 테마
  - 작성 내용: 제시하는 근본적인 삶의 방향성

각 소챕터를 충분히 상세히 서술하세요.
"""


def build_prompt_wealth(saju_data: dict, db: dict) -> str:
    """섹션 2: 재물운 분석 (A4 2.5장 이상)"""
    full_name  = saju_data["기본정보"]["이름"]
    origin_ctx = build_origin_context(saju_data, current_year_from_saju(saju_data))
    sipsung_db = db.get("십성", {})
    jae_ref    = {"편재": sipsung_db.get("편재", {}), "정재": sipsung_db.get("정재", {})}

    return f"""
[사주 데이터]
이름: {full_name}

{origin_ctx}

[재물 십성 DB 참고]
{json.dumps(jae_ref, ensure_ascii=False)}

[작성 요청]
'재물운 상세 분석' 파트를 1,200자(A4 2.5장) 이상 2,000자 이내 작성하세요.
{_HEADING_RULES}
※ 의뢰인 호칭은 반드시 '{full_name} 님'으로만 표기할 것 (성 생략 금지)

{COMMON_RESTRICTIONS}
※ 대신: 이 사람이 실제로 돈을 어떻게 버는지·쓰는지를 먼저 구체적으로 쓰고,
         사주 근거는 뒤에서 짧게 한 번만 언급하거나 생략할 것

반드시 아래 각 항목을 ## 소제목으로 구성할 것:
- 재물 구조와 타고난 재복: 십성 배치(편재/정재)와 오행 구조로 본 재물 성향
- 재물 유형 분석: 노동소득 vs 자산소득 적합성, 수입 패턴
- 투자·소비 패턴과 주의사항: 이 사주에서 반복되는 금전 행동 패턴과 함정
- 대운별 재물 흐름: 현재 대운 및 향후 대운에서의 재물 변화 방향
- 재물 강화 전략: 이 사주에 맞는 실천 가능한 재물 증식 방법
"""


def build_prompt_career(saju_data: dict, db: dict) -> str:
    """섹션 3: 직업/직장운 분석 (A4 2.5장 이상)"""
    full_name  = saju_data["기본정보"]["이름"]
    origin_ctx = build_origin_context(saju_data, current_year_from_saju(saju_data))

    return f"""
[사주 데이터]
이름: {full_name}
성별: {saju_data['기본정보']['성별']}

{origin_ctx}

[작성 요청]
'직업 및 직장운 상세 분석' 파트를 1,200자(A4 2.5장) 이상 2,000자 이내 작성하세요.
{_HEADING_RULES}
※ 의뢰인 호칭은 반드시 '{full_name} 님'으로만 표기할 것 (성 생략 금지)

{COMMON_RESTRICTIONS}
※ 대신: 이 사람이 실제 일터에서 어떻게 움직이는지를 먼저 구체적으로 쓰고,
         사주 근거는 뒤에서 짧게 한 번만 언급하거나 생략할 것

반드시 아래 각 항목을 ## 소제목으로 구성할 것:
- 천직 직업군 도출: 사주 구조상 가장 빛을 발하는 직업군 최소 5개 (구체적으로)
- 직장 생활 패턴: 조직에서의 역할, 상하관계, 동료와의 관계 방식
- 사업 vs 직장: 이 사주가 독립 사업에 적합한지 직장 생활이 맞는지 근거와 함께
- 커리어 성장 전략: 성공을 앞당기는 구체적인 직업 전략 (원국 신살·대운 반영)
- 주의해야 할 직업적 함정: 피해야 할 상황과 환경
- 인생에서 가장 빛나는 직업적 시기: 대운 흐름 기준으로 언제 절정을 맞는지
"""


def build_prompt_love(saju_data: dict, db: dict) -> str:
    """섹션 4: 연애/결혼운 분석 (A4 2.5장 이상)"""
    full_name  = saju_data["기본정보"]["이름"]
    gender     = saju_data["기본정보"]["성별"]
    origin_ctx = build_origin_context(saju_data, current_year_from_saju(saju_data))

    return f"""
[사주 데이터]
이름: {full_name}
성별: {gender}

{origin_ctx}

[작성 요청]
'연애 및 결혼운 상세 분석' 파트를 1,200자(A4 2.5장) 이상 2,000자 이내 작성하세요.
{_HEADING_RULES}
※ 의뢰인 호칭은 반드시 '{full_name} 님'으로만 표기할 것 (성 생략 금지)

{COMMON_RESTRICTIONS}
※ 대신: 이 사람이 연애에서 실제로 어떤 패턴을 반복하는지를 먼저 구체적으로 쓰고,
         사주 근거는 뒤에서 짧게 한 번만 언급하거나 생략할 것

반드시 아래 각 항목을 ## 소제목으로 구성할 것:
- 연애 스타일: 이 사람이 연애에서 보여주는 고유한 패턴 (년살 등 신살 반영)
- 최고의 배우자나 연인: 사주 구조상 잘 맞는 이성의 유형
- 연애의 장점과 단점: 파트너에게 주는 것과 받아야 하는 것
- 결혼 시기와 인연: 결혼운이 강한 대운·세운 시기와 인연의 형태
- 부부 관계 패턴: 결혼 후 가정 내 역할과 관계 방식
- 사랑을 오래 유지하는 비결: 이 사주에 맞는 구체적인 관계 유지 전략
"""


def build_prompt_health(saju_data: dict, db: dict) -> str:
    """섹션 5: 건강운 분석 (A4 2장 이상)"""
    full_name  = saju_data["기본정보"]["이름"]
    origin_ctx = build_origin_context(saju_data, current_year_from_saju(saju_data))

    return f"""
[사주 데이터]
이름: {full_name}

{origin_ctx}

[작성 요청]
'건강운 상세 분석' 파트를 1,000자(A4 2장) 이상 2,000자 이내 작성하세요.
{_HEADING_RULES}
※ 의뢰인 호칭은 반드시 '{full_name} 님'으로만 표기할 것 (성 생략 금지)

{COMMON_RESTRICTIONS}
※ 금지 패턴 추가: "~조심해야 합니다"도 한 단락에 2번 이상 나오지 않도록 할 것
※ 대신: 이 사람의 몸이 실제로 어떤 상황에서 어떻게 반응하는지를 먼저 구체적으로 쓰고,
         사주 근거는 뒤에서 짧게 한 번만 언급하거나 생략할 것

반드시 아래 각 항목을 ## 소제목으로 구성할 것:
- 체질과 타고난 건강 구조: 오행 분포와 일간의 오행으로 본 체질적 특성
- 취약한 신체 부위와 질환: 오행 과부족·신살로 예측되는 취약 부위 (구체적 장기·계통 명시)
- 건강 유지 전략: 오행 균형을 맞추는 식습관·생활 습관·운동 조언
- 대운별 건강 흐름: 현재 및 향후 대운에서 특별히 주의할 건강 시기와 사항
"""


def build_prompt_lucky_charm(saju_data: dict, db: dict) -> str:
    """섹션 6: 맞춤형 개운 가이드 (A4 2.5장 이상)"""
    full_name  = saju_data["기본정보"]["이름"]
    origin_ctx = build_origin_context(saju_data, current_year_from_saju(saju_data))

    return f"""
[사주 데이터]
이름: {full_name}

{origin_ctx}

[작성 요청]
'맞춤형 개운 가이드' 파트를 1,200자(A4 2.5장) 이상 2,000자 이내 작성하세요.
{_HEADING_RULES}
※ 의뢰인 호칭은 반드시 '{full_name} 님'으로만 표기할 것 (성 생략 금지)

{COMMON_RESTRICTIONS}
※ 대신: 이 사람이 실생활에서 바로 써먹을 수 있는 구체적 조언을 먼저 쓰고,
         왜 그런지 이유는 뒤에서 짧게 한 번만 언급하거나 생략할 것

반드시 아래 각 항목을 ## 소제목으로 구성할 것:
- 오행 균형을 위한 개운 처방: 부족한 오행을 채우는 핵심 개운 방향
- 행운의 색상과 패션 전략: 강화해야 할 오행·신살 기준 색상과 착장 조언
- 개운 음식 처방: 오행별 음식 처방 및 피해야 할 식품
- 생활 공간 풍수 인테리어: 집·사무실 배치 및 인테리어 개운법
- 행운의 방향과 숫자: 의사결정 시 활용할 방향·숫자·날짜
- 정신적 개운법: 명상·기도·마인드셋 관련 조언
- 연간 개운 실천 스케줄: 월별로 실천할 수 있는 구체적 개운 행동 목록
"""


def build_prompt_relationships(saju_data: dict, db: dict) -> str:
    """섹션 7: 인간관계·가족운 상세 분석 (A4 2.5장 이상)"""
    full_name  = saju_data["기본정보"]["이름"]
    origin_ctx = build_origin_context(saju_data, current_year_from_saju(saju_data))

    return f"""
[사주 데이터]
이름: {full_name}
성별: {saju_data['기본정보']['성별']}

{origin_ctx}

[작성 요청]
'인간관계·가족운 상세 분석' 파트를 1,200자(A4 2.5장) 이상 2,000자 이내 작성하세요.
{_HEADING_RULES}
※ 의뢰인 호칭은 반드시 '{full_name} 님'으로만 표기할 것 (성 생략 금지)

{COMMON_RESTRICTIONS}
※ 금지 패턴 추가: "OO의 기운이 강해 ~에 유의해야 합니다" 구조로 쓰지 말 것
※ 대신: 이 사람이 관계에서 실제로 반복하는 패턴을 먼저 구체적으로 쓰고,
         사주 근거는 뒤에서 짧게 한 번만 언급하거나 생략할 것

반드시 아래 각 항목을 ## 소제목으로 구성할 것:
- 부모와의 인연과 정서적 영향: 사주 구조로 본 부모와의 관계 패턴 및 심리적 영향
- 형제자매·가족과의 거리감: 가족 관계에서 나타나는 친밀도와 거리감의 구조
- 가족으로 인해 짊어지기 쉬운 짐: 이 사주에서 반복되는 가족 관련 부담 패턴
- 인간관계에서 반복되는 갈등 구조: 대인관계에서 되풀이되는 갈등의 원인과 패턴
- 귀인운과 사람을 잘못 믿는 구조: 귀인 여부, 배신·손해를 부르는 관계 패턴 여부
- 평생 옆에 남는 사람의 유형: 장기적으로 인연이 이어지는 사람의 특성
- 외로움·고립·인정욕구의 작동 방식: 내면의 정서 패턴과 사회적 관계 욕구 구조
"""


def build_prompt_fortune_peaks(saju_data: dict, db: dict) -> str:
    """섹션 8: 인생의 상승기와 저운의 시기 (대운 기준, 1,400자 이내)"""
    full_name  = saju_data["기본정보"]["이름"]
    origin_ctx = build_origin_context(saju_data, current_year_from_saju(saju_data))

    daewun_list = saju_data.get("대운", [])
    daewun_lines = []
    for i, dw in enumerate(daewun_list):
        gan    = dw["간지"]["천간"]
        ji     = dw["간지"]["지지"]
        gan_ss = dw["천간"]["십성"]["값"]
        ji_ss  = dw["지지"]["십성"]["값"]
        ji_12  = dw["지지"]["12운성"]
        sal    = "/".join(dw["지지"]["신살"]) if dw["지지"]["신살"] else "없음"
        end_age = (
            daewun_list[i + 1]["시작나이"] - 1
            if i + 1 < len(daewun_list)
            else dw["시작나이"] + 9
        )
        daewun_lines.append(
            f"  {dw['시작나이']}세~{end_age}세 ({gan}{ji}): "
            f"천간십성={gan_ss} / 지지십성={ji_ss} / 12운성={ji_12} / 신살={sal}"
        )
    daewun_ctx = "\n".join(daewun_lines)

    return f"""
[사주 데이터]
이름: {full_name}

{origin_ctx}

[대운 목록]
{daewun_ctx}

[작성 요청]
위 대운 데이터를 분석하여 '{full_name} 님'의 '인생의 상승기와 저운의 시기'를 작성하세요.
※ 반드시 1,400자 이내로 작성할 것 (초과 엄금)
{_HEADING_RULES.replace('## 소제목으로 바로 시작할 것', '## 소제목으로 바로 시작할 것')}
※ 의뢰인 호칭은 반드시 '{full_name} 님'으로만 표기할 것 (성 생략 금지)

{COMMON_RESTRICTIONS}
※ 금지 패턴 추가: "OO 대운이므로 길한 시기입니다" 구조로 쓰지 말 것
※ 금지 패턴 추가: "OO(한자)이/가 활성화되어 ~가 따르는 시기입니다" 구조로 쓰지 말 것
※ 대신: 그 시기 이 사람의 삶이 실제로 어떻게 달라지는지를 먼저 구체적으로 쓰고,
         대운 이름은 뒤에서 짧게 한 번만 언급하거나 생략할 것

반드시 아래 ## 소제목 구조로 작성할 것:

## 인생 전체 흐름 한눈에 보기
- 대운 전체를 조망하여 이 사주가 전반적으로 어떤 인생 곡선을 그리는지 3~4줄로 서술

## 인생의 상승기
- 가장 강하게 운이 상승하는 대운 구간들을 구체적 나이와 간지를 명시하여 서술
- 각 상승기마다: 왜 좋은 운인지 (십성·12운성 근거), 어떤 분야가 잘 풀리는지, 어떻게 활용해야 하는지

## 저운의 시기
- 가장 조심해야 할 대운 구간들을 구체적 나이와 간지를 명시하여 서술
- 각 저운마다: 왜 힘든 운인지 (십성·12운성·신살 근거), 어떤 분야를 조심해야 하는지, 어떻게 대비해야 하는지

## 인생의 전환점
- 운의 흐름이 크게 바뀌는 대운 전환 시기를 명시하고, 그 시기에 특별히 중요한 결정이나 준비 사항 서술
"""


# ── 세운 / 월운 프롬프트 ──────────────────────────────────────────────────────

def build_prompt_yearly_fortune(saju_data: dict, seun: dict) -> str:
    """세운(年運) 분석 프롬프트."""
    import re as _re

    year     = seun["연도"]
    gan      = seun["간지"]["천간"]
    ji       = seun["간지"]["지지"]
    gan_elem = seun["천간"]["오행"]
    gan_ss   = seun["천간"]["십성"]["값"]
    ji_elem  = seun["지지"]["오행"]
    ji_ss    = seun["지지"]["십성"]["값"]
    ji_12    = seun["지지"]["12운성"]
    ji_sal   = "/".join(seun["지지"]["신살"]) if seun["지지"]["신살"] else "없음"

    full_name      = saju_data["기본정보"]["이름"]
    birth_date_str = saju_data["기본정보"]["생년월일"]
    origin_ctx     = build_origin_context(saju_data, year)

    try:
        nums        = _re.findall(r'\d+', birth_date_str)
        birth_year  = int(nums[0])
        current_age = year - birth_year
    except Exception:
        current_age = 0

    # 현재 대운 찾기
    current_daewun_str = ""
    daewun_list = saju_data.get("대운", [])
    for i, dw in enumerate(daewun_list):
        next_age = daewun_list[i + 1]["시작나이"] if i + 1 < len(daewun_list) else dw["시작나이"] + 10
        if dw["시작나이"] <= current_age < next_age:
            dw_gan = dw["간지"]["천간"]
            dw_ji  = dw["간지"]["지지"]
            current_daewun_str = (
                f"※ 현재 대운 ({current_age}세, {dw['시작나이']}세~{next_age - 1}세 구간): "
                f"{dw_gan}{dw_ji} 대운 "
                f"(천간십성:{dw['천간']['십성']['값']} / "
                f"지지십성:{dw['지지']['십성']['값']} / "
                f"12운성:{dw['지지']['12운성']} / "
                f"신살:{'/'.join(dw['지지']['신살']) if dw['지지']['신살'] else '없음'}) "
                f"← 반드시 이 대운을 기준으로 분석할 것"
            )
            break

    return f"""
[분석 대상]
이름: {full_name} ({current_age}세, {year}년)

{origin_ctx}
{current_daewun_str}

[{year}년 세운 데이터]
세운 간지: {gan}{ji}년
천간 {gan}: 오행={gan_elem}, 일간과의 십성={gan_ss}
지지 {ji}: 오행={ji_elem}, 십성={ji_ss}, 12운성={ji_12}, 신살={ji_sal}

[작성 요청]
{year}년({gan}{ji}년) 연간 운세를 800자 이상 1,100자 이내로 분석하세요.
※ 분량 엄수: 1,100자를 초과하지 말 것
※ 인사말·본인 소개·제목 없이 바로 시작할 것
※ 의뢰인 호칭은 반드시 '{full_name} 님'으로만 표기할 것 (성 생략 금지)
※ 소제목(###) 없이 파트 구분 없이 흐르는 글 형식으로 작성할 것
※ 현재 대운은 위에 명시된 대운({current_age}세 구간)이며, 대운 흐름 목록의 다른 나이 대운을 현재 대운으로 혼동하지 말 것

{COMMON_RESTRICTIONS}
※ 금지 패턴 추가: "금년 세운에서 OO이 투출하여 ~하는 구조입니다" 구조로 쓰지 말 것
※ 금지 패턴 추가: "OO(한자)의 기운이 강해 ~에 유의해야 합니다" 구조로 쓰지 말 것
※ 대신: 올해 이 사람의 실생활에서 어떤 변화가 오는지를 먼저 구체적으로 쓰고,
         이유는 뒤에서 짧게 한 번만 언급하거나 생략할 것

※ 단락을 자연스럽게 이어가며 아래 내용을 모두 녹여낼 것:
  - {year}년 전체 기운: 세운과 원국·대운의 상호작용 (신살 {ji_sal} 영향 포함)
  - 재물의 흐름과 금전 조언
  - 직업·직장·사업의 변화 방향
  - 인간관계와 연애의 흐름
  - 건강 주의 사항
"""


def build_prompt_monthly_fortune(saju_data: dict, wolun: dict) -> str:
    """월운(月運) 분석 프롬프트."""
    year     = wolun["연도"]
    month    = wolun["월"]
    gan      = wolun["간지"]["천간"]
    ji       = wolun["간지"]["지지"]
    gan_elem = wolun["천간"]["오행"]
    gan_ss   = wolun["천간"]["십성"]["값"]
    ji_elem  = wolun["지지"]["오행"]
    ji_ss    = wolun["지지"]["십성"]["값"]
    ji_12    = wolun["지지"]["12운성"]
    ji_sal   = "/".join(wolun["지지"]["신살"]) if wolun["지지"]["신살"] else "없음"

    month_names = ["1월","2월","3월","4월","5월","6월",
                   "7월","8월","9월","10월","11월","12월"]
    full_name  = saju_data["기본정보"]["이름"]
    origin_ctx = build_origin_context(saju_data, year)

    seun_for_year = next(
        (s for s in saju_data.get("세운", []) if s["연도"] == year), None
    )
    seun_ctx = ""
    if seun_for_year:
        s_gan = seun_for_year["간지"]["천간"]
        s_ji  = seun_for_year["간지"]["지지"]
        s_sal = "/".join(seun_for_year["지지"]["신살"]) if seun_for_year["지지"]["신살"] else "없음"
        seun_ctx = (
            f"{year}년 세운: {s_gan}{s_ji} "
            f"(천간십성:{seun_for_year['천간']['십성']['값']} / "
            f"지지십성:{seun_for_year['지지']['십성']['값']} / 신살:{s_sal})"
        )

    return f"""
[사주 데이터]
이름: {full_name}

{origin_ctx}
{seun_ctx}

[{year}년 {month_names[month - 1]} 월운 데이터]
월운 간지: {gan}{ji}월
천간 {gan}: 오행={gan_elem}, 십성={gan_ss}
지지 {ji}: 오행={ji_elem}, 십성={ji_ss}, 12운성={ji_12}, 신살={ji_sal}

[작성 요청]
{year}년 {month_names[month - 1]}의 월별 운세를 700자 이상 1,000자 이내로 작성하세요.
※ 분량 엄수: 1,000자를 초과하지 말 것
※ 인사말·본인 소개·제목 없이 바로 시작할 것
※ 의뢰인 호칭은 반드시 '{full_name} 님'으로만 표기할 것 (성 생략 금지)
※ 소제목(###) 없이 파트 구분 없이 흐르는 글 형식으로 작성할 것

{COMMON_RESTRICTIONS}
※ 금지 패턴 추가: "이달 월간 십성이 OO으로 ~한 달입니다" 구조로 쓰지 말 것
※ 금지 패턴 추가: "OO(한자)의 기운이 강해 ~에 유의해야 합니다" 구조로 쓰지 말 것
※ 대신: 이달 이 사람의 일상에서 실제로 어떤 일이 벌어지는지를 먼저 구체적으로 쓰고,
         이유는 뒤에서 짧게 한 번만 언급하거나 생략할 것

※ 단락을 자연스럽게 이어가며 아래 내용을 모두 녹여낼 것:
  - 이달의 전체 기운: 월운·세운·원국 삼중 작용 요약 (신살 {ji_sal} 반영)
  - 재물: 이달 금전 흐름과 구체적 조언
  - 직장·사업: 이달 업무와 커리어 포인트
  - 인간관계·연애: 이달 중요한 만남 및 관계와 연애 흐름 및 감정 포인트
  - 건강: 이달 특별 주의 사항
"""


# ── 기본 리포트 전용 프롬프트 ─────────────────────────────────────────────────

def build_prompt_personality_basic(saju_data: dict, db: dict) -> str:
    """기본 리포트용 성격 분석 (A4 1.5장)"""
    day_stem   = saju_data["일간정보"]["일간"]
    day_branch = saju_data["사주원국"]["일주"]["지지"]
    ilju       = saju_data["사주원국"]["일주"]["간지"]
    full_name  = saju_data["기본정보"]["이름"]

    stem_info   = db.get("천간", {}).get(day_stem, {})
    branch_info = db.get("지지", {}).get(day_branch, {})
    origin_ctx  = build_origin_context(saju_data, current_year_from_saju(saju_data))

    return f"""
[분석 대상 사주 데이터]
이름: {full_name}
생년월일: {saju_data['기본정보']['생년월일']}
성별: {saju_data['기본정보']['성별']}

{origin_ctx}

[일간 참고 데이터]
{day_stem}일간 특성: {json.dumps(stem_info, ensure_ascii=False)}
일지 {day_branch} 특성: {json.dumps(branch_info, ensure_ascii=False)}

[작성 요청]
위 사주 데이터를 바탕으로 '타고난 성격과 기질' 파트를 A4 1.5장(700자 이상) 분량으로 작성해주세요.
파트 구분 없이 흐르는 글 형식으로 작성하세요.
※ 인사말·본인 소개 없이 마크다운 제목(## {ilju}일주 타고난 성격과 기질)으로 바로 시작할 것
※ 의뢰인 호칭은 반드시 '{full_name} 님'으로만 표기할 것 (성 생략 금지)

{COMMON_RESTRICTIONS}
※ 대신: 이 사람이 실제로 어떤 상황에서 어떻게 행동하는지를 먼저 구체적으로 쓰고,
         사주 근거는 뒤에서 짧게 한 번만 언급하거나 생략할 것

포함 내용:
- {ilju}일주의 핵심 기질과 삶의 방식 (1~2 단락)
- 타고난 강점 3가지 (간단히)
- 보완이 필요한 약점 3가지 (간단히)
- 소제목은 ## 하나만 사용, 그 외 소제목(###) 없이 단락으로 서술
"""


def build_prompt_basic_overview(saju_data: dict, target_year: int) -> str:
    """기본 리포트용 전반 운세 요약"""
    full_name  = saju_data["기본정보"]["이름"]
    origin_ctx = build_origin_context(saju_data, target_year)

    return f"""
[사주 데이터]
이름: {full_name}

{origin_ctx}

[작성 요청]
위 사주를 바탕으로 전반적인 운세를 단락 형식으로 작성하세요.
파트 구분 없이 흐르는 글 형식이어야 합니다.
※ 인사말·본인 소개 없이 ## 제목으로 바로 시작할 것
※ 의뢰인 호칭은 반드시 '{full_name} 님'으로만 표기할 것 (성 생략 금지)
※ 각 분야를 세세하게 분석하지 말고 방향성 위주로 간결하게 서술하세요

{COMMON_RESTRICTIONS}
※ 대신: 이 사람의 실제 삶에서 어떻게 나타나는지를 먼저 쓰고, 사주 근거는 뒤에서 짧게 언급하거나 생략

형식:
## 전반 운세

재물운
(2~4줄, 재물 흐름의 방향성만)

직업운
(2~4줄, 직업·커리어 방향성만)

연애운
(2~4줄, 연애·관계 방향성만)

건강운
(2~4줄, 건강 관리 핵심 포인트만)
"""


def build_prompt_basic_thisyear(saju_data: dict, seun: dict) -> str:
    """기본 리포트용 신년 총평"""
    year      = seun["연도"]
    gan       = seun["간지"]["천간"]
    ji        = seun["간지"]["지지"]
    gan_ss    = seun["천간"]["십성"]["값"]
    ji_ss     = seun["지지"]["십성"]["값"]
    ji_sal    = "/".join(seun["지지"]["신살"]) if seun["지지"]["신살"] else "없음"
    full_name = saju_data["기본정보"]["이름"]
    origin_ctx = build_origin_context(saju_data, year)

    return f"""
[사주 데이터]
이름: {full_name}

{origin_ctx}

[{year}년 세운]
세운: {gan}{ji}년 (천간십성={gan_ss} / 지지십성={ji_ss} / 신살={ji_sal})

[작성 요청]
"{year}년은 ○○의 해입니다" 수준의 한 줄 총평을 포함해, {year}년 전체 기운을 3~5줄로 간결하게 서술하세요.
월운·10년 대운 등 세세한 내용은 절대 포함하지 마세요.
※ 인사말·본인 소개 없이 ## 제목으로 바로 시작할 것
※ 의뢰인 호칭은 반드시 '{full_name} 님'으로만 표기할 것 (성 생략 금지)

{COMMON_RESTRICTIONS}
※ 금지 패턴 추가: "금년 세운에서 OO이 ~하는 구조입니다" 구조로 쓰지 말 것
※ 대신: 올해 이 사람의 실생활에서 어떤 느낌이 오는지를 먼저 쓰고, 이유는 짧게 뒤에

형식:
## {year}년 간략 총평

(3~5줄 간결한 서술)
"""
