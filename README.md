# AI 사주 리포트 자동 생성 시스템

> 생년월일·시각을 입력하면 만세력을 자동 계산하고, Gemini AI가 섹션별 분석을 생성하여 PDF 리포트로 출력하는 사주명리 자동화 시스템.

<img src="https://github.com/user-attachments/assets/8625645b-198a-414d-b13c-24c976429310" width="400" />

---

## 기술 스택

| 분류 | 기술 |
|---|---|
| 언어 | Python 3.10+ |
| AI API | Google Gemini REST API (`gemini-3-flash-preview`) |
| PDF 생성 | fpdf2 |
| 역법 계산 | ephem (태양 황경 기반 절기 계산) |
| 음력 변환 | korean-lunar-calendar |
| HTTP 클라이언트 | requests |
| 환경변수 관리 | python-dotenv |
| 폰트 | Noto Sans KR (Regular / Bold / Light) |

---

## 폴더 구조

```
AI-SAJU-ANALYZER/
├── main.py                          # 진입점 — 모드 선택 라우터
├── .env                             # 환경변수 (GEMINI_API_KEYS)
├── .gitignore
├── db_knowledge.json                # 천간·지지·십성 참고 지식 DB
├── fonts/
│   ├── NotoSansKR-Regular.ttf
│   ├── NotoSansKR-Bold.ttf
│   └── NotoSansKR-Light.ttf
├── outputs/                         # 생성된 PDF·JSON 저장 디렉토리
├── core/                            # 도메인 순수 계산 레이어
│   ├── constants.py                 # 천간·지지·오행 등 명리학 기본 상수
│   ├── shinsal.py                   # 신살 테이블 및 판별 함수
│   ├── calendar_engine.py           # 절기 계산, 음력 변환, 주(柱) 산출
│   └── saju_calculator.py           # 8글자·십성·대운·세운·월운 조립
├── analysis/                        # AI 분석 레이어
│   ├── gemini_client.py             # KeyPool, REST 호출, 재시도 로직
│   ├── prompt_builder.py            # 사주 컨텍스트 문자열 조립
│   ├── prompt_templates.py          # 섹션별 프롬프트 f-string 템플릿
│   ├── sections_premium.py          # 프리미엄 섹션 분석 함수 (8개 + 세운·월운)
│   ├── sections_basic.py            # 기본 섹션 분석 함수 (3개)
│   └── report_generator.py          # 전체 리포트 생성 오케스트레이터
├── app/                             # 애플리케이션 I/O·파이프라인 레이어
│   ├── user_input.py                # CLI 입력 수집, 간지 수동 수정
│   ├── pipeline.py                  # 전체 파이프라인 실행
│   ├── modes.py                     # 모드 2·3·4 실행 핸들러
│   ├── progress.py                  # 분석 진행 상태 관리
│   └── sample_data.py               # API 키 없을 때 폴백 샘플 텍스트
└── pdf/                             # PDF 렌더링 레이어
    ├── styles.py                    # 색상 상수, 폰트 경로
    ├── markdown_parser.py           # 마크다운 → 블록 리스트 변환
    ├── base_pdf.py                  # SajuPDF 기본 클래스 (폰트·헤더·공통 드로잉)
    ├── pages_common.py              # 표지·목차·원국표·에필로그 페이지 빌더
    ├── pages_analysis.py            # AI 분석 섹션 페이지 빌더
    ├── pages_fortune.py             # 세운표·월운표·대운표 페이지 빌더 (미사용)
    └── generator.py                 # generate_pdf() 진입점
```

---

## 설치 및 실행

### 1. 의존성 설치

```bash
pip install fpdf2 ephem korean-lunar-calendar requests python-dotenv
```

### 2. 환경변수 설정

프로젝트 루트에 `.env` 파일을 생성한다.

```dotenv
GEMINI_API_KEYS=your_api_key_1,your_api_key_2,your_api_key_3
```

여러 개의 API 키를 콤마로 구분하여 입력하면 라운드 로빈 방식으로 순환 사용된다.

### 3. 실행

```bash
python main.py
```

실행 시 4가지 모드 중 하나를 선택한다.

```
모드 선택:
  1: 전체 실행 (사주 계산 → AI 분석 → PDF)
  2: 문서만 재생성 (기존 analysis.json → PDF)
  3: AI 분석 재실행 (기존 사주 데이터 재사용, 타입 변경 가능)
  4: 프리미엄 부분 재호출 (중단된 분석 이어하기 / 특정 항목만 재호출)
```

