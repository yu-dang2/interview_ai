from agent.parsers.jd_parser import parse_jd_from_text
from agent.graph.state import InterviewState


async def jd_parser(state: InterviewState):
    result = await parse_jd_from_text(state["jd_raw"])
    jd_parsed = result.data if hasattr(result, "data") else result
    return {"jd_parsed": jd_parsed}
