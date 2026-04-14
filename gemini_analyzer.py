"""
Gemini API 기반 사주 분석 모듈
- 30년 경력 역술가 페르소나 시스템 프롬프트 고정
- 섹션별 분산 호출로 100페이지 분량 생성
- 연도별 세운 루프, 월별 월운 루프 포함

[saju_data 구조 기준]
사주원국 각 주(柱):
  {"천간": "乙", "지지": "亥", "간지": "乙亥"}  ← 단순 평면 구조

대운/세운/월운 각 항목 (_build_pillar_block 구조):
  {
    "간지": {"천간": "丙", "지지": "午"},
    "천간": {"문자": "丙", "오행": "화", "십성": {"값": "...", "기준": "일간"}},
    "지지": {"문자": "午", "오행": "화", "십성": {"값": "...", "기준": "일간"},
             "12운성": "...", "신살": [...]}
  }

최상위 키:
  기본정보 / 사주원국 / 일간정보(일간·오행·음양·신강신약) /
  십성 / 오행분포 / 십이운성 / 신살(리스트) / 대운수 / 대운 / 세운 / 월운
"""

import google.generativeai as genai
import json
import time
import os
from datetime import datetime

# ── 30년 경력 역술가 시스템 프롬프트 ──────────────────────────────────

EXPERT_SYSTEM_PROMPT = """당신은 30년 경력의 대한민국 최고 역술가입니다.

[정체성]
- 사주명리학, 자미두수, 기문둔갑에 정통한 동양철학 박사
- 3대째 내려오는 전통 역술 가문 출신
- 수만 명의 사주를 직접 분석한 실전 경험 보유
- 현대 심리학과 코칭 기법을 접목한 현대적 역술 선도

[분석 원칙]
1. 단순한 길흉 판단이 아닌 '왜 그런가'를 심층 설명한다
2. 부정적 운도 긍정적 방향으로 전환하는 조언을 제공한다
3. 구체적이고 실천 가능한 개운법을 반드시 포함한다
4. 현대인의 삶에 적용 가능한 현실적 조언을 한다
5. 학문적 근거(사주 원리)를 들어 신뢰감을 준다

[문체]
- 따뜻하고 진지하며 전문적인 어조 유지
- 어려운 한자 용어는 반드시 한글로 풀어서 설명
- A4 기준 분량을 충실히 채우는 상세한 서술
- 독자가 자신의 이야기를 읽는 것처럼 개인화된 표현 사용

[호칭 규칙 - 반드시 준수]
- 의뢰인을 호칭할 때는 반드시 성(姓)을 포함한 전체 이름에 '님'을 붙인다
  예) 이름이 '이혜수'이면 → '이혜수 님' (O) / '혜수 님' (X)
- 이름이 두 글자(성+이름 1자)인 경우도 동일하게 전체 이름 사용
- 본문 중간에 이름을 줄여 부르는 것을 절대 금지한다

[시작 형식 - 반드시 준수]
- 각 섹션은 반드시 분석 본문으로 바로 시작한다
- "반갑습니다", "안녕하세요" 등의 인사말로 시작하는 것을 절대 금지한다
- "저는 30년 경력의~", "역술가입니다" 등 본인 소개 문장을 절대 금지한다
- 마크다운 제목(##) 또는 분석 내용으로 즉시 시작할 것

[중요 지침]
- 운명론적 결정론을 피하고 '경향성'으로 표현한다
- "반드시 ~한다"보다 "~하는 경향이 강하다"고 표현한다
- 어떤 운세든 노력과 의지로 극복/증폭 가능함을 강조한다"""


def init_gemini(api_key: str):
    genai.configure(api_key=api_key)
    return genai.GenerativeModel(
        model_name="models/gemini-3-flash-preview",
        system_instruction=EXPERT_SYSTEM_PROMPT
    )


def _clean_markdown(text: str) -> str:
    """AI 응답에서 마크다운 강조 기호(**) 제거"""
    import re
    # 텍스트 → 텍스트
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
    # 혹시 남은 단독 * 도 제거
    text = re.sub(r'\*(.+?)\*', r'\1', text)
    return text


