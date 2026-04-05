"""
Gemini API 기반 사주 분석 모듈
- 30년 경력 역술가 페르소나 시스템 프롬프트 고정
- 섹션별 분산 호출로 100페이지 분량 생성
- 연도별 세운 루프, 월별 월운 루프 포함

[대운/세운/월운 데이터 구조]
모든 주(柱) 데이터는 _build_pillar_block 구조를 따른다:
{
  "간지": {"천간": "丙", "지지": "午"},        ← 간지 문자
  "천간": {"문자": "丙", "오행": "화", "십성": {"값": "...", "기준": "일간"}},
  "지지": {"문자": "午", "오행": "화", "십성": {...}, "12운성": "...", "신살": [...]}
}
대운에는 "순서", "시작나이" 추가
세운에는 "연도" 추가
월운에는 "연도", "월" 추가
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
            return response.text
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


# ── 주(柱) 데이터 헬퍼 ───────────────────────────────────────────────────────

def _pillar_str(pillar: dict) -> str:
    """
    _build_pillar_block 구조에서 'XX일(오행/십성/12운성/신살)' 형태 요약 문자열 반환.
    예) "丙午 (화/식신/건록/역마살)"
    """
    gan  = pillar["간지"]["천간"]
    ji   = pillar["간지"]["지지"]
    oh   = pillar["지지"]["오행"]
    ss   = pillar["지지"]["십성"]["값"]
    un   = pillar["지지"]["12운성"]
    sal  = "/".join(pillar["지지"]["신살"]) if pillar["지지"]["신살"] else "없음"
    return f"{gan}{ji} (지지오행:{oh} / 십성:{ss} / 12운성:{un} / 신살:{sal})"


# ── 섹션별 분석 함수 ──────────────────────────────────────────────────────────

def analyze_personality(model, saju_data: dict, db: dict) -> str:
    """섹션 1: 타고난 본질 및 성격 분석 (A4 3장)"""
    day_stem = saju_data["일간정보"]["일간"]
    day_branch = saju_data["사주원국"]["일주"]["지지"]
    ilju = saju_data["사주원국"]["일주"]["간지"]
    strength = saju_data["일간정보"]["신강신약"]
    elements = saju_data["오행분포"]

    stem_info   = db["천간"].get(day_stem, {})
    branch_info = db["지지"].get(day_branch, {})

    prompt = f"""
[분석 대상 사주 데이터]
이름: {saju_data['기본정보']['이름']}
생년월일: {saju_data['기본정보']['생년월일']}
성별: {saju_data['기본정보']['성별']}
일주(핵심): {ilju} ({day_stem}일간)
신강/신약: {strength}
오행분포: 목{elements['목']} 화{elements['화']} 토{elements['토']} 금{elements['금']} 수{elements['수']}
사주원국: 연주{saju_data['사주원국']['연주']['간지']} 월주{saju_data['사주원국']['월주']['간지']} 일주{ilju} 시주{saju_data['사주원국']['시주']['간지']}

[일간 참고 데이터]
{day_stem}일간 특성: {json.dumps(stem_info, ensure_ascii=False)}
일지 {day_branch} 특성: {json.dumps(branch_info, ensure_ascii=False)}

[작성 요청]
위 사주 데이터를 바탕으로 '타고난 본질과 성격 분석' 파트를 A4 3장 이상(1,500자 이상) 분량으로 작성해주세요.

반드시 포함할 내용:
1. **일주(일간+일지)의 핵심 기질**: {ilju}일주가 가진 근본적 에너지와 삶의 방식
2. **신강/신약에 따른 심리 구조**: {strength}인 이유와 이것이 성격에 미치는 영향
3. **오행 균형 분석**: 강한 오행과 약한 오행이 성격에 미치는 구체적 영향
4. **대인관계 패턴**: 이 사주 구조가 만들어내는 인간관계 특성
5. **핵심 강점과 성장 과제**: 이 사람이 타고난 재능과 반드시 개발해야 할 영역
6. **삶의 철학적 테마**: 이 사주가 제시하는 근본적인 삶의 방향성

