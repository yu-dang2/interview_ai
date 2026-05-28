# JD 파서 모듈

채용 공고를 JSON으로 파싱하는 모듈입니다.
텍스트 입력, 이미지 업로드, URL 크롤링 3가지 입력 방식을 지원합니다.


---


## 설치

```bash
# 필수
pip install requests

# 이미지 파싱 또는 URL 크롤링을 사용할 경우
pip install openai playwright
playwright install chromium
```


---


## 입력 방식


### 1. 텍스트 직접 입력 (기본)

사용자가 채용 공고 텍스트를 복사해서 붙여넣는 방식입니다.

```python
from agent.parsers.jd_parser_free import parse_jd_from_text

result = parse_jd_from_text("채용 공고 텍스트...")
print(result)
```


### 2. 이미지 업로드

채용 공고 스크린샷을 GPT-4o Vision 또는 Gemini로 텍스트 변환 후 파싱합니다.
잡코리아, 사람인 등 이미지 기반 채용 공고에 사용합니다.

```python
from agent.parsers.jd_parser_free import parse_jd_from_image

result = parse_jd_from_image("screenshot.png")
```

처리 흐름:

```
이미지 업로드
  -> Vision AI로 텍스트 추출
  -> JD 파싱 프롬프트로 JSON 추출
```


### 3. URL 크롤링

Playwright로 채용 공고 페이지를 크롤링하여 파싱합니다.
"상세 정보 더 보기" 같은 동적 로딩 콘텐츠도 자동으로 처리합니다.

```python
from agent.parsers.jd_parser_free import parse_jd_from_url

result = parse_jd_from_url("https://www.wanted.co.kr/wd/328573")
```

처리 흐름:

```
URL 입력
  -> Playwright로 페이지 열기
  -> "더 보기" 버튼 자동 클릭
  -> 텍스트 추출
  -> JD 파싱 프롬프트로 JSON 추출
```

지원 사이트: 원티드, 잡코리아, 사람인, 프로그래머스


---


## 출력 형식

모든 입력 방식에서 동일한 JSON 형식으로 출력됩니다.

```json
{
  "job_title": "Backend 개발자",
  "company": "콘텐츠웨이브(wavve)",
  "required_skills": ["Java", "AWS", "K8S"],
  "preferred_skills": ["MSA 설계 경험", "대용량 트래픽 처리"],
  "soft_skills": ["커뮤니케이션 스킬", "협업 능력", "주인의식"],
  "experience_years": "3년 이상",
  "main_tasks": ["서비스 API 설계 및 개발"],
  "interview_keywords": ["API 설계", "클라우드 운영", "대용량 트래픽"]
}
```

각 필드 설명:

- required_skills: 자격요건에 해당하는 기술 스택, 도구, 프레임워크
- preferred_skills: 우대사항에 해당하는 기술 스택, 도구, 프레임워크
- soft_skills: 인성, 태도, 협업 관련 항목 (면접 인성 질문 생성에 활용)
- interview_keywords: 기술 + 인성을 종합하여 면접에서 검증할 키워드를 추론


---


## 에러 핸들링

파싱 결과는 3가지 상태로 반환됩니다.


### 성공 (success)

모든 필수 항목이 정상적으로 파싱된 경우입니다.


### 부분 성공 (partial)

일부 항목이 누락된 경우입니다.
사용자에게 부족한 부분을 텍스트로 직접 입력하라고 안내합니다.

```
채용 공고를 파싱했지만, 일부 항목(자격요건, 우대사항)을 찾지 못했습니다.
다음 항목을 텍스트로 직접 입력해주시면 더 정확한 면접 질문을 생성할 수 있습니다.
```


### 실패 (failed)

파싱이 불가능한 경우입니다.
입력 방식에 따라 다른 대체 방법을 안내합니다.

- URL 실패시: "스크린샷으로 찍어서 이미지로 업로드" 또는 "텍스트로 붙여넣기" 안내
- 이미지 실패시: "더 선명하게 다시 캡처" 또는 "텍스트로 직접 입력" 안내
- 텍스트 실패시: "주요업무, 자격요건, 우대사항이 포함되어 있는지 확인" 안내


