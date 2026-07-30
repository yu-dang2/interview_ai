import json

import streamlit as st
import streamlit.components.v1 as components


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
    sync_access_token()


# ── 로그인 유지 (새로고침 대응) ──────────────────────────────────────────

def sync_access_token():
   
    if st.session_state.get("_logout_pending", False):
        st.session_state["_token_restore"] = "__NONE__"

    st.markdown(
        "<style>.st-key-_token_restore { position:absolute; width:0; height:0; "
        "overflow:hidden; clip:rect(0,0,0,0); margin:0; padding:0; }</style>",
        unsafe_allow_html=True,
    )
    restored = st.text_input(
        "_token_restore", key="_token_restore", label_visibility="collapsed"
    )

    if st.session_state.pop("_logout_pending", False):
        components.html(
            "<script>localStorage.removeItem('iv_access_token');</script>",
            height=0,
        )
        return

    token = st.session_state.get("access_token", "")

    if token:
        components.html(
            f"<script>localStorage.setItem('iv_access_token', {json.dumps(token)});</script>",
            height=0,
        )
        return

    if restored == "__NONE__":
        return

    if restored:
        st.session_state["access_token"] = restored
        st.session_state["is_logged_in"] = True
        st.session_state["_token_sync_attempts"] = 0
        st.rerun()
        return

    attempts = st.session_state.get("_token_sync_attempts", 0)
    if attempts >= 5:
        return

    st.session_state["_token_sync_attempts"] = attempts + 1
    components.html("""
    <script>
    (function() {
      var doc = window.parent.document;
      var tries = 0;
      function attempt() {
        var input = doc.querySelector('.st-key-_token_restore input');
        if (!input) {
          tries++;
          if (tries < 20) setTimeout(attempt, 50);
          return;
        }
        var saved = localStorage.getItem('iv_access_token');
        var setter = Object.getOwnPropertyDescriptor(
          window.parent.HTMLInputElement.prototype, 'value'
        ).set;
        setter.call(input, saved || '__NONE__');
        input.dispatchEvent(new Event('input', { bubbles: true }));
        input.dispatchEvent(new FocusEvent('focusout', { bubbles: true }));
        input.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', code: 'Enter', bubbles: true }));
      }
      attempt();
    })();
    </script>
    """, height=0)
    st.stop()


# ── 로그인 유지 (비차단, 랜딩페이지 전용) ─────────────────────────────────

def restore_access_token_nonblocking() -> str:
    """인증 API를 직접 호출하지 않는 페이지용 가벼운 복원 (st.stop() 없이 동작)."""
    if st.session_state.get("_logout_pending", False):
        st.session_state["_landing_token_restore"] = "__NONE__"

    st.markdown(
        "<style>.st-key-_landing_token_restore { position:absolute; width:0; height:0; "
        "overflow:hidden; clip:rect(0,0,0,0); margin:0; padding:0; }</style>",
        unsafe_allow_html=True,
    )
    restored = st.text_input(
        "_landing_token_restore", key="_landing_token_restore", label_visibility="collapsed"
    )

    if st.session_state.pop("_logout_pending", False):
        components.html(
            "<script>localStorage.removeItem('iv_access_token');</script>",
            height=0,
        )
        return ""

    token = st.session_state.get("access_token", "")

    if token:
        components.html(
            f"<script>localStorage.setItem('iv_access_token', {json.dumps(token)});</script>",
            height=0,
        )
        return token

    if restored == "__NONE__":
        return ""

    if restored:
        st.session_state["access_token"] = restored
        st.session_state["is_logged_in"] = True
        st.rerun()
        return restored

    components.html("""
    <script>
    (function() {
      var doc = window.parent.document;
      var tries = 0;
      function attempt() {
        var input = doc.querySelector('.st-key-_landing_token_restore input');
        if (!input) {
          tries++;
          if (tries < 20) setTimeout(attempt, 50);
          return;
        }
        var saved = localStorage.getItem('iv_access_token');
        var setter = Object.getOwnPropertyDescriptor(
          window.parent.HTMLInputElement.prototype, 'value'
        ).set;
        setter.call(input, saved || '__NONE__');
        input.dispatchEvent(new Event('input', { bubbles: true }));
        input.dispatchEvent(new FocusEvent('focusout', { bubbles: true }));
        input.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', code: 'Enter', bubbles: true }));
      }
      attempt();
    })();
    </script>
    """, height=0)
    return ""


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
