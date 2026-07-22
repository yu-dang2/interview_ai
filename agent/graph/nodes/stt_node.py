"""
stt_node (STT: Speech-to-Text) — 인터페이스 스텁

음성 답변을 텍스트로 전사하는 노드 자리. 실제 GPT-4o-transcribe API 호출은
백엔드가 구현한다. 현재는 입출력 State 인터페이스만 정의한다.

입력 (State에서 기대):
    audio_input (str): 전사할 오디오. base64 인코딩 문자열 또는 URL/경로.
                       (인코딩 방식은 백엔드/프론트 합의)

출력 (State로 반환):
    transcribed_text (str): 전사된 텍스트.
    (전사 결과를 messages에 HumanMessage로 넣을지 여부는 그래프 연결 시점에
     answer_evaluator 입력 규약과 함께 결정한다.)

백엔드가 채울 부분:
    - audio_input을 GPT-4o-transcribe로 전사하는 실제 호출
    - 반환 dict에 {"transcribed_text": <결과>} 채우기

그래프 엣지에는 아직 연결하지 않는다 (백엔드 오디오 API 협의 후 연결).
다른 노드와 동일한 async 시그니처(state → dict)를 따른다.
"""

from agent.graph.state import InterviewState


async def stt_node(state: InterviewState):
    raise NotImplementedError(
        "stt_node: STT(GPT-4o-transcribe) 연동은 백엔드에서 구현 예정 "
        "(audio_input → transcribed_text)"
    )