---


## CLI 테스트 (무료)


### 사전 준비

1. https://aistudio.google.com/apikey 에서 Gemini API 키를 발급받습니다 (무료).

2. API 키를 환경변수로 설정합니다.

```bash
# Windows PowerShell
$env:GEMINI_API_KEY = "your-key"

# Mac / Linux
export GEMINI_API_KEY=your-key
```

3. 필요한 패키지를 설치합니다.

```bash
pip install requests
```


### 테스트 실행

```bash
# 텍스트 입력 테스트
python jd_parser_free.py text

# 이미지 파싱 테스트
python jd_parser_free.py image screenshot.png

# URL 크롤링 테스트 (playwright 추가 설치 필요)
pip install playwright
playwright install chromium
python jd_parser_free.py url https://www.wanted.co.kr/wd/328573
```


---


## 테스트 결과


### JD 파싱 (프롬프트 v2)


#### wavve Backend 개발자

- required_skills: Go, Java, Kotlin, Node.js 등 11개 -- 정상
- preferred_skills: MSA, 대용량 트랜잭션, Kafka 등 7개 -- 정상
- soft_skills: 빈 배열 (공고에 인성 항목 없음) -- 정상


#### 배민 Server(푸드주문시스템)

- required_skills: Java, Kotlin, Spring Framework 등 6개 -- 정상
- preferred_skills: AWS, Kafka, Redis, Elasticsearch 등 14개 -- 정상
- soft_skills: 커뮤니케이션, 주인의식, 협업 능력 등 9개 -- 정상
- 인성/기술 분리 정상 동작 확인


### 이력서 파싱 (프롬프트 v1)


#### 가상 이력서 (백엔드 개발자 김서준, 4년차)

- skills: Java, Kotlin, Python, Spring Boot, JPA, AWS, Redis, Kafka 등 21개 -- 정상
- experience: 회사별 분리 (ABC테크, XYZ소프트) -- 정상
- projects: 경력에서 프로젝트 단위 분리 2개 -- 정상
- achievements: "응답속도 60% 개선", "일 50만 건 처리" 정량적 성과 추출 -- 정상
- soft_skills: "코드 리뷰 문화 정착 주도", "팀 협업 중심 개발" 등 -- 정상
- 인성/기술 분리: v1에서 일부 기술 항목 혼입 발견 -> 규칙 강화 완료


### JD <-> 이력서 매칭 (프롬프트 v1)


#### 배민 JD + 가상 이력서 (김서준)

- matching_skills: Java, Kotlin, JPA, AWS, Kafka, Redis 등 14개 -- 정상
- missing_skills: Linux/Unix, SNS, Elasticsearch, 도메인 모델링 -- 정상
- strength_areas: 대규모 주문 처리, 비동기 메시징, 장애 대응 등 5개 -- 정량적 근거 포함
- weakness_areas: 경력 연차 부족 (4년 vs 7년), Linux/Unix 미기재 등 4개 -- 정상
- experience_fit: "부족" (4년 vs 7년) -- 정상
- interview_topics: 기술 5개 + 인성 2개, sample_question 포함 -- 정상
- 상위/하위 기술 매칭: v1에서 Spring Boot-Spring Framework 미매칭 발견 -> 규칙 추가 완료


### 답변 평가 (프롬프트 v1)


#### 부족한 답변 테스트 (배민 Redis 캐싱 질문)

- 질문: "Redis 캐싱 도입으로 주문 조회 API 속도를 60% 개선했다고 했는데, 병목 원인을 어떻게 분석했고 어떤 캐시 전략을 적용했나요?"
- 답변: "네, Redis를 도입해서 캐싱을 했습니다. 속도가 많이 빨라졌습니다."
- score: 3점 -- 부족한 답변에 적절한 점수
- strengths: Redis 캐싱 도입 경험 언급, 성능 개선 결과 전달 -- 부족한 답변에서도 강점 추출
- weaknesses: 병목 분석 방법 미설명, 캐시 전략 설명 없음 -- 구체적
- follow_up_needed: true (score < 7) -- 정상
- follow_up_focus: APM 분석, Cache Aside/Write Through, 캐시 만료 정책, 데이터 정합성 -- 구체적


