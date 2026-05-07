"""
Gemini API 클라이언트.

담당 기능:
  - KeyPool: 멀티 API 키 라운드 로빈 관리
  - call_gemini: REST API 직접 호출 with Failover
  - _checked_call: sentinel 검사 후 예외 변환
  - load_db: 지식 DB 로드
  - EXPERT_SYSTEM_PROMPT: 30년 역술가 시스템 프롬프트 상수
"""

import json
import os
import random
import re
import time
from itertools import cycle

import requests

# ── 30년 경력 역술가 시스템 프롬프트 ─────────────────────────────────────────

EXPERT_SYSTEM_PROMPT = """당신은 30년 경력의 대한민국 최고 역술가입니다.

[정체성]
- 사주명리학, 자미두수, 기문둔갑에 정통한 동양철학 박사
- 3대째 내려오는 전통 역술 가문 출신
- 수만 명의 사주를 직접 분석한 실전 경험 보유
- 현대 심리학과 코칭 기법을 접목한 현대적 역술 선도

[핵심 접근 방식 - 가장 중요]
사주는 '운명 예언서'가 아니라 '성향과 라이프스타일 분석 도구'다.
- 추상적 기운 설명 대신, 현대인의 일상으로 번역하라.
  예) "비겁이 강하다" → "혼자서 다 하려는 사람이다. 동업보다 1인 사업이 맞는 구조다."
  예) "무관 사주" → "조직보다 자기 방식대로 사는 게 스트레스가 훨씬 적은 유형이다."
  예) "식상이 발달했다" → "가르치고, 만들고, 표현하는 것에서 에너지가 생기는 사람이다."
- '혼자 사는 게 나은 사주', '남 밑에서는 절대 못 버티는 사주', '돈을 벌어도 쌓지 못하는 구조'처럼
  일반인이 바로 이해하는 언어로 먼저 말하고, 그 뒤에 이유를 설명하라.

[절대 금지 작성 패턴 - 반드시 준수]
아래 구조로 문장을 쓰는 것을 엄격히 금지한다.

금지 패턴 1 — 개념 설명 후 결론 도출
  "OO(한자, 설명)이/가 있어 → ~한 경향이 있습니다/있어요"
  "OO의 기운이 강하게 자리 잡고 있어 → ~한 편입니다"
  "OO살의 영향으로 → ~하는 모습이 나타납니다"
  나쁜 예) "인성(印星, 나를 돕는 기운)이 두텁게 자리 잡고 있어, 학습 능력이 탁월합니다."
  좋은 예) "뭔가를 배울 때 남들보다 훨씬 빠르게 흡수하는 편이에요. 지식이 쌓이는 게 눈에 보일 정도예요."

금지 패턴 2 — 이론 먼저, 삶 나중
  "~의 구조입니다. 따라서 ~한 사람입니다."
  "~이 작용하고 있습니다. 이는 ~을 의미합니다."
  나쁜 예) "식상생재의 구조입니다. 따라서 자신의 역량을 발휘해 재물을 창출하는 능력이 탁월합니다."
  좋은 예) "실력을 드러낼수록 돈이 따라오는 구조예요. 월급보다 성과급, 고용보다 프리랜서 쪽이 훨씬 잘 맞아요."

금지 패턴 3 — 한자 용어 두 개 이상 나열 후 설명
  "A(한자)와 B(한자)가 조화를 이루고 있어 → ~한 재능이 있습니다"
  나쁜 예) "식신(食神)과 상관(傷官)이 적절히 조화를 이루고 있어, 깊은 생각을 논리적으로 전달하는 재능이 있습니다."
  좋은 예) "머릿속에서 정리한 걸 말로 풀어낼 때 설득력이 살아나는 유형이에요. 복잡한 내용을 쉽게 설명하는 데 재능이 있어요."

올바른 작성 순서
  1) 이 사람의 실제 행동·감정·패턴을 먼저 구체적으로 서술
  2) 사주 근거는 뒤에서 한 번만 짧게 언급하거나 생략 가능

[분석 원칙]
1. 사주 이론 설명이 먼저가 아니라, 이 사람의 삶이 먼저다.
2. 부정적 운도 긍정적 방향으로 전환하는 조언을 제공한다
3. 구체적이고 실천 가능한 개운법을 반드시 포함한다
4. 현대인의 삶에 적용 가능한 현실적 조언을 한다
5. 학문적 근거(사주 원리)는 뒷받침 역할로만 쓴다

[문체 - 반드시 준수]
- 술술 읽히는 자연스러운 글말체를 사용한다.
- "~해야 합니다", "~반드시 필요합니다", "~경계해야 합니다" 등 훈계조 표현을 지양한다.
  대신 "~하면 훨씬 수월해요", "~쪽이 더 잘 맞아요", "~때 힘이 빠질 수 있어요"처럼 자연스럽게 쓴다.
- 한 단락 안에 "~해야 합니다" 또는 "~필요합니다"가 2번 이상 나오지 않도록 할 것
- 한 문장 안에 괄호(설명) 삽입을 최대 1개로 제한한다.
  두 개 이상의 한자 용어가 연달아 나올 경우, 하나는 풀어서 본문에 녹인다.
- 어려운 한자 용어는 반드시 한글로 풀어서 설명
- A4 기준 분량을 충실히 채우는 상세한 서술
- 독자가 자신의 이야기를 읽는 것처럼 개인화된 표현 사용
- 따뜻하고 진지하며 전문적인 어조 유지

[호칭 규칙 - 반드시 준수]
- 의뢰인을 호칭할 때는 반드시 성(姓)을 포함한 전체 이름에 '님'을 붙인다
  예) 이름이 '이혜수'이면 → '이혜수 님' (O) / '혜수 님' (X)
- 이름이 두 글자(성+이름 1자)인 경우도 동일하게 전체 이름 사용
- 본문 중간에 이름을 줄여 부르는 것을 절대 금지한다

[한자 표기 규칙 - 반드시 준수]
- 모든 한자 용어는 반드시 "한국어(한자)" 형식으로 최초 1회만 표기한다.
   예) 자수(子水), 오화(午火)
- 한자를 단독으로 사용하는 것을 절대 금지한다.
   예) "癸수", "己토", "丙子년" (X)
- 동일한 용어는 문단 내에서 1회만 한자를 병기하고, 이후에는 한글만 사용한다.
   예) "계수(癸水)는 ..." → 이후 "계수는 ..." (O)
- 일반 독자가 이해하기 어려운 한자어는 반드시 풀어서 설명한다.
   예) "편관(偏官)" → "편관(偏官, 나를 압박하고 단련시키는 기운)"
- 한자 사용은 '설명 목적'일 때만 제한적으로 사용하며, 가독성을 해치는 과도한 한자 사용을 금지한다.

[시작 형식 - 반드시 준수]
- 각 섹션은 반드시 분석 본문으로 바로 시작한다
- "반갑습니다", "안녕하세요" 등의 인사말로 시작하는 것을 절대 금지한다
- "저는 30년 경력의~", "역술가입니다" 등 본인 소개 문장을 절대 금지한다
- 마크다운 제목(##) 또는 분석 내용으로 즉시 시작할 것

[중요 지침]
- 운명론적 결정론을 피하고 '경향성'으로 표현한다
- "반드시 ~한다"보다 "~하는 편이에요", "~하는 경향이 강해요"로 표현한다
- 어떤 운세든 노력과 의지로 극복/증폭 가능함을 강조한다"""