def call_gemini(model, prompt: str, retry: int = 3) -> str:
    for attempt in range(retry):
        try:
            response = model.generate_content(
                prompt,
                generation_config={
                    "temperature": 0.8,
                    "max_output_tokens": 4096,
                },
            )
            return _clean_markdown(response.text)
        except Exception as e:
            print(f"  ⚠️  API 오류 (시도 {attempt+1}/{retry}): {e}")
            if attempt < retry - 1:
                time.sleep(3)
    return "분석 생성 중 오류가 발생했습니다."


def load_db() -> dict:
    """지식 DB 로드"""
    db_path = os.path.join(os.path.dirname(__file__), "db_knowledge.json")
    with open(db_path, "r", encoding="utf-8") as f:
        return json.load(f)


# ── 사주원국 주(柱) 헬퍼 ─────────────────────────────────────────────────────
# 사주원국은 {"천간":"乙","지지":"亥","간지":"乙亥"} 단순 구조

def _origin_pillar_str(pillar: dict) -> str:
    """사주원국 주 → 'XX (천간오행)' 형태 요약"""
    gan    = pillar["천간"]
    ji     = pillar["지지"]
    ganji  = pillar["간지"]
    return f"{ganji} (천간:{gan} / 지지:{ji})"


# ── 대운/세운/월운 주(柱) 헬퍼 ───────────────────────────────────────────────
# _build_pillar_block 구조: 간지.천간/지지, 천간.문자/오행/십성, 지지.문자/오행/십성/12운성/신살

def _pillar_str(pillar: dict) -> str:
    """
    _build_pillar_block 구조에서 요약 문자열 반환.
    예) "丙午 (지지오행:화 / 십성:정인 / 12운성:제왕 / 신살:육해살/장성살)"
    """
    gan  = pillar["간지"]["천간"]
    ji   = pillar["간지"]["지지"]
    gan_elem = pillar["천간"]["오행"]
    gan_ss   = pillar["천간"]["십성"]["값"]
    ji_elem  = pillar["지지"]["오행"]
    ji_ss    = pillar["지지"]["십성"]["값"]
    un       = pillar["지지"]["12운성"]
    sal      = "/".join(pillar["지지"]["신살"]) if pillar["지지"]["신살"] else "없음"
    return (f"{gan}{ji} "
            f"(천간:{gan}·{gan_elem}·{gan_ss} / "
            f"지지:{ji}·{ji_elem}·{ji_ss} / "
            f"12운성:{un} / 신살:{sal})")


def _build_origin_context(saju_data: dict) -> str:
    """사주원국 전체 컨텍스트 문자열 (프롬프트 공통 삽입용)"""
    ori = saju_data["사주원국"]
    twelve = saju_data.get("십이운성", {})
    sipsung = saju_data.get("십성", {})
    shinsal_list = saju_data.get("신살", [])

    lines = [
        f"사주원국: 연주 {ori['연주']['간지']}  월주 {ori['월주']['간지']}  일주 {ori['일주']['간지']}  시주 {ori['시주']['간지']}",
        f"일간: {saju_data['일간정보']['일간']} ({saju_data['일간정보']['오행']} · {saju_data['일간정보']['음양']})",
        f"신강신약: {saju_data['일간정보']['신강신약']}",
        f"오행분포: 목{saju_data['오행분포']['목']} 화{saju_data['오행분포']['화']} 토{saju_data['오행분포']['토']} 금{saju_data['오행분포']['금']} 수{saju_data['오행분포']['수']}",
        f"십성: 연간={sipsung.get('연간','-')} 연지={sipsung.get('연지','-')} 월간={sipsung.get('월간','-')} 월지={sipsung.get('월지','-')} 일지={sipsung.get('일지','-')} 시간={sipsung.get('시간','-')} 시지={sipsung.get('시지','-')}",
        f"십이운성: 연지={twelve.get('연지','-')} 월지={twelve.get('월지','-')} 일지={twelve.get('일지','-')} 시지={twelve.get('시지','-')}",
        f"원국 신살: {', '.join(shinsal_list) if shinsal_list else '없음'}",
        f"대운수: {saju_data.get('대운수', '-')}세 시작",
    ]

    # 대운 흐름 요약
    daewun = saju_data.get("대운", [])
    if daewun:
        dw_lines = []
        for d in daewun:
            gan = d["간지"]["천간"]
            ji  = d["간지"]["지지"]
            sal = "/".join(d["지지"]["신살"]) if d["지지"]["신살"] else "-"
            dw_lines.append(
                f"  {d['시작나이']}세~: {gan}{ji} "
                f"(천간십성:{d['천간']['십성']['값']} / "
                f"지지십성:{d['지지']['십성']['값']} / "
                f"12운성:{d['지지']['12운성']} / 신살:{sal})"
            )
        lines.append("대운 흐름:\n" + "\n".join(dw_lines))

    return "\n".join(lines)


