import requests
import streamlit as st

BASE_URL = "http://127.0.0.1:8000"


class SessionExpiredError(Exception):
    """토큰이 만료·무효(401)일 때 — 호출부에서 재로그인 유도용으로 구분해서 잡는다."""
    pass


def _headers() -> dict:
    token = st.session_state.get("access_token", "")
    return {"Authorization": f"Bearer {token}"} if token else {}


def _check(res: requests.Response) -> requests.Response:
    if res.status_code == 401:
        raise SessionExpiredError()
    res.raise_for_status()
    return res


# ── 인증 ────────────────────────────────────────────────────────────────────

def login(email: str, password: str) -> dict:
    res = requests.post(
        f"{BASE_URL}/auth/login",
        json={"email": email, "password": password},
        timeout=30,
    )
    res.raise_for_status()
    return res.json()


def register(name: str, email: str, password: str) -> dict:
    res = requests.post(
        f"{BASE_URL}/auth/register",
        json={"name": name, "email": email, "password": password},
        timeout=30,
    )
    res.raise_for_status()
    return res.json()


# ── 파일 업로드 ─────────────────────────────────────────────────────────────

def upload_resume(file_bytes: bytes, filename: str) -> int:
    res = requests.post(
        f"{BASE_URL}/resume/upload",
        files={"file": (filename, file_bytes)},
        headers=_headers(),
        timeout=30,
    )
    _check(res)
    return res.json()["resume_id"]


def upload_jd(file_bytes: bytes, filename: str) -> int:
    res = requests.post(
        f"{BASE_URL}/jd/upload",
        files={"file": (filename, file_bytes)},
        headers=_headers(),
        timeout=30,
    )
    _check(res)
    return res.json()["jd_id"]


# ── 면접 ────────────────────────────────────────────────────────────────────

def start_interview(resume_id: int, jd_id: int, persona: str) -> dict:
    res = requests.post(
        f"{BASE_URL}/interview/sessions",
        json={"resume_id": resume_id, "jd_id": jd_id, "persona": persona},
        headers=_headers(),
        timeout=180,
    )
    _check(res)
    return res.json()


def send_answer(session_id: str, answer: str, input_type: str | None = None) -> dict:
    payload = {"answer": answer}
    if input_type == "voice":
        payload["input_type"] = "voice"
    res = requests.post(
        f"{BASE_URL}/interview/sessions/{session_id}/chat",
        json=payload,
        headers=_headers(),
        timeout=180,
    )
    _check(res)
    return res.json()


def end_session(session_id: str) -> None:
    res = requests.post(
        f"{BASE_URL}/interview/sessions/{session_id}/end",
        headers=_headers(),
        timeout=30,
    )
    _check(res)


def get_result(session_id: str) -> dict:
    res = requests.get(
        f"{BASE_URL}/interview/sessions/{session_id}/result",
        headers=_headers(),
        timeout=90,
    )
    _check(res)
    return res.json()


# ── 피드백 ──────────────────────────────────────────────────────────────────

def get_feedback(session_id: str) -> dict:
    res = requests.get(
        f"{BASE_URL}/interview/sessions/{session_id}/feedback",
        headers=_headers(),
        timeout=30,
    )
    _check(res)
    return res.json()


# ── 영상 분석 ───────────────────────────────────────────────────────────────

def get_video_metrics(session_id: str) -> dict:
    res = requests.get(
        f"{BASE_URL}/interview/{session_id}/video-metrics",
        headers=_headers(),
        timeout=30,
    )
    _check(res)
    return res.json()


def get_my_videos() -> dict:
    res = requests.get(
        f"{BASE_URL}/mypage/videos",
        headers=_headers(),
        timeout=30,
    )
    _check(res)
    return res.json()


def get_my_sessions(limit: int = 20) -> dict:
    res = requests.get(
        f"{BASE_URL}/interview/sessions",
        params={"limit": limit},
        headers=_headers(),
        timeout=30,
    )
    _check(res)
    return res.json()