# ── Gemini REST API 설정 ──────────────────────────────────────────────────────

_GEMINI_REST_URL = (
    "https://generativelanguage.googleapis.com/v1beta/"
    "models/gemini-3-flash-preview:generateContent"
)

# sentinel 상수 — 오케스트레이터가 실패 감지에 사용
_API_ERROR_SENTINEL = "__API_ERROR__"
_API_FATAL_SENTINEL = "__API_FATAL__"

_RETRYABLE_ERRORS = (
    "503", "502", "500", "429",
    "ResourceExhausted", "ServiceUnavailable",
    "overloaded", "quota", "rate limit", "deadline", "timeout",
)
_FATAL_ERRORS = (
    "API_KEY_INVALID", "PermissionDenied",
    "InvalidArgument", "INVALID_ARGUMENT", "NOT_FOUND",
)


# ── KeyPool ───────────────────────────────────────────────────────────────────

class KeyPool:
    """
    여러 Gemini API 키를 라운드 로빈으로 순환 관리.

    genai.configure() 전역 상태 문제를 피하기 위해
    REST API 직접 호출 방식을 채택 — 키를 URL 파라미터로 전달하여
    매 호출마다 완전히 독립적인 인증이 보장된다.
    """

    def __init__(self, keys: list[str]) -> None:
        if not keys:
            raise ValueError("API 키가 1개 이상 필요합니다.")
        self._keys: list[str] = [k.strip() for k in keys if k.strip()]
        self._pool = cycle(self._keys)
        self._current: str = next(self._pool)

    def rotate(self) -> None:
        """Failover 시 다음 키로 즉시 전환."""
        self._current = next(self._pool)

    def next_key(self) -> str:
        """정상 순환용: 다음 키로 전진 후 반환."""
        self._current = next(self._pool)
        return self._current

    @property
    def current_key(self) -> str:
        return self._current

    @property
    def key_hint(self) -> str:
        """보안용 로그 힌트 (끝 4자리만 노출)."""
        return f"...{self._current[-4:]}"

    def __len__(self) -> int:
        return len(self._keys)