# ── 섹션별 분석 함수 (프리미엄) ───────────────────────────────────────────────

def analyze_personality(model, saju_data: dict, db: dict) -> str:
    """섹션 1: 타고난 본질 및 성격 분석 (A4 3장 이상)"""
    day_stem   = saju_data["일간정보"]["일간"]
    day_branch = saju_data["사주원국"]["일주"]["지지"]
    ilju       = saju_data["사주원국"]["일주"]["간지"]
    full_name  = saju_data['기본정보']['이름']

    stem_info   = db.get("천간", {}).get(day_stem, {})
    branch_info = db.get("지지", {}).get(day_branch, {})

    origin_ctx = _build_origin_context(saju_data)

    prompt = f"""
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
위 사주 데이터를 바탕으로 '타고난 본질과 성격 분석' 파트를 A4 3장 이상(1,500자 이상) 분량으로 작성해주세요.
※ 인사말·본인 소개 없이 ## 소제목으로 바로 시작할 것
※ 소제목은 반드시 ## 형식만 사용하고, 소제목에 번호(1. 2. 3. 등)를 절대 붙이지 말 것
※ 의뢰인 호칭은 반드시 '{full_name} 님'으로만 표기할 것 (성 생략 금지)

반드시 아래 각 항목을 ## 소제목으로 구성할 것:
- 일주(일간+일지)의 핵심 기질: {ilju}일주가 가진 근본적 에너지와 삶의 방식
- 사주가 형성하는 심리 구조: 신강신약·십성 배치가 만드는 심리적 특성
- 오행 균형 분석: 강한 오행과 약한 오행이 성격에 미치는 구체적 영향 (원국 신살 포함)
- 대인관계 패턴: 이 사주 구조가 만들어내는 인간관계 특성
- 핵심 강점과 성장 과제: 타고난 재능과 반드시 개발해야 할 영역
- 삶의 철학적 테마: 제시하는 근본적인 삶의 방향성

각 소챕터를 충분히 상세히 서술하세요.
"""
    return call_gemini(model, prompt)


def analyze_wealth(model, saju_data: dict, db: dict) -> str:
    """섹션 2: 재물운 분석 (A4 2.5장 이상)"""
    full_name  = saju_data['기본정보']['이름']
    origin_ctx = _build_origin_context(saju_data)

    sipsung_db_jae = db.get("십성", {})
    jae_ref = {
        "편재": sipsung_db_jae.get("편재", {}),
        "정재": sipsung_db_jae.get("정재", {}),
    }

    prompt = f"""
[사주 데이터]
이름: {full_name}

{origin_ctx}

[재물 십성 DB 참고]
{json.dumps(jae_ref, ensure_ascii=False)}

[작성 요청]
위 데이터를 바탕으로 '재물운 상세 분석' 파트를 A4 2.5장(1,200자) 이상 작성하세요.
※ 인사말·본인 소개 없이 ## 소제목으로 바로 시작할 것
※ 소제목은 반드시 ## 형식만 사용하고, 소제목에 번호(1. 2. 3. 등)를 절대 붙이지 말 것
※ 의뢰인 호칭은 반드시 '{full_name} 님'으로만 표기할 것 (성 생략 금지)

반드시 아래 각 항목을 ## 소제목으로 구성할 것:
- 재물 구조와 타고난 재복: 십성 배치(편재/정재)와 오행 구조로 본 재물 성향
- 재물 유형 분석: 노동소득 vs 자산소득 적합성, 수입 패턴
- 투자·소비 패턴과 주의사항: 이 사주에서 반복되는 금전 행동 패턴과 함정
- 대운별 재물 흐름: 현재 대운 및 향후 대운에서의 재물 변화 방향
- 재물 강화 전략: 이 사주에 맞는 실천 가능한 재물 증식 방법
"""
    return call_gemini(model, prompt)


