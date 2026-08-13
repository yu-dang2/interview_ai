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
    sync_interviewer_style()
    sync_session_id()


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
            "<script>sessionStorage.removeItem('iv_access_token');</script>",
            height=0,
        )
        return

    token = st.session_state.get("access_token", "")

    if token:
        components.html(
            f"<script>sessionStorage.setItem('iv_access_token', {json.dumps(token)});</script>",
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
        var saved = sessionStorage.getItem('iv_access_token');
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


# ── 페르소나 선택 유지 (새로고침 대응) ────────────────────────────────────

def sync_interviewer_style():
    st.markdown(
        "<style>.st-key-_persona_restore { position:absolute; width:0; height:0; "
        "overflow:hidden; clip:rect(0,0,0,0); margin:0; padding:0; }</style>",
        unsafe_allow_html=True,
    )
    restored = st.text_input(
        "_persona_restore", key="_persona_restore", label_visibility="collapsed"
    )

    style = st.session_state.get("interviewer_style", "")

    if style:
        components.html(
            f"<script>localStorage.setItem('iv_interviewer_style', {json.dumps(style)});</script>",
            height=0,
        )
        return

    if restored == "__NONE__":
        return

    if restored:
        st.session_state["interviewer_style"] = restored
        st.rerun()
        return

    components.html("""
    <script>
    (function() {
      var doc = window.parent.document;
      var tries = 0;
      function attempt() {
        var input = doc.querySelector('.st-key-_persona_restore input');
        if (!input) {
          tries++;
          if (tries < 20) setTimeout(attempt, 50);
          return;
        }
        var saved = localStorage.getItem('iv_interviewer_style');
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


# ── 면접 세션 ID 유지 (하드 리다이렉트 대응) ────────────────────────────

def sync_session_id():
    if st.session_state.get("_session_id_clear_pending", False):
        st.session_state["_session_id_restore"] = "__NONE__"

    st.markdown(
        "<style>.st-key-_session_id_restore { position:absolute; width:0; height:0; "
        "overflow:hidden; clip:rect(0,0,0,0); margin:0; padding:0; }</style>",
        unsafe_allow_html=True,
    )
    restored = st.text_input(
        "_session_id_restore", key="_session_id_restore", label_visibility="collapsed"
    )

    if st.session_state.pop("_session_id_clear_pending", False):
        components.html(
            "<script>localStorage.removeItem('iv_session_id');</script>",
            height=0,
        )
        return

    session_id = st.session_state.get("session_id")

    if session_id:
        components.html(
            f"<script>localStorage.setItem('iv_session_id', {json.dumps(session_id)});</script>",
            height=0,
        )
        return

    if restored == "__NONE__":
        return

    if restored:
        st.session_state["session_id"] = restored
        st.rerun()
        return

    components.html("""
    <script>
    (function() {
      var doc = window.parent.document;
      var tries = 0;
      function attempt() {
        var input = doc.querySelector('.st-key-_session_id_restore input');
        if (!input) {
          tries++;
          if (tries < 20) setTimeout(attempt, 50);
          return;
        }
        var saved = localStorage.getItem('iv_session_id');
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
            "<script>sessionStorage.removeItem('iv_access_token');</script>",
            height=0,
        )
        return ""

    token = st.session_state.get("access_token", "")

    if token:
        components.html(
            f"<script>sessionStorage.setItem('iv_access_token', {json.dumps(token)});</script>",
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
        var saved = sessionStorage.getItem('iv_access_token');
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


# ── 세션 만료 처리 ────────────────────────────────────────────────────

def mark_session_expired():
    st.session_state["_logout_pending"] = True
    st.session_state["access_token"] = ""
    st.session_state["is_logged_in"] = False
    st.session_state["_session_expired"] = True


def is_session_expired() -> bool:
    return bool(st.session_state.get("_session_expired"))


def render_session_expired_inline():
    st.session_state["_session_expired"] = False
    st.error("로그인이 만료되었습니다. 다시 로그인해주세요.")
    if st.button("로그인 화면으로 이동", key="_session_expired_relogin", use_container_width=True):
        st.switch_page("pages/01_로그인.py")


def render_session_expired_banner():
    if not is_session_expired():
        return
    _, mid, _ = st.columns([1, 2, 1])
    with mid:
        render_session_expired_inline()
