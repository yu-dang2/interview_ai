"""
직무 지식 카드 효과 측정 (A/B)

카드를 새로 채우거나 고친 뒤, 그 카드가 질문 품질을 실제로 바꾸는지 확인하는 도구다.
같은 JD·이력서로 question_generator 를 두 번 돌리되 참고자료 유무만 다르게 한다.

    A) 참고자료 없음 — 카드 도입 전과 동일
    B) 참고자료 있음 — 검색된 카드를 프롬프트에 주입

파싱·매칭은 딱 한 번만 돌려 두 쪽에 같은 입력을 넣는다. 그래야 차이가 카드 때문인지
LLM 의 실행 편차 때문인지 헷갈리지 않는다.

실행:
    # 1) 검색만 확인 (LLM 호출 없음, 빠르고 무료) — 카드 채운 직후 첫 확인용
    .venv/Scripts/python.exe scripts/compare_question_quality.py --search-only

    # 2) 질문 품질 A/B (LLM 호출 있음)
    .venv/Scripts/python.exe scripts/compare_question_quality.py --scenario sales

    # 3) 직접 만든 JD·이력서로
    .venv/Scripts/python.exe scripts/compare_question_quality.py --jd my_jd.txt --resume my_resume.txt

    # 4) 다른 인덱스로 (구/신 코퍼스 비교)
    .venv/Scripts/python.exe scripts/compare_question_quality.py --scenario sales --index ./data/knowledge_index_v2

무엇을 보아야 하나:
    1. B 의 질문이 이력서의 구체적 경험을 여전히 언급하는가
       → 카드를 그대로 질문화해 "캐싱 경험 있으신가요?" 같은 뻔한 질문으로 퇴행하면 실패다.
    2. B 에만 있는 관점이 있는가
       → A 와 주제가 똑같으면 그 카드는 LLM 이 이미 아는 내용만 담고 있다는 뜻이다.
         추상적 역량 서술 대신 실제 기출 원문·꼬리질문 순서·감점 사유를 넣어야 한다.
    3. 질문 개수가 크게 줄지 않았는가
       → 참고자료가 길면 질문 수가 줄어드는 경향이 있다. 주제 커버리지 손실을 확인한다.

주의: 개발 직무는 모델이 이미 잘 알아 카드 효과가 약하게 나온다. 카드의 문제가 아니라
직무 특성이므로, 효과 확인은 비개발 직무로 하는 편이 판단하기 쉽다.
"""

import argparse
import asyncio
import json
import os
import sys

from dotenv import load_dotenv

# 프로젝트 루트에서 실행하지 않아도 agent 패키지를 찾을 수 있게 한다.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

load_dotenv()