def analyze_career(model, saju_data: dict, db: dict) -> str:
    """섹션 3: 직업/직장운 분석 (A4 2.5장 이상)"""
    full_name  = saju_data['기본정보']['이름']
    origin_ctx = _build_origin_context(saju_data)

    prompt = f"""
[사주 데이터]
이름: {full_name}
성별: {saju_data['기본정보']['성별']}

{origin_ctx}

[작성 요청]
'직업 및 직장운 상세 분석' 파트를 A4 2.5장(1,200자) 이상 작성하세요.
※ 인사말·본인 소개 없이 ## 소제목으로 바로 시작할 것
※ 소제목은 반드시 ## 형식만 사용하고, 소제목에 번호(1. 2. 3. 등)를 절대 붙이지 말 것
※ 의뢰인 호칭은 반드시 '{full_name} 님'으로만 표기할 것 (성 생략 금지)

반드시 아래 각 항목을 ## 소제목으로 구성할 것:
- 천직 직업군 도출: 사주 구조상 가장 빛을 발하는 직업군 최소 5개 (구체적으로)
- 직장 생활 패턴: 조직에서의 역할, 상하관계, 동료와의 관계 방식
- 사업 vs 직장: 이 사주가 독립 사업에 적합한지 직장 생활이 맞는지 근거와 함께
- 커리어 성장 전략: 성공을 앞당기는 구체적인 직업 전략 (원국 신살·대운 반영)
- 주의해야 할 직업적 함정: 피해야 할 상황과 환경
- 인생에서 가장 빛나는 직업적 시기: 대운 흐름 기준으로 언제 절정을 맞는지
"""
    return call_gemini(model, prompt)


def analyze_love(model, saju_data: dict, db: dict) -> str:
    """섹션 4: 연애/결혼운 분석 (A4 2.5장 이상)"""
    full_name  = saju_data['기본정보']['이름']
    gender     = saju_data['기본정보']['성별']
    origin_ctx = _build_origin_context(saju_data)

    prompt = f"""
[사주 데이터]
이름: {full_name}
성별: {gender}

{origin_ctx}

[작성 요청]
'연애 및 결혼운 상세 분석' 파트를 A4 2.5장(1,200자) 이상 작성하세요.
※ 인사말·본인 소개 없이 ## 소제목으로 바로 시작할 것
※ 소제목은 반드시 ## 형식만 사용하고, 소제목에 번호(1. 2. 3. 등)를 절대 붙이지 말 것
※ 의뢰인 호칭은 반드시 '{full_name} 님'으로만 표기할 것 (성 생략 금지)

반드시 아래 각 항목을 ## 소제목으로 구성할 것:
- 연애 스타일: 이 사람이 연애에서 보여주는 고유한 패턴 (도화살 등 신살 반영)
- 최고의 배우자나 연인: 사주 구조상 잘 맞는 이성의 유형
- 연애의 장점과 단점: 파트너에게 주는 것과 받아야 하는 것
- 결혼 시기와 인연: 결혼운이 강한 대운·세운 시기와 인연의 형태
- 부부 관계 패턴: 결혼 후 가정 내 역할과 관계 방식
- 사랑을 오래 유지하는 비결: 이 사주에 맞는 구체적인 관계 유지 전략
"""
    return call_gemini(model, prompt)


def analyze_health(model, saju_data: dict, db: dict) -> str:
    """섹션 5: 건강운 분석 (A4 2장 이상)"""
    full_name  = saju_data['기본정보']['이름']
    origin_ctx = _build_origin_context(saju_data)

    prompt = f"""
[사주 데이터]
이름: {full_name}

{origin_ctx}

[작성 요청]
'건강운 상세 분석' 파트를 A4 2장(1,000자) 이상 작성하세요.
※ 인사말·본인 소개 없이 ## 소제목으로 바로 시작할 것
※ 소제목은 반드시 ## 형식만 사용하고, 소제목에 번호(1. 2. 3. 등)를 절대 붙이지 말 것
※ 의뢰인 호칭은 반드시 '{full_name} 님'으로만 표기할 것 (성 생략 금지)

반드시 아래 각 항목을 ## 소제목으로 구성할 것:
- 체질과 타고난 건강 구조: 오행 분포와 일간의 오행으로 본 체질적 특성
- 취약한 신체 부위와 질환: 오행 과부족·신살로 예측되는 취약 부위 (구체적 장기·계통 명시)
- 건강 유지 전략: 오행 균형을 맞추는 식습관·생활 습관·운동 조언
- 대운별 건강 흐름: 현재 및 향후 대운에서 특별히 주의할 건강 시기와 사항
"""
    return call_gemini(model, prompt)


