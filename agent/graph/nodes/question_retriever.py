"""
question_retriever 노드
작성: 이현주

직무 지식 카드를 검색해 question_generator 의 보조 참고자료로 넘긴다.
채용공고(JD)가 질문의 주재료이고, 이 카드는 "그 직무를 더 전문적으로 파고들 관점"만 보탠다.

검색 쿼리는 match_result 가 아니라 jd_parsed 를 쓴다. 카드가 직무 단위 문서라
쿼리도 같은 입도여야 하기 때문이다(A/B 실측: 세부 토픽 3/6 → 직무 단위 6/6.
근거는 agent/retrieval/store.py 모듈 docstring 참고).

부수 효과로 jd_parser 직후에 놓을 수 있게 되어 jd_resume_matcher 와 같은 super-step 에서
병렬로 돈다. 면접 시작 시간에 사실상 비용을 더하지 않는다.

실패 격리: 검색이 죽어도 면접은 굴러가야 하므로 빈 리스트로 폴백한다.
(resume_optimizer 와 같은 패턴)
"""

import logging

from agent.graph.state import InterviewState
from agent.retrieval import store

logger = logging.getLogger(__name__)


async def question_retriever(state: InterviewState):
    query = store.build_job_query(state.get("jd_parsed", {}))

    # JD 파싱이 실패했거나 직무명·필수역량이 모두 비면 검색할 것이 없다.
    if not query:
        logger.info("검색 쿼리를 만들 수 없습니다(jd_parsed 비어 있음) — 참고자료 없이 진행")
        return {"retrieved_knowledge": []}

    try:
        cards = await store.search([query])
    except Exception as e:
        logger.warning(
            "직무 지식 검색 실패 — 빈 결과로 폴백: %s: %s", type(e).__name__, e
        )
        return {"retrieved_knowledge": []}

    logger.info(
        "직무 지식 카드 %d개 검색됨: %s",
        len(cards), [c.get("job_family") for c in cards],
    )
    return {"retrieved_knowledge": cards}
