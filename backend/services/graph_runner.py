"""
LangGraph 그래프 소유 모듈

그래프는 서버 기동 시 딱 한 번 컴파일하고, 세션마다 thread_id 로 재사용한다.
(예전처럼 요청마다 서브그래프를 다시 조립하지 않는다.)

호출 흐름:
    init()                             → 체크포인터 연결 + 그래프 컴파일 (lifespan 에서 호출)
    start(session_id, init_state)      → 첫 질문까지 실행하고 answer_evaluator 앞에서 멈춤
    resume(session_id, answer, input_type) → 답변을 넣고 재개, 다음 질문/꼬리질문/리포트까지
    snapshot(session_id)               → (state values, 종료 여부)
    close()                            → 체크포인터 연결 종료 (lifespan 에서 호출)

주의(async): agent 그래프의 노드/LLM 호출(call_llm)이 전부 async 이므로 여기서도
ainvoke/aget_state/aupdate_state 를 쓴다. 동기 invoke 로는 구동되지 않는다.

주의(output 스키마): build_graph 는 output=InterviewOutput(messages 만) 으로 컴파일된다.
따라서 ainvoke 의 반환값에는 eval_score·eval_result·report_result·match_result 가 없다.
서비스가 그 값들을 읽어야 하므로, start/resume 은 ainvoke 반환값이 아니라
항상 aget_state().values(온전한 State)를 반환한다.

주의(초기화 시점): AsyncSqliteSaver 는 async 컨텍스트 매니저라 모듈 import 시점에 만들 수
없다. 그래서 그래프를 전역에서 바로 컴파일하지 않고 init() 에서 만든다.
FastAPI lifespan 이 init()/close() 를 호출한다(backend/main.py).
"""

from langchain_core.messages import HumanMessage
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from agent.graph.interview_agent import build_graph
from backend.core.config import CHECKPOINT_DB_PATH, require_openai_key

# 키가 없으면 첫 요청이 아니라 서버 기동 시점에 실패시킨다.
require_openai_key()

# 조립이 어긋나면 첫 요청이 아니라 기동 시점에 터지게 한다.
_REQUIRED_NODES = {
    "persona_selector", "jd_parser", "resume_parser", "jd_resume_matcher",
    "question_generator", "answer_evaluator", "follow_up_generator", "report_generator",
}

_saver_cm = None   # AsyncSqliteSaver 컨텍스트 매니저 (close 에서 닫는다)
_graph = None


def _require_graph():
    """init() 전에 그래프를 쓰면 원인을 알기 어려운 AttributeError 대신 명확히 실패시킨다."""
    if _graph is None:
        raise RuntimeError(
            "그래프가 초기화되지 않았습니다. FastAPI lifespan 에서 graph_runner.init() 이 "
            "호출되는지 확인하세요."
        )
    return _graph


async def init() -> None:
    """체크포인터를 열고 그래프를 컴파일한다. 서버 기동 시 한 번만 호출한다."""
    global _saver_cm, _graph
    if _graph is not None:      # --reload 등으로 두 번 불려도 안전하게
        return

    _saver_cm = AsyncSqliteSaver.from_conn_string(CHECKPOINT_DB_PATH)
    checkpointer = await _saver_cm.__aenter__()
    await checkpointer.setup()  # 체크포인트 테이블 생성 (이미 있으면 통과)

    # interrupt_before=["answer_evaluator"] → 첫 질문/꼬리질문 생성 후 사용자 답변을 기다리는 지점.
    # 이 모드에서만 build_graph 가 question_generator → answer_evaluator 엣지를 잇는다.
    _graph = build_graph(checkpointer=checkpointer, interrupt_before=["answer_evaluator"])

    missing = _REQUIRED_NODES - set(_graph.nodes)
    if missing:
        raise RuntimeError(f"그래프에 노드가 누락되었습니다: {sorted(missing)}")


async def close() -> None:
    """체크포인터 연결을 닫는다. 서버 종료 시 호출한다."""
    global _saver_cm, _graph
    if _saver_cm is not None:
        await _saver_cm.__aexit__(None, None, None)
        _saver_cm = None
    _graph = None


def config_for(session_id: str) -> dict:
    return {"configurable": {"thread_id": session_id}}


async def start(session_id: str, init_state: dict) -> dict:
    """면접을 시작하고 첫 질문 직후(answer_evaluator 직전)까지 실행한다."""
    graph = _require_graph()
    config = config_for(session_id)
    await graph.ainvoke(init_state, config)
    # output 스키마로 필터링되지 않은 온전한 State 를 돌려준다.
    return (await graph.aget_state(config)).values


async def resume(session_id: str, answer: str, input_type: str = "text") -> dict:
    """사용자 답변을 넣고 그래프를 재개한다."""
    graph = _require_graph()
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
    graph = _require_graph()
    state = await graph.aget_state(config_for(session_id))
    return state.values, state.next == ()


async def exists(session_id: str) -> bool:
    """해당 thread_id 에 체크포인트가 있는지."""
    graph = _require_graph()
    state = await graph.aget_state(config_for(session_id))
    return bool(state.created_at)