def analyze_lucky_charm(model, saju_data: dict, db: dict) -> str:
    """섹션 6: 맞춤형 개운 가이드 (A4 2.5장 이상)"""
    full_name  = saju_data['기본정보']['이름']
    origin_ctx = _build_origin_context(saju_data)

    prompt = f"""
[사주 데이터]
이름: {full_name}

{origin_ctx}

[작성 요청]
'맞춤형 개운 가이드' 파트를 A4 2.5장(1,200자) 이상 작성하세요.
※ 인사말·본인 소개 없이 ## 소제목으로 바로 시작할 것
※ 소제목은 반드시 ## 형식만 사용하고, 소제목에 번호(1. 2. 3. 등)를 절대 붙이지 말 것
※ 의뢰인 호칭은 반드시 '{full_name} 님'으로만 표기할 것 (성 생략 금지)

반드시 아래 각 항목을 ## 소제목으로 구성할 것:
- 오행 균형을 위한 개운 처방: 부족한 오행을 채우는 핵심 개운 방향
- 행운의 색상과 패션 전략: 강화해야 할 오행·신살 기준 색상과 착장 조언
- 개운 음식 처방: 오행별 음식 처방 및 피해야 할 식품
- 생활 공간 풍수 인테리어: 집·사무실 배치 및 인테리어 개운법
- 행운의 방향과 숫자: 의사결정 시 활용할 방향·숫자·날짜
- 정신적 개운법: 명상·기도·마인드셋 관련 조언
- 연간 개운 실천 스케줄: 월별로 실천할 수 있는 구체적 개운 행동 목록
"""
    return call_gemini(model, prompt)