# 바로 돌려볼 수 있는 예시 시나리오. --jd/--resume 로 직접 넣어도 된다.
SCENARIOS = {
    "backend": {
        "persona": "기술 리드",
        "jd": """[채용] 백엔드 개발자 (3년 이상)
- Python/Django 기반 API 서버 개발 및 운영
- 일 500만 요청 규모 트래픽 처리, 성능 최적화
- MySQL 쿼리 튜닝, Redis 캐시 설계
- AWS 환경 운영, 장애 대응
우대: MSA 경험, Kafka, 모니터링 체계 구축 경험""",
        "resume": """김서준 / 백엔드 개발자 3년
[ABC테크 2022-2025] 커머스 백엔드 개발
- Django REST Framework로 주문 API 개발, 일 200만 요청 처리
- 주문 조회 지연 개선: Redis 캐싱 도입해 응답속도 800ms → 120ms
- MySQL 슬로우 쿼리 인덱스 재설계로 CPU 40% 절감
- AWS EC2/RDS 운영, CloudWatch 알람 구성
[프로젝트] 사내 배치 시스템을 Celery로 전환해 처리시간 3시간 → 40분
기술: Python, Django, MySQL, Redis, AWS, Docker""",
    },
    "sales": {
        "persona": "인사 담당자",
        "jd": """[채용] B2B 기업영업 담당자
- 신규 고객사 발굴 및 기존 고객 관리
- 제안서 작성 및 계약 협상
- 매출 목표 달성
- 경력 3년 이상, 원활한 커뮤니케이션 능력""",
        "resume": """박지현 / B2B 영업 4년
[대한솔루션 2021-2025] 제조업 대상 SaaS 영업
- 신규 고객사 23곳 발굴, 연 매출 12억 달성 (목표 대비 118%)
- 이탈 위기 고객사 5곳 재계약 성사
- 제안서 템플릿 표준화로 제안 리드타임 2주 → 5일 단축
- 파트너사 3곳과 공동 영업 채널 구축
기술: Salesforce, 제안서 작성, 계약 협상""",
    },
    "marketing": {
        "persona": "인사 담당자",
        "jd": """[채용] 퍼포먼스 마케터
- 디지털 광고 채널 운영 및 최적화
- 캠페인 기획과 성과 분석
- 예산 집행 및 ROI 관리
- 경력 3년 이상""",
        "resume": """이수민 / 퍼포먼스 마케터 3년
[그로스랩 2022-2025] 커머스 브랜드 퍼포먼스 마케팅
- 월 광고비 8천만원 집행, ROAS 320% → 410% 개선
- 랜딩페이지 A/B 테스트로 전환율 2.1% → 3.4%
- GA4 이벤트 설계 및 퍼널 대시보드 구축
- 리타게팅 세그먼트 재설계로 CAC 22% 절감
기술: GA4, Meta Ads, Google Ads, SQL""",
    },
}


def read_scenario(args) -> dict:
    """--jd/--resume 가 있으면 파일에서, 없으면 내장 시나리오에서 읽는다."""
    if args.jd or args.resume:
        if not (args.jd and args.resume):
            raise SystemExit("--jd 와 --resume 는 함께 지정해야 합니다.")
        for path in (args.jd, args.resume):
            if not os.path.isfile(path):
                raise SystemExit(f"파일을 찾을 수 없습니다: {path}")
        return {
            "persona": args.persona,
            "jd": open(args.jd, encoding="utf-8").read(),
            "resume": open(args.resume, encoding="utf-8").read(),
        }

    scenario = SCENARIOS.get(args.scenario)
    if scenario is None:
        raise SystemExit(
            f"알 수 없는 시나리오: {args.scenario} (가능: {', '.join(SCENARIOS)})"
        )
    return {**scenario, "persona": args.persona or scenario["persona"]}


def show(title, result):
    questions = result.get("question_list", [])
    print("\n" + "=" * 78)
    print(f"  {title}  (질문 {len(questions)}개)")
    print("=" * 78)
    for i, q in enumerate(questions, 1):
        print(f"\n{i}. [{q.get('topic','?')} / {q.get('priority','?')}] {q.get('question','')}")
        print(f"   의도: {q.get('intent','')}")