마크다운 형식으로 소제목을 사용하고, 각 항목을 충분히 상세히 서술하세요.
"""
    return call_gemini(model, prompt)


def analyze_wealth(model, saju_data: dict, db: dict) -> str:
    """섹션 2: 재물운 분석 (A4 2.5장)"""
    sipsung  = saju_data["십성"]
    ilju     = saju_data["사주원국"]["일주"]["간지"]
    elements = saju_data["오행분포"]

    prompt = f"""
[사주 데이터]
일주: {ilju}
십성 구성: {json.dumps(sipsung, ensure_ascii=False)}
오행분포: 목{elements['목']} 화{elements['화']} 토{elements['토']} 금{elements['금']} 수{elements['수']}
신강신약: {saju_data['일간정보']['신강신약']}

[재물운 DB 참고]
편재 특성: {json.dumps(db['십성']['편재'], ensure_ascii=False)}
정재 특성: {json.dumps(db['십성']['정재'], ensure_ascii=False)}

[작성 요청]
위 데이터를 바탕으로 '재물운 상세 분석' 파트를 A4 2.5장(1,200자) 이상 작성하세요.

포함 내용:
1. **재물 성향 분석**: 이 사주가 돈을 버는 방식과 재물과의 관계
2. **수입 패턴**: 어떤 방식으로 돈이 들어오고 나가는지
3. **재테크 적합 유형**: 안정형/투자형/사업형 중 어느 방향이 맞는지
4. **재물 위험 요소**: 조심해야 할 금전적 함정
5. **부를 늘리는 구체적 전략**: 이 사주에 맞는 실천 가능한 재물 증식 방법
6. **평생 재물 흐름**: 인생 단계별 재물운의 전반적 흐름
"""
    return call_gemini(model, prompt)


def analyze_career(model, saju_data: dict, db: dict) -> str:
    """섹션 3: 직업/직장운 분석 (A4 2.5장)"""
    day_stem = saju_data["일간정보"]["일간"]
    sipsung  = saju_data["십성"]
    strength = saju_data["일간정보"]["신강신약"]
    elements = saju_data["오행분포"]

    prompt = f"""
[사주 데이터]
일간: {day_stem} (오행: {saju_data['일간정보']['오행']})
사주원국: 연주{saju_data['사주원국']['연주']['간지']} 월주{saju_data['사주원국']['월주']['간지']} 일주{saju_data['사주원국']['일주']['간지']} 시주{saju_data['사주원국']['시주']['간지']}
십성: {json.dumps(sipsung, ensure_ascii=False)}
신강신약: {strength}
오행분포: 목{elements['목']} 화{elements['화']} 토{elements['토']} 금{elements['금']} 수{elements['수']}

[작성 요청]
'직업 및 직장운 상세 분석' 파트를 A4 2.5장(1,200자) 이상 작성하세요.

포함 내용:
1. **천직 분야 도출**: 사주 구조상 가장 빛을 발하는 직업군 (최소 5개 구체적으로)
2. **직장 생활 패턴**: 조직에서의 역할, 상하관계, 동료와의 관계 방식
3. **사업 vs 직장**: 이 사주가 독립 사업에 적합한지 직장 생활이 맞는지
4. **커리어 성장 전략**: 성공을 앞당기는 구체적인 직업 전략
5. **주의해야 할 직업적 함정**: 피해야 할 상황과 환경
6. **인생에서 가장 빛나는 직업적 시기**: 언제 절정을 맞는지
"""
    return call_gemini(model, prompt)


def analyze_love(model, saju_data: dict, db: dict) -> str:
    """섹션 4: 연애/결혼운 분석 (A4 2.5장)"""
    gender  = saju_data['기본정보']['성별']
    ilju    = saju_data['사주원국']['일주']['간지']
    sipsung = saju_data['십성']

    prompt = f"""
[사주 데이터]
성별: {gender}
일주: {ilju}
십성 구성: {json.dumps(sipsung, ensure_ascii=False)}
신강신약: {saju_data['일간정보']['신강신약']}

[작성 요청]
'연애 및 결혼운 상세 분석' 파트를 A4 2.5장(1,200자) 이상 작성하세요.

