"""
LangGraph 그래프 소유 모듈

그래프는 여기서 딱 한 번 컴파일하고, 세션마다 thread_id 로 재사용한다.
(예전처럼 요청마다 서브그래프를 다시 조립하지 않는다.)

호출 흐름:
    start(session_id, init_state)      → 첫 질문까지 실행하고 answer_evaluator 앞에서 멈춤
    resume(session_id, answer, input_type) → 답변을 넣고 재개, 다음 질문/꼬리질문/리포트까지
    snapshot(session_id)               → (state values, 종료 여부)

주의(async): agent 그래프의 노드/LLM 호출(call_llm)이 전부 async 이므로 여기서도
ainvoke/aget_state/aupdate_state 를 쓴다. 동기 invoke 로는 구동되지 않는다.

주의(output 스키마): build_graph 는 output=InterviewOutput(messages 만) 으로 컴파일된다.
따라서 ainvoke 의 반환값에는 eval_score·eval_result·report_result·match_result 가 없다.
서비스가 그 값들을 읽어야 하므로, start/resume 은 ainvoke 반환값이 아니라
항상 aget_state().values(온전한 State)를 반환한다.
"""

from langchain_core.messages import HumanMessage
from langgraph.checkpoint.memory import InMemorySaver

from agent.graph.interview_agent import build_graph
from backend.core.config import require_openai_key

# 키가 없으면 첫 요청이 아니라 서버 기동 시점에 실패시킨다.
require_openai_key()

# InMemorySaver 는 프로세스 재시작 시 진행 중인 면접이 사라지고 멀티 워커에서 공유되지 않는다.
# 영속성이 필요해지면 langgraph-checkpoint-sqlite 를 추가하고 SqliteSaver 로 교체할 것.
# 그때까지는 uvicorn 을 --workers 1 로 띄운다.
_checkpointer = InMemorySaver()

# interrupt_before=["answer_evaluator"] → 첫 질문/꼬리질문 생성 후 사용자 답변을 기다리는 지점.
# 이 모드에서만 build_graph 가 question_generator → answer_evaluator 엣지를 잇는다.
graph = build_graph(checkpointer=_checkpointer, interrupt_before=["answer_evaluator"])

# 조립이 어긋나면 첫 요청이 아니라 여기서 터지게 한다.
_required_nodes = {
    "persona_selector", "jd_parser", "resume_parser", "jd_resume_matcher",
    "question_generator", "answer_evaluator", "follow_up_generator", "report_generator",
}
_missing = _required_nodes - set(graph.nodes)
if _missing:
    raise RuntimeError(f"그래프에 노드가 누락되었습니다: {sorted(_missing)}")


def config_for(session_id: str) -> dict:
    return {"configurable": {"thread_id": session_id}}


async def start(session_id: str, init_state: dict) -> dict:
    """면접을 시작하고 첫 질문 직후(answer_evaluator 직전)까지 실행한다."""
    config = config_for(session_id)
    await graph.ainvoke(init_state, config)
    # output 스키마로 필터링되지 않은 온전한 State 를 돌려준다.
    return (await graph.aget_state(config)).values


async def resume(session_id: str, answer: str, input_type: str = "text") -> dict:
    """사용자 답변을 넣고 그래프를 재개한다."""
    config = config_for(session_id)
    # input_type 은 리듀서 없는 LastValue 채널이라 한 번 "voice" 를 쓰면 계속 남는다.
    # 음성일 때만 조건부로 쓰지 말고 매 턴 덮어쓸 것.
    await graph.aupdate_state(
        config,
        {"messages": [HumanMessage(content=answer)], "input_type": input_type},
    )
    await graph.ainvoke(None, config)
    return (await graph.aget_state(config)).values


async def snapshot(session_id: str) -> tuple[dict, bool]:
    """(state values, 종료 여부)를 반환한다. next 가 비어 있으면 그래프가 끝난 것."""
    state = await graph.aget_state(config_for(session_id))
    return state.values, state.next == ()


async def exists(session_id: str) -> bool:
    """해당 thread_id 에 체크포인트가 있는지."""
    state = await graph.aget_state(config_for(session_id))
    return bool(state.created_at)