### 4. 출력물 확인

실행 완료 후 `outputs/saju_{이름}_{타임스탬프}/` 디렉토리에 다음 파일이 생성된다.

```
outputs/saju_홍길동_20260507_120000/
├── saju_data.json             # 만세력 계산 결과
├── analysis_basic.json        # 기본 리포트 AI 분석 결과
├── analysis_premium.json      # 프리미엄 리포트 AI 분석 결과
├── analysis_progress.json     # 프리미엄 분석 진행 상태 (재시작용)
├── [기본] 사주리포트_홍길동님.pdf
└── [프리미엄] 사주리포트_홍길동님.pdf
```

---

## 환경변수 목록

| 변수명 | 필수 여부 | 설명 |
|---|---|---|
| `GEMINI_API_KEYS` | 선택 (없으면 샘플 텍스트 사용) | Gemini API 키. 콤마(`,`)로 구분하여 여러 개 입력 가능. 키 미설정 시 샘플 텍스트로 PDF만 생성됨. |

---

## 핵심 기능

### 만세력 자동 계산
- 생년월일·시각을 입력하면 연주·월주·일주·시주 8글자를 자동 산출
- 야자시(夜子時) 처리 지원: 23:30 이후 출생 시 전통 방식과 현대 명리 방식 선택 가능
- `ephem` 라이브러리로 태양 황경을 계산하여 절기 기반 월주 산출 (오호둔법)
- 십성·12운성·신살·오행 분포·신강신약·대운수 자동 계산

### 신살 계산
- 12신살 (겁살~화개살): 년지·일지 이중 기준 산출
- 일간 기준 신살: 천을귀인·문창귀인·홍염살·학당귀인·양인살
- 특수 신살: 백호대살·괴강살·원진살·귀문관살·삼재·공망

### AI 분석 생성 (Gemini API)
- **프리미엄 리포트**: 8개 분석 섹션 + 세운(10년) + 월운(12개월) = 최대 30개 API 호출
  - 타고난 본질과 성격 / 재물운 / 직업운 / 연애운 / 건강운 / 개운 가이드 / 인간관계·가족운 / 인생 상승기·저운
- **기본 리포트**: 성격·기질 / 전반 운세 요약 / 신년 총평 = 3개 API 호출
- 30년 경력 역술가 페르소나 시스템 프롬프트 적용
- 한자 표기 규칙·금지 패턴·문체 규칙을 시스템 프롬프트에 명시

### 멀티 API 키 라운드 로빈 (KeyPool)
- 여러 개의 Gemini API 키를 `cycle()` 기반으로 순환 사용
- HTTP 503·429 응답 시 즉시 다음 키로 Failover (대기 없음)
- 인증 오류(401·403) 시 Fatal sentinel 반환 후 파이프라인 중단
- 최대 재시도 횟수: `len(pool) × 3`

### 프리미엄 분석 재시작 (Resume)
- 분석 중 중단되어도 `analysis_progress.json`에 완료 항목 자동 저장
- 모드 4에서 미완료 항목만 선택적으로 재호출 가능
- 번호 범위 지정 가능 (예: `16-30`, `5 12 27`)

### PDF 생성
- A4 세로 형식, fpdf2 기반 한국어 폰트(Noto Sans KR) 렌더링
- 표지·목차·사주 원국표·오행 분포도·AI 분석 섹션·세운표·월운표·대운표·에필로그 자동 구성
- AI 응답의 마크다운(`##`, `###`, `-`, `**`) 파싱 후 계층적 렌더링
- 페이지 넘침 시 자동 페이지 추가 (흐름 유지)

### 사주 원국 수정
- 계산 결과 확인 후 천간·지지를 독음(갑·을·병… / 자·축·인…) 입력으로 직접 수정
- 수정 후 십성·12운성·신살·대운 전체 재계산

---

## API 엔드포인트 요약

이 프로젝트는 CLI 기반 로컬 실행 애플리케이션으로, 별도의 HTTP 서버 엔드포인트를 제공하지 않는다.

외부 API 호출은 다음 1개이다.

| 방향 | 메서드 | 엔드포인트 | 설명 |
|---|---|---|---|
| 아웃바운드 | `POST` | `https://generativelanguage.googleapis.com/v1beta/models/gemini-3-flash-preview:generateContent?key={API_KEY}` | Gemini 텍스트 생성 API. 사주 분석 프롬프트를 전송하고 분석 텍스트를 반환받음. |