포함 내용:
1. **연애 스타일**: 이 사람이 연애에서 보여주는 고유한 패턴
2. **이상형 분석**: 사주 구조상 잘 맞는 이성의 유형
3. **연애의 장점과 단점**: 파트너에게 주는 것과 받아야 하는 것
4. **결혼 시기와 인연**: 결혼운이 강한 시기와 인연의 형태
5. **부부 관계 패턴**: 결혼 후 가정 내 역할과 관계 방식
6. **사랑을 오래 유지하는 비결**: 이 사주에 맞는 구체적인 관계 유지 전략
"""
    return call_gemini(model, prompt)


def analyze_health(model, saju_data: dict, db: dict) -> str:
    """섹션 5: 건강운 분석 (A4 2장)"""
    day_stem = saju_data["일간정보"]["일간"]
    elements = saju_data["오행분포"]
    branches = [saju_data['사주원국'][p]['지지'] for p in ['연주','월주','일주','시주']]

    weak_elem   = min(elements, key=elements.get)
    strong_elem = max(elements, key=elements.get)

    prompt = f"""
[사주 데이터]
일간: {day_stem} ({saju_data['일간정보']['오행']} 오행)
오행분포: 목{elements['목']} 화{elements['화']} 토{elements['토']} 금{elements['금']} 수{elements['수']}
강한 오행: {strong_elem}  약한 오행: {weak_elem}
지지: {' '.join(branches)}

[작성 요청]
'건강운 상세 분석' 파트를 A4 2장(1,000자) 이상 작성하세요.

포함 내용:
1. **체질 분석**: 이 사주 구조가 만들어내는 선천적 체질
2. **주의해야 할 신체 부위**: 오행 구조상 취약한 장기와 부위 (구체적으로)
3. **건강 위험 시기**: 운세 흐름상 건강에 특별히 주의할 시기
4. **권장 운동 방법**: 이 오행 구조에 맞는 최적의 운동 유형
5. **식이 요법**: 보충해야 할 오행에 맞는 음식 처방
6. **정신 건강 관리**: 이 사주의 심리적 취약점과 마음 건강 관리법
"""
    return call_gemini(model, prompt)


def analyze_lucky_charm(model, saju_data: dict, db: dict) -> str:
    """섹션 6: 개운 가이드 (A4 3장)"""
    elements  = saju_data["오행분포"]
    weak_elem = min(elements, key=elements.get)
    day_stem  = saju_data["일간정보"]["일간"]

    elem_db = db["오행개운"].get(weak_elem, {})

    prompt = f"""
[사주 데이터]
일간: {day_stem}
오행분포: 목{elements['목']} 화{elements['화']} 토{elements['토']} 금{elements['금']} 수{elements['수']}
보강 필요 오행: {weak_elem}
보강 오행 DB: {json.dumps(elem_db, ensure_ascii=False)}

[작성 요청]
'맞춤형 개운 가이드' 파트를 A4 3장(1,500자) 이상 작성하세요.

포함 내용:
1. **오행 균형 처방**: 부족한 오행을 채우는 전방위 개운 전략
2. **행운의 색상**: 착용하면 도움이 되는 색상과 피해야 할 색상 + 이유
3. **개운 음식 처방**: 매일 먹으면 좋은 음식과 피해야 할 음식
4. **생활 공간 풍수**: 집/사무실 배치 및 인테리어 개운법
5. **행운의 방향과 숫자**: 의사결정 시 활용할 방향, 숫자, 날짜
6. **정신적 개운법**: 명상, 기도, 마인드셋 관련 조언
7. **연간 개운 스케줄**: 월별로 실천할 수 있는 구체적 개운 행동 목록
"""
    return call_gemini(model, prompt)


def analyze_yearly_fortune(model, saju_data: dict, seun: dict) -> str:
    """
    세운(年運) 분석 (A4 2장)
    seun: get_seun() 반환값 (_build_pillar_block 구조 + "연도")
    """
    year       = seun["연도"]
    gan        = seun["간지"]["천간"]
    ji         = seun["간지"]["지지"]
    gan_elem   = seun["천간"]["오행"]
    gan_ss     = seun["천간"]["십성"]["값"]
    ji_elem    = seun["지지"]["오행"]
    ji_ss      = seun["지지"]["십성"]["값"]
    ji_12      = seun["지지"]["12운성"]
    ji_sal     = "/".join(seun["지지"]["신살"]) if seun["지지"]["신살"] else "없음"
    current_age = year - int(saju_data['기본정보']['생년월일'][:4]) + 1

    prompt = f"""
