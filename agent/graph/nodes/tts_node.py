"""
tts_node (TTS: Text-to-Speech) — 인터페이스 스텁

면접관 질문 텍스트를 음성으로 합성하는 노드 자리. 실제 TTS API 호출은
백엔드가 구현한다. 현재는 입출력 State 인터페이스만 정의한다.

입력 (State에서 기대):
    합성할 텍스트는 별도 필드 없이 messages의 마지막 AIMessage 내용
    (직전에 생성된 질문 또는 꼬리질문)을 사용한다.

출력 (State로 반환):
    audio_output (str): 합성된 오디오. base64 인코딩 문자열 또는 URL.

백엔드가 채울 부분:
    - 마지막 AIMessage 텍스트를 TTS API로 합성하는 실제 호출
    - 반환 dict에 {"audio_output": <결과>} 채우기

그래프 엣지에는 아직 연결하지 않는다 (백엔드 오디오 API 협의 후 연결).
다른 노드와 동일한 async 시그니처(state → dict)를 따른다.
"""

from agent.graph.state import InterviewState


async def tts_node(state: InterviewState):
    raise NotImplementedError(
        "tts_node: TTS 연동은 백엔드에서 구현 예정 "
        "(마지막 AIMessage → audio_output)"
    )