def make_key_pool(api_keys_input) -> KeyPool:
    """
    문자열(콤마 구분) 또는 리스트를 받아 KeyPool 생성.
    둘 다 없으면 환경변수 GEMINI_API_KEYS로 폴백.
    """
    if isinstance(api_keys_input, list):
        keys = api_keys_input
    elif isinstance(api_keys_input, str) and api_keys_input:
        keys = api_keys_input.split(",")
    else:
        raw = os.getenv("GEMINI_API_KEYS", "")
        keys = raw.split(",") if raw else []

    keys = [k.strip() for k in keys if k.strip()]
    if not keys:
        raise ValueError(
            "유효한 Gemini API 키가 없습니다. .env의 GEMINI_API_KEYS를 확인하세요."
        )
    return KeyPool(keys)


# ── API 호출 ──────────────────────────────────────────────────────────────────

def _clean_markdown(text: str) -> str:
    """AI 응답에서 마크다운 강조 기호(**) 제거."""
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
    text = re.sub(r'\*(.+?)\*',     r'\1', text)
    return text


def call_gemini(
    pool: KeyPool,
    prompt: str,
    max_failover: int = None,
    base_delay: float = 2.0,
    max_delay: float = 30.0,
) -> str:
    """
    Gemini REST API 직접 호출 with 멀티 키 Failover.

    - 성공       → pool.next_key() 로 키 전진 후 텍스트 반환
    - 503/429 등 → pool.rotate() 후 즉시 재시도 (대기 없음)
    - 인증 오류  → _API_FATAL_SENTINEL 반환
    - 재시도 소진 → _API_ERROR_SENTINEL 반환
    """
    if max_failover is None:
        max_failover = len(pool) * 3

    payload = {
        "system_instruction": {
            "parts": [{"text": EXPERT_SYSTEM_PROMPT}]
        },
        "contents": [
            {"role": "user", "parts": [{"text": prompt}]}
        ],
        "generationConfig": {
            "temperature": 0.1,
            "maxOutputTokens": 8192,
        },
    }

    for attempt in range(max_failover):
        key = pool.current_key
        url = f"{_GEMINI_REST_URL}?key={key}"

        try:
            resp = requests.post(url, json=payload, timeout=120)

            if resp.status_code in (500, 502, 503, 429):
                err_body = resp.text[:120]
                if attempt == max_failover - 1:
                    print(f"  ❌ 최대 재시도 {max_failover}회 초과. 포기합니다.")
                    return _API_ERROR_SENTINEL
                print(
                    f"  ⚠️  HTTP {resp.status_code} [{pool.key_hint}] → "
                    f"즉시 다음 키로 교체 (시도 {attempt + 1}/{max_failover}) "
                    f"[{err_body}]"
                )
                pool.rotate()
                continue

            if resp.status_code in (400, 404):
                print(f"  ❌ 잘못된 요청({resp.status_code}) [{pool.key_hint}]: {resp.text[:200]}")
                return _API_FATAL_SENTINEL

            if resp.status_code in (401, 403):
                print(f"  ❌ 인증 오류({resp.status_code}) [{pool.key_hint}]: {resp.text[:120]}")
                return _API_FATAL_SENTINEL

            resp.raise_for_status()

            data = resp.json()
            text = data["candidates"][0]["content"]["parts"][0]["text"]
            print(f"  ✅ 성공 [{pool.key_hint}]")
            pool.next_key()
            return _clean_markdown(text)

        except requests.exceptions.Timeout:
            if attempt == max_failover - 1:
                print(f"  ❌ 타임아웃 최대 재시도 초과.")
                return _API_ERROR_SENTINEL
            print(
                f"  ⚠️  타임아웃 [{pool.key_hint}] → 즉시 다음 키로 교체 "
                f"(시도 {attempt + 1}/{max_failover})"
            )
            pool.rotate()
            continue

        except Exception as e:
            err_str = str(e)
            if any(kw in err_str for kw in _FATAL_ERRORS):
                print(f"  ❌ 치명적 오류 [{pool.key_hint}]: {err_str[:120]}")
                return _API_FATAL_SENTINEL
            wait = min(
                base_delay * (2 ** (attempt % 4)) + random.uniform(0, 1),
                max_delay,
            )
            print(
                f"  ⚠️  알 수 없는 오류 [{pool.key_hint}] "
                f"(시도 {attempt + 1}/{max_failover}), "
                f"{wait:.1f}초 후 재시도... [{err_str[:80]}]"
            )
            time.sleep(wait)
            pool.rotate()

    return _API_ERROR_SENTINEL


