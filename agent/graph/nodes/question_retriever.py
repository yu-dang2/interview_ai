import logging

from agent.graph.state import InterviewState
from agent.retrieval import store

logger = logging.getLogger(__name__)


async def question_retriever(state: InterviewState):
    query = store.build_job_query(state.get("jd_parsed", {}))

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