[분석 대상]
이름: {saju_data['기본정보']['이름']} ({current_age}세, {year}년)
본인 사주: 연{saju_data['사주원국']['연주']['간지']} 월{saju_data['사주원국']['월주']['간지']} 일{saju_data['사주원국']['일주']['간지']} 시{saju_data['사주원국']['시주']['간지']}
일간: {saju_data['일간정보']['일간']} ({saju_data['일간정보']['오행']})
신강신약: {saju_data['일간정보']['신강신약']}

[{year}년 세운 데이터]
세운 간지: {gan}{ji}년
천간 {gan}: 오행={gan_elem}, 일간과의 십성={gan_ss}
지지 {ji}: 오행={ji_elem}, 십성={ji_ss}, 12운성={ji_12}, 신살={ji_sal}

[작성 요청]
{year}년({gan}{ji}년) 연간 운세를 A4 2장(1,000자) 이상 상세히 분석하세요.

포함 내용:
1. **{year}년 전체 기운**: 세운 천간/지지와 사주 원국의 상호작용 (신살 {ji_sal} 영향 포함)
2. **재물운**: {year}년 돈과 재물의 흐름
3. **직업/직장운**: {year}년 커리어와 사업의 변화
4. **인간관계/연애운**: {year}년 중요한 인연과 관계 변화
5. **건강운**: {year}년 특별히 주의할 건강 사항
6. **총평 및 핵심 조언**: {year}년을 성공적으로 보내기 위한 핵심 전략 3가지
"""
    return call_gemini(model, prompt)


def analyze_monthly_fortune(model, saju_data: dict, wolun: dict) -> str:
    """
    월운(月運) 분석 (A4 1장)
    wolun: get_wolun() 반환값 (_build_pillar_block 구조 + "연도", "월")
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

    prompt = f"""
[사주 데이터]
일간: {saju_data['일간정보']['일간']} ({saju_data['일간정보']['오행']})
사주원국: 연{saju_data['사주원국']['연주']['간지']} 월{saju_data['사주원국']['월주']['간지']} 일{saju_data['사주원국']['일주']['간지']} 시{saju_data['사주원국']['시주']['간지']}

[{year}년 {month_names[month-1]} 월운 데이터]
월운 간지: {gan}{ji}월
천간 {gan}: 오행={gan_elem}, 십성={gan_ss}
지지 {ji}: 오행={ji_elem}, 십성={ji_ss}, 12운성={ji_12}, 신살={ji_sal}

[작성 요청]
{year}년 {month_names[month-1]}의 월별 운세를 A4 1장(500자) 이상 작성하세요.

포함 내용:
1. **이달의 전체 기운 한 줄 요약** (신살 {ji_sal} 영향 반영)
2. **재물**: 이달 금전 흐름 (구체적 조언 포함)
3. **직장/사업**: 이달 업무와 커리어 포인트
4. **인간관계**: 이달 중요한 만남과 관계
5. **건강**: 이달 특별 주의 사항
6. **행운의 날짜와 조심할 날짜**: 각 3개씩
7. **이달의 핵심 메시지**: 한 문장으로
"""
    return call_gemini(model, prompt)


def analyze_daewun(model, saju_data: dict, daewun: dict) -> str:
    """
    대운 분석 (A4 1.5장)
    daewun: calculate_saju()["대운"][i] (_build_pillar_block 구조 + "순서", "시작나이")
    """
    start_age = daewun["시작나이"]
    gan       = daewun["간지"]["천간"]
    ji        = daewun["간지"]["지지"]
    gan_elem  = daewun["천간"]["오행"]
    gan_ss    = daewun["천간"]["십성"]["값"]
    ji_elem   = daewun["지지"]["오행"]
    ji_ss     = daewun["지지"]["십성"]["값"]
    ji_12     = daewun["지지"]["12운성"]
    ji_sal    = "/".join(daewun["지지"]["신살"]) if daewun["지지"]["신살"] else "없음"

    prompt = f"""
[사주 데이터]
일간: {saju_data['일간정보']['일간']} ({saju_data['일간정보']['오행']})
사주원국: 연{saju_data['사주원국']['연주']['간지']} 월{saju_data['사주원국']['월주']['간지']} 일{saju_data['사주원국']['일주']['간지']} 시{saju_data['사주원국']['시주']['간지']}

[대운 데이터]
{start_age}~{start_age+9}세 대운: {gan}{ji}
천간 {gan}: 오행={gan_elem}, 십성={gan_ss}
지지 {ji}: 오행={ji_elem}, 십성={ji_ss}, 12운성={ji_12}, 신살={ji_sal}

[작성 요청]
{start_age}~{start_age+9}세 대운 분석을 A4 1.5장(700자) 이상 작성하세요.
이 10년 동안의 전반적 흐름, 재물/직업/건강/인간관계 전망,
신살({ji_sal}) 영향, 핵심 조언을 포함하세요.
"""
    return call_gemini(model, prompt)


