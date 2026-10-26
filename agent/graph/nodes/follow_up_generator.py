import json
from langchain_core.messages import HumanMessage, AIMessage
from agent.parsers.follow_up_prompt import FOLLOW_UP_GENERATOR_SYSTEM_PROMPT
from agent.graph.state import InterviewState
from agent.graph.nodes.persona_selector import PERSONA_MAP
from agent.parsers.persona_prompts import PERSONA_TECH_LEAD
from agent.graph.utils import call_llm


async def follow_up_generator(state: InterviewState):
    count = state.get("follow_up_count", 0)
    eval_result = state.get("eval_result", {})

    persona_prompt = PERSONA_MAP.get(state.get("persona"), PERSONA_TECH_LEAD)
    system_prompt = persona_prompt + FOLLOW_UP_GENERATOR_SYSTEM_PROMPT

    recent_context = []
    for msg in state.get("messages", [])[-4:]:
        if isinstance(msg, HumanMessage):
            recent_context.append({"role": "user", "content": msg.content})
        elif isinstance(msg, AIMessage):
            recent_context.append({"role": "assistant", "content": msg.content})

    user_content = json.dumps({
        "recent_conversation": recent_context,
        "follow_up_focus": eval_result.get("follow_up_focus", "")
    }, ensure_ascii=False)

    result = await call_llm(system_prompt, user_content, stage="follow_up_generator")
    return {
        "messages": [AIMessage(content=result.get("follow_up_question", ""))],
        "follow_up_count": count + 1
    }