### 면접 질문 생성 (프롬프트 v1)


#### 배민 JD + 김서준 이력서 + 깐깐한 기술 면접관

- 질문 7개 생성 (기술 5개 + 인성 2개) -- 정상
- priority 순서: 상 4개 -> 중 2개 -> 하 1개 -- 정상
- 이력서 내용 구체적 언급 ("ABC테크에서 Redis 캐싱을 도입하셨다고 했는데...") -- 정상
- good_answer_criteria: APM, At-least-once, Saga 패턴 등 구체적 키워드 포함 -- 정상
- intent: 각 질문의 검증 목적 명확 -- 정상


### 꼬리질문 생성 (프롬프트 v1)


#### Redis 캐싱 부족한 답변 (score 3) 기반 꼬리질문

- follow_up_question: "Redis를 적용하기 전에 API 응답 지연 원인이 DB 조회 때문이라고 판단하신 근거가..." -- 자연스러운 이어가기
- target_weakness: "성능 병목 원인 분석 과정과 측정 근거 부족" -- 정확
- expected_depth: APM, SQL 로그, 슬로우 쿼리, DB CPU 사용량 등 구체적 기준 포함 -- 정상
- follow_up_focus에서 핵심 1개만 선택하여 질문 -- 규칙대로 동작


### 면접관 페르소나 (3종)

| 페르소나 | 파일 변수명 | 특징 |
|---|---|---|
| 깐깐한 기술 팀장 | PERSONA_STRICT | 정량적 수치, 의사결정 근거를 끈질기게 추궁 |
| 공감형 인사 담당자 | PERSONA_FRIENDLY | 성장 과정, 협업 태도, 동기에 관심 |
| 실무형 시니어 개발자 | PERSONA_PRACTICAL | 실제 구현, 디버깅, 트러블슈팅 경험 확인 |

사용법: 다른 프롬프트의 System Prompt 앞에 페르소나를 붙여서 사용

```python
system_prompt = PERSONA_STRICT + QUESTION_GENERATOR_SYSTEM_PROMPT
```


---


## 파일 구조

```
agent/parsers/
  README.md                       -- 이 파일
  jd_parser_prompt.py             -- JD 파싱 프롬프트 v2
  jd_parser.py                    -- JD 파서 메인 코드 (OpenAI 전용)
  jd_parser_free.py               -- JD 파서 무료 테스트 버전 (Gemini + 에러 핸들링)
  resume_parser_prompt.py         -- 이력서 파싱 프롬프트 v1
  jd_resume_matcher_prompt.py     -- JD <-> 이력서 매칭 프롬프트 v1
  answer_evaluator_prompt.py      -- 답변 평가 프롬프트 v1
  question_generator_prompt.py    -- 면접 질문 생성 프롬프트 v1
  follow_up_prompt.py             -- 꼬리질문 생성 프롬프트 v1
  persona_prompts.py              -- 면접관 페르소나 3종
```


---


## 전체 프롬프트 완성 현황

- [x] JD 파싱 프롬프트 v2
- [x] 이력서 파싱 프롬프트 v1
- [x] JD <-> 이력서 매칭 프롬프트 v1
- [x] 답변 평가 프롬프트 v1
- [x] 면접 질문 생성 프롬프트 v1
- [x] 꼬리질문 생성 프롬프트 v1
- [x] 면접관 페르소나 3종


## 다음 단계

- 노드 구조를 설계해서 공유받으면, 각 프롬프트를 해당 구조에 맞춰 조정
- 최종 리포트 생성 프롬프트 개발 (report_generator_prompt.py)
- 전체 End-to-End 테스트 (JD 입력 -> 면접 질문 -> 답변 -> 평가 -> 꼬리질문 -> 리포트)