# ── 프리미엄 전체 생성 오케스트레이터 ─────────────────────────────────

def generate_premium_report(api_key: str, saju_data: dict,
                            target_year: int = None,
                            progress_callback=None) -> dict:
    """
    프리미엄 100페이지 리포트 전체 생성.
    세운/월운 데이터는 saju_data["세운"], saju_data["월운"] 에서 읽는다.
    Returns: 섹션별 텍스트 딕셔너리
    """
    if target_year is None:
        target_year = datetime.now().year

    model  = init_gemini(api_key)
    db     = load_db()
    results = {}

    seun_list  = saju_data.get("세운", [])   # get_seun() 구조 리스트
    wolun_list = saju_data.get("월운", [])   # get_wolun() 구조 리스트

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

    # ── 세운 루프 (saju_data["세운"] 사용) ──
    print("\n📅 세운(연운) 분석 생성 중...")
    results["yearly"] = {}
    for seun in seun_list:
        yr = seun["연도"]
        progress(f"{yr}년 세운 분석 중...")
        results["yearly"][yr] = analyze_yearly_fortune(model, saju_data, seun)
        time.sleep(1.5)

    # ── 월운 루프 (saju_data["월운"] 사용) ──
    print("\n📆 월운 분석 생성 중...")
    results["monthly"] = {}
    for wolun in wolun_list:
        m = wolun["월"]
        progress(f"{target_year}년 {m}월 월운 분석 중...")
        results["monthly"][m] = analyze_monthly_fortune(model, saju_data, wolun)
        time.sleep(1.5)

    return results


def generate_basic_report(api_key: str, saju_data: dict,
                          target_year: int = None) -> dict:
    """기본 리포트 생성 (핵심 섹션만)"""
    if target_year is None:
        target_year = datetime.now().year

    model  = init_gemini(api_key)
    db     = load_db()
    results = {}

    print("  [1/3] 성격 분석 중...")
    results["personality"] = analyze_personality(model, saju_data, db)
    time.sleep(1)

    print("  [2/3] 재물/직업/연애/건강 요약 분석 중...")
    prompt = f"""
[사주 데이터]
{json.dumps(saju_data, ensure_ascii=False, indent=2)}

[작성 요청]
위 사주를 바탕으로 재물운, 직업운, 연애운, 건강운을 각각 300자씩 총 1,200자 이상으로 요약 분석하세요.
각 분야별 소제목을 사용하고, 핵심 내용과 실천 조언을 포함하세요.
"""
    results["summary"] = call_gemini(model, prompt)
    time.sleep(1)

    # 올해 세운 데이터 사용
    seun_list = saju_data.get("세운", [])
    this_year_seun = next((s for s in seun_list if s["연도"] == target_year), None)

    print(f"  [3/3] {target_year}년 올해 운세 분석 중...")
    if this_year_seun:
        results["this_year"] = analyze_yearly_fortune(model, saju_data, this_year_seun)
    else:
        # 세운 데이터 없으면 간단 프롬프트로 대체
        from saju_calculator import get_seun
        d_stem   = saju_data["일간정보"]["일간"]
        y_branch = saju_data["사주원국"]["연주"]["지지"]
        fallback_seun = get_seun(target_year, d_stem, y_branch)
        results["this_year"] = analyze_yearly_fortune(model, saju_data, fallback_seun)

    return results


if __name__ == "__main__":
    print("Gemini 분석 모듈 로드 완료")
    print("사용법: generate_premium_report(api_key, saju_data)")