# ── 예외 / checked call ───────────────────────────────────────────────────────

class ApiUnavailableError(Exception):
    """503 등 서버 에러로 API를 사용할 수 없을 때 오케스트레이터가 raise."""
    pass


def checked_call(pool: KeyPool, prompt: str) -> str:
    """
    call_gemini 호출 후 sentinel을 검사한다.

    - _API_ERROR_SENTINEL / _API_FATAL_SENTINEL → ApiUnavailableError raise
    - 정상 텍스트                                → 그대로 반환
    """
    result = call_gemini(pool, prompt)
    if result in (_API_ERROR_SENTINEL, _API_FATAL_SENTINEL):
        raise ApiUnavailableError(
            "Gemini API 호출 실패 — 전체 파이프라인을 중단합니다."
        )
    return result


# ── 지식 DB ───────────────────────────────────────────────────────────────────

def load_db() -> dict:
    """
    db_knowledge.json 로드.

    이 파일은 프로젝트 루트(fortune_teller/ 상위)에 위치한다.
    """
    db_path = os.path.join(
        os.path.dirname(__file__),  # analysis/
        "..",                        # fortune_teller/
        "db_knowledge.json",
    )
    with open(os.path.normpath(db_path), "r", encoding="utf-8") as f:
        return json.load(f)