async def run(args):
    # store 가 호출 시점에 환경변수를 읽으므로 import 전후 어디서 넣어도 되지만,
    # 실수를 줄이려 노드 import 전에 설정한다.
    if args.index:
        os.environ["KNOWLEDGE_INDEX_PATH"] = args.index

    from agent.retrieval import store
    from agent.graph.nodes.jd_parser import jd_parser
    from agent.graph.nodes.resume_parser import resume_parser
    from agent.graph.nodes.jd_resume_matcher import jd_resume_matcher
    from agent.graph.nodes.question_retriever import question_retriever
    from agent.graph.nodes.question_generator import question_generator

    print(f"인덱스: {store.index_path()}")
    print(f"임베딩 모델: {store.embedding_model()} | 거리 상한: {store.max_distance()}")

    if store.get_collection() is None:
        raise SystemExit(
            "인덱스를 열 수 없습니다. scripts/build_knowledge_index.py 로 먼저 색인하세요."
        )

    scenario = read_scenario(args)

    # ── 검색만 확인 (LLM 호출 없음) ──
    if args.search_only:
        print("\n[검색만 확인 — 질문 생성은 건너뜁니다]")
        for name, s in (SCENARIOS.items() if not (args.jd or args.resume)
                        else [(args.scenario or "custom", scenario)]):
            # 검색 쿼리는 jd_parsed 가 필요하지만, 검색만 볼 때는 LLM 파싱 없이
            # JD 첫 줄을 직무명으로 대충 넣어 감을 본다. 정확한 확인은 A/B 로 할 것.
            head = s["jd"].strip().splitlines()[0].replace("[채용]", "").strip()
            cards = await store.search([head])
            print(f"  {name:<10} '{head}'")
            print(f"    → {[(c['job_family'], round(c['_distance'], 3)) for c in cards] or '관련 카드 없음'}")
        return

    # ── 파싱·매칭 1회 (A/B 공통 입력 고정) ──
    print("\n파싱·매칭 실행 중 (A/B 공통 입력을 고정하기 위해 한 번만)...")
    state = {"jd_raw": scenario["jd"], "resume_raw": scenario["resume"],
             "persona": scenario["persona"]}
    state.update(await jd_parser(state))
    state.update(await resume_parser(state))
    state.update(await jd_resume_matcher(state))
    print(f"  job_title   : {state['jd_parsed'].get('job_title')}")
    print(f"  match_score : {state.get('match_score')}")

    retrieved = (await question_retriever(state))["retrieved_knowledge"]
    if not retrieved:
        print("  검색된 카드 : 없음 — 이 JD 에 맞는 카드가 코퍼스에 없습니다.")
        print("  (A/B 차이가 나올 수 없으니 카드를 추가하거나 다른 시나리오로 확인하세요)")
        return
    print(f"  검색된 카드 : {[(c['job_family'], round(c['_distance'], 3)) for c in retrieved]}")

    base = {**state, "question_list": [], "current_question_index": 0}
    a = await question_generator({**base, "retrieved_knowledge": []})
    b = await question_generator({**base, "retrieved_knowledge": retrieved})

    show("A) 참고자료 없음 — 카드 도입 전", a)
    show("B) 참고자료 있음 — 카드 적용", b)

    print("\n" + "=" * 78)
    print("  확인할 것")
    print("  1. B 가 이력서의 구체적 경험을 여전히 언급하는가 (뻔한 질문으로 퇴행하지 않았는가)")
    print("  2. B 에만 있는 관점이 있는가 (없으면 그 카드는 LLM 이 아는 내용만 담고 있다)")
    print("  3. 질문 개수가 크게 줄지 않았는가")
    print("=" * 78)

    if args.save:
        with open(args.save, "w", encoding="utf-8") as f:
            json.dump({"scenario": scenario, "retrieved": retrieved,
                       "without_reference": a.get("question_list", []),
                       "with_reference": b.get("question_list", [])},
                      f, ensure_ascii=False, indent=2)
        print(f"\n결과 저장: {args.save}")


def main():
    parser = argparse.ArgumentParser(
        description="직무 지식 카드가 질문 품질을 바꾸는지 A/B 로 측정한다",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--scenario", default="sales",
                        help=f"내장 시나리오 ({', '.join(SCENARIOS)}). 기본 sales")
    parser.add_argument("--jd", help="JD 텍스트 파일 경로 (--resume 와 함께)")
    parser.add_argument("--resume", help="이력서 텍스트 파일 경로 (--jd 와 함께)")
    parser.add_argument("--persona", help="면접관 페르소나 (기본: 시나리오별 기본값)")
    parser.add_argument("--index", help="인덱스 경로 (기본: KNOWLEDGE_INDEX_PATH)")
    parser.add_argument("--search-only", action="store_true",
                        help="검색 결과만 확인하고 질문 생성은 건너뛴다 (LLM 호출 없음)")
    parser.add_argument("--save", help="결과를 JSON 으로 저장할 경로")
    args = parser.parse_args()

    if not os.getenv("OPENAI_API_KEY"):
        raise SystemExit(
            "OPENAI_API_KEY가 설정되어 있지 않습니다. .env 파일을 확인해주세요."
        )

    asyncio.run(run(args))


if __name__ == "__main__":
    main()
