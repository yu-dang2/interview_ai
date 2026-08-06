import requests
import streamlit as st

BASE_URL = "http://127.0.0.1:8000"


def _headers() -> dict:
    token = st.session_state.get("access_token", "")
    return {"Authorization": f"Bearer {token}"} if token else {}


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
    res.raise_for_status()
    return res.json()["resume_id"]


def upload_jd(file_bytes: bytes, filename: str) -> int:
    res = requests.post(
        f"{BASE_URL}/jd/upload",
        files={"file": (filename, file_bytes)},
        headers=_headers(),
        timeout=30,
    )
    res.raise_for_status()
    return res.json()["jd_id"]


# ── 면접 ────────────────────────────────────────────────────────────────────

def start_interview(resume_id: int, jd_id: int, persona: str) -> dict:
    res = requests.post(
        f"{BASE_URL}/interview/sessions",
        json={"resume_id": resume_id, "jd_id": jd_id, "persona": persona},
        headers=_headers(),
        timeout=180,  # JD·이력서 파싱 + 첫 질문 생성까지 LLM 호출이 이어져 오래 걸림
    )
    res.raise_for_status()
    return res.json()


def send_answer(session_id: str, answer: str, input_type: str | None = None) -> dict:
    payload = {"answer": answer}
    if input_type == "voice":
        payload["input_type"] = "voice"
    res = requests.post(
        f"{BASE_URL}/interview/sessions/{session_id}/chat",
        json=payload,
        headers=_headers(),
        timeout=90,  # 답변 평가 + 다음 질문 생성 LLM 호출
    )
    res.raise_for_status()
    return res.json()


def end_session(session_id: str) -> None:
    requests.post(
        f"{BASE_URL}/interview/sessions/{session_id}/end",
        headers=_headers(),
        timeout=30,
    ).raise_for_status()


def get_result(session_id: str) -> dict:
    res = requests.get(
        f"{BASE_URL}/interview/sessions/{session_id}/result",
        headers=_headers(),
        timeout=90,  # 결과 종합 분석 LLM 호출
    )
    res.raise_for_status()
    return res.json()


# ── 피드백 ──────────────────────────────────────────────────────────────────

def get_feedback(session_id: str) -> dict:
    res = requests.get(
        f"{BASE_URL}/interview/sessions/{session_id}/feedback",
        headers=_headers(),
        timeout=30,
    )
    res.raise_for_status()
    return res.json()