def analyze_monthly_fortune(model, saju_data: dict, wolun: dict) -> str:
    """
    월운(月運) 분석
    wolun: get_wolun() 반환값 (_build_pillar_block 구조 + "연도", "월")
    항목 5개만: 전체기운·재물·직장·인간관계·건강 (행운의 날짜·핵심 메시지 제거)
    """
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

    full_name  = saju_data['기본정보']['이름']
    origin_ctx = _build_origin_context(saju_data)

    # 해당 연도의 세운 데이터 찾기
    seun_for_year = next(
        (s for s in saju_data.get("세운", []) if s["연도"] == year),
        None
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

    prompt = f"""
[사주 데이터]
이름: {full_name}

{origin_ctx}
{seun_ctx}

[{year}년 {month_names[month-1]} 월운 데이터]
월운 간지: {gan}{ji}월
천간 {gan}: 오행={gan_elem}, 십성={gan_ss}
지지 {ji}: 오행={ji_elem}, 십성={ji_ss}, 12운성={ji_12}, 신살={ji_sal}

[작성 요청]
{year}년 {month_names[month-1]}의 월별 운세를 700자 이상 1,000자 이내로 작성하세요.
※ 분량 엄수: 1,000자를 초과하지 말 것
※ 인사말·본인 소개·제목 없이 바로 시작할 것
※ 의뢰인 호칭은 반드시 '{full_name} 님'으로만 표기할 것 (성 생략 금지)
※ 소제목(###) 없이 파트 구분 없이 흐르는 글 형식으로 작성할 것
※ 단락을 자연스럽게 이어가며 아래 내용을 모두 녹여낼 것:
  - 이달의 전체 기운: 월운·세운·원국 삼중 작용 요약 (신살 {ji_sal} 반영)
  - 재물: 이달 금전 흐름과 구체적 조언
  - 직장·사업: 이달 업무와 커리어 포인트
  - 인간관계·연애: 이달 중요한 만남 및 관계와 연애 흐름 및 감정 포인트
  - 건강: 이달 특별 주의 사항
"""
    return call_gemini(model, prompt)


def analyze_yearly_fortune(model, saju_data: dict, seun: dict) -> str:
    """
    세운(年運) 분석
    seun: get_seun() 반환값 (_build_pillar_block 구조 + "연도")
    """
    year      = seun["연도"]
    gan       = seun["간지"]["천간"]
    ji        = seun["간지"]["지지"]
    gan_elem  = seun["천간"]["오행"]
    gan_ss    = seun["천간"]["십성"]["값"]
    ji_elem   = seun["지지"]["오행"]
    ji_ss     = seun["지지"]["십성"]["값"]
    ji_12     = seun["지지"]["12운성"]
    ji_sal    = "/".join(seun["지지"]["신살"]) if seun["지지"]["신살"] else "없음"

    birth_year_str = saju_data['기본정보']['생년월일'][:4]
    try:
        current_age = year - int(birth_year_str) + 1
    except Exception:
        current_age = "??"

    full_name  = saju_data['기본정보']['이름']
    origin_ctx = _build_origin_context(saju_data)

    # 해당 연도의 현재 대운 찾기
    current_daewun_str = ""
    daewun_list = saju_data.get("대운", [])
    for i, dw in enumerate(daewun_list):
        next_age = daewun_list[i+1]["시작나이"] if i+1 < len(daewun_list) else dw["시작나이"] + 10
        if dw["시작나이"] <= current_age < next_age:
            dw_gan = dw["간지"]["천간"]
            dw_ji  = dw["간지"]["지지"]
            current_daewun_str = (
                f"현재 대운: {dw_gan}{dw_ji} "
                f"(천간십성:{dw['천간']['십성']['값']} / "
                f"지지십성:{dw['지지']['십성']['값']} / "
                f"12운성:{dw['지지']['12운성']} / "
                f"신살:{'/'.join(dw['지지']['신살']) if dw['지지']['신살'] else '없음'})"
            )
            break

    prompt = f"""
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
※ 단락을 자연스럽게 이어가며 아래 내용을 모두 녹여낼 것:
  - {year}년 전체 기운: 세운과 원국·대운의 상호작용 (신살 {ji_sal} 영향 포함)
  - 재물의 흐름과 금전 조언
  - 직업·직장·사업의 변화 방향
  - 인간관계와 연애의 흐름
  - 건강 주의 사항
"""
    return call_gemini(model, prompt)


# ── 기본 리포트 전용 분석 함수 ────────────────────────────────────────────────

def analyze_personality_basic(model, saju_data: dict, db: dict) -> str:
    """기본 리포트용 성격 분석 (A4 1.5장, 핵심 기질 + 강점/약점)"""
    day_stem   = saju_data["일간정보"]["일간"]
    day_branch = saju_data["사주원국"]["일주"]["지지"]
    ilju       = saju_data["사주원국"]["일주"]["간지"]
    full_name  = saju_data['기본정보']['이름']

    stem_info   = db.get("천간", {}).get(day_stem, {})
    branch_info = db.get("지지", {}).get(day_branch, {})
    origin_ctx  = _build_origin_context(saju_data)

    prompt = f"""
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

포함 내용:
- {ilju}일주의 핵심 기질과 삶의 방식 (1~2 단락)
- 타고난 강점 3가지 (간단히)
- 보완이 필요한 약점 3가지 (간단히)
- 소제목은 ## 하나만 사용, 그 외 소제목(###) 없이 단락으로 서술
"""
    return call_gemini(model, prompt)


def analyze_basic_overview(model, saju_data: dict, target_year: int, db: dict) -> str:
    """기본 리포트용 전반 운세 요약 (재물·직업·연애·건강 각 2~4줄)"""
    full_name  = saju_data['기본정보']['이름']
    origin_ctx = _build_origin_context(saju_data)

    prompt = f"""
[사주 데이터]
이름: {full_name}

{origin_ctx}

[작성 요청]
위 사주를 바탕으로 전반적인 운세를 단락 형식으로 작성하세요.
파트 구분 없이 흐르는 글 형식이어야 합니다.
※ 인사말·본인 소개 없이 ## 제목으로 바로 시작할 것
※ 의뢰인 호칭은 반드시 '{full_name} 님'으로만 표기할 것 (성 생략 금지)
※ 각 분야를 세세하게 분석하지 말고 방향성 위주로 간결하게 서술하세요

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
    return call_gemini(model, prompt)


def analyze_basic_thisyear(model, saju_data: dict, seun: dict) -> str:
    """기본 리포트용 신년 총평 간략 수준"""
    year      = seun["연도"]
    gan       = seun["간지"]["천간"]
    ji        = seun["간지"]["지지"]
    gan_ss    = seun["천간"]["십성"]["값"]
    ji_ss     = seun["지지"]["십성"]["값"]
    ji_sal    = "/".join(seun["지지"]["신살"]) if seun["지지"]["신살"] else "없음"

    full_name  = saju_data['기본정보']['이름']
    origin_ctx = _build_origin_context(saju_data)

    prompt = f"""
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

형식:
## {year}년 간략 총평

(3~5줄 간결한 서술)
"""
    return call_gemini(model, prompt)


# ── 프리미엄 전체 생성 오케스트레이터 ─────────────────────────────────────────

def generate_premium_report(api_key: str, saju_data: dict,
                            target_year: int = None,
                            progress_callback=None) -> dict:
    """
    프리미엄 100페이지 리포트 전체 생성.
    월운/세운 데이터는 saju_data["월운"], saju_data["세운"] 에서 읽는다.
    Returns: 섹션별 텍스트 딕셔너리
    """
    if target_year is None:
        target_year = datetime.now().year

    model  = init_gemini(api_key)
    db     = load_db()
    results = {}

    wolun_list = saju_data.get("월운", [])
    seun_list  = saju_data.get("세운", [])

    total_steps = 6 + len(seun_list) + len(wolun_list)
    step = 0

    def progress(msg):
        nonlocal step
        step += 1
        if progress_callback:
            progress_callback(step, total_steps, msg)
        else:
            print(f"  [{step}/{total_steps}] {msg}")

    # ── 섹션 1~6: 기본 분석 ──
    print("\n📖 기본 분석 섹션 생성 중...")

    progress("성격/본질 분석 중...")
    results["personality"] = analyze_personality(model, saju_data, db)
    time.sleep(1)

    progress("재물운 분석 중...")
    results["wealth"] = analyze_wealth(model, saju_data, db)
    time.sleep(1)

    progress("직업/직장운 분석 중...")
    results["career"] = analyze_career(model, saju_data, db)
    time.sleep(1)

    progress("연애/결혼운 분석 중...")
    results["love"] = analyze_love(model, saju_data, db)
    time.sleep(1)

    progress("건강운 분석 중...")
    results["health"] = analyze_health(model, saju_data, db)
    time.sleep(1)

    progress("개운 가이드 작성 중...")
    results["lucky_charm"] = analyze_lucky_charm(model, saju_data, db)
    time.sleep(1)

    # ── 월운 루프 ──
    print("\n📆 월운 분석 생성 중...")
    results["monthly"] = {}
    for wolun in wolun_list:
        m = wolun["월"]
        progress(f"{target_year}년 {m}월 월운 분석 중...")
        results["monthly"][m] = analyze_monthly_fortune(model, saju_data, wolun)
        time.sleep(1.5)

    # ── 세운 루프 ──
    print("\n📅 세운(연운) 분석 생성 중...")
    results["yearly"] = {}
    for seun in seun_list:
        yr = seun["연도"]
        progress(f"{yr}년 세운 분석 중...")
        results["yearly"][yr] = analyze_yearly_fortune(model, saju_data, seun)
        time.sleep(1.5)

    return results


def generate_basic_report(api_key: str, saju_data: dict,
                          target_year: int = None) -> dict:
    """
    기본 리포트 생성 (목표 10페이지)
    섹션: 성격·기질 / 전반 운세 요약 / 신년 총평
    세세한 운세(월운·연운·10년대운) 없음
    """
    if target_year is None:
        target_year = datetime.now().year

    model  = init_gemini(api_key)
    db     = load_db()
    results = {}

    print("  [1/3] 성격·기질 분석 중...")
    results["personality"] = analyze_personality_basic(model, saju_data, db)
    time.sleep(1)

    print("  [2/3] 전반 운세 요약 중...")
    results["summary"] = analyze_basic_overview(model, saju_data, target_year, db)
    time.sleep(1)

    print(f"  [3/3] {target_year}년 간략 총평 중...")
    seun_list = saju_data.get("세운", [])
    this_year_seun = next((s for s in seun_list if s["연도"] == target_year), None)

    if this_year_seun:
        results["this_year"] = analyze_basic_thisyear(model, saju_data, this_year_seun)
    else:
        from saju_calculator import get_seun
        d_stem   = saju_data["일간정보"]["일간"]
        y_branch = saju_data["사주원국"]["연주"]["지지"]
        d_branch = saju_data["사주원국"]["일주"]["지지"]
        fallback_seun = get_seun(target_year, d_stem, y_branch, d_branch)
        results["this_year"] = analyze_basic_thisyear(model, saju_data, fallback_seun)

    return results


if __name__ == "__main__":
    print("Gemini 분석 모듈 로드 완료")
    print("사용법: generate_premium_report(api_key, saju_data)")