import streamlit as st


# ── 초기화 ────────────────────────────────────────────────────────────

def init_session():
    defaults = {
        "user_name":        "",
        "user_email":       "",
        "is_logged_in":     False,
        "access_token":     "",
        "user_id":          0,

        "interviewer_style": "",   # 기술 리드 / 인사 담당자 / 임원
        "jd_text":          "",
        "jd_id":            0,
        "resume_text":      "",
        "resume_id":        0,

        "session_id":       None,  # 백엔드 면접 세션 ID
        "first_question":   None,  # start_interview 응답의 첫 질문
        "interview_done":   False,
        "messages":         [],    # 면접 채팅 기록
        "scores":           {},    # {"논리력": 78, "표현력": 65, ...}
        "result":           None,  # get_result 응답 전체
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


# ── 편의 함수 ─────────────────────────────────────────────────────────

def get(key: str):
    return st.session_state.get(key)


def set(key: str, value):
    st.session_state[key] = value


def reset_interview():
    """면접 관련 세션만 초기화 (로그인 정보는 유지)"""
    set("interview_done", False)
    set("messages", [])
    set("scores", {})
