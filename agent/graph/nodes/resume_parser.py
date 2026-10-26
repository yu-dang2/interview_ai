from agent.parsers.resume_parser_prompt import RESUME_PARSER_SYSTEM_PROMPT
from agent.graph.state import InterviewState
from agent.graph.utils import call_llm
from agent.graph.experience import recompute_experience_years


async def resume_parser(state: InterviewState):
    resume_parsed = await call_llm(
        RESUME_PARSER_SYSTEM_PROMPT, state["resume_raw"], stage="resume_parser"
    )
    return {"resume_parsed": recompute_experience_years(resume_parsed)}
