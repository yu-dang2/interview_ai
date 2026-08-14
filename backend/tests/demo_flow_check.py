# -*- coding: utf-8 -*-
"""
데모 경로 백엔드 확인 스크립트

심사 시연에서 보여줄 흐름을 API 로 끝까지 돌려본다.

    로그인 → 이력서·JD 등록 → 면접 진행 → 결과 리포트 → 피드백 → 기록 목록

화면(Streamlit) 확인을 대체하지는 않는다. 백엔드가 끊기지 않는지만 본다.
화면은 backend/tests/README.md 의 시나리오로 따로 확인할 것.

⚠️ 실제 LLM 을 호출한다. 면접 1회에 gpt-5-mini 호출이 십수 번 발생한다.
   반복 실행하면 비용이 쌓이므로 필요할 때만 돌릴 것.

실행:
    # 터미널 1
    uvicorn backend.main:app --port 8000
    # 터미널 2
    python backend/tests/demo_flow_check.py
    python backend/tests/demo_flow_check.py --keep    # 테스트 데이터 남기기
"""

import sys
import time
import uuid
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

BASE = "http://127.0.0.1:8000"
PERSONA = "기술 리드"
MAX_TURNS = 20          # 면접이 안 끝날 때를 대비한 안전장치
KEEP = "--keep" in sys.argv

RESUME = """
백엔드 개발자 지원
- ABC테크 (2023.03~2025.12) 주문 서비스 백엔드 개발
- Python, FastAPI, MySQL, Redis 사용
- 주문 조회 API 응답 지연을 Redis 캐싱 도입으로 개선
- 결제 실패 재처리 배치 개발
- 팀 규모 5명, 일 평균 주문 3만 건 처리
"""

JD_TITLE = "백엔드 개발자 (주니어)"
JD = """
[필수 역량]
- Python 기반 웹 백엔드 개발 경험
- RDBMS 설계 및 쿼리 튜닝 경험
- REST API 설계 경험

[우대 사항]
- 캐싱 전략 수립 경험
- 대용량 트래픽 처리 경험
- 비동기 처리 경험
"""

# 턴마다 돌아가며 사용. 일부러 짧은 답을 섞어 꼬리질문을 유도한다.
ANSWERS = [
    "주문 조회 API 응답이 평균 800ms 였는데, 조회 비중이 높다고 판단해 Redis 캐싱을 도입했습니다. "
    "캐시 키는 주문 ID 기준으로 잡았고 TTL 은 5분으로 뒀습니다. 도입 후 평균 응답이 120ms 로 줄었습니다.",
    "네, 개선했습니다.",
    "결제 실패 건을 모아 30분 주기로 재처리하는 배치를 만들었습니다. 재시도는 최대 3회까지 하고, "
    "그래도 실패하면 운영팀에 알림이 가도록 했습니다.",
    "잘 모르겠습니다.",
    "팀은 5명이었고 제가 주문 도메인을 맡았습니다. 스펙 변경이 잦아서 API 버전을 나눠 관리했습니다.",
    "인덱스를 걸어서 해결했습니다.",
    "일 평균 3만 건 정도였고, 피크 시간대에는 초당 20건 정도 들어왔습니다.",
    "비동기 처리는 Celery 를 검토했지만 실제로 적용해보지는 못했습니다.",
]

_failures = []


def check(label, ok, detail=""):
    mark = "OK  " if ok else "FAIL"
    print(f"  [{mark}] {label}" + (f" — {detail}" if detail else ""))
    if not ok:
        _failures.append(label)
    return ok


def die(msg):
    print(f"\n중단: {msg}")
    sys.exit(1)


def main():
    print("=" * 60)
    print("데모 경로 백엔드 확인")
    print("=" * 60)

    # ── 0. 서버 ──────────────────────────────────────
    print("\n[0] 서버 확인")
    try:
        requests.get(f"{BASE}/", timeout=5).raise_for_status()
    except Exception as e:
        die(f"{BASE} 에 연결할 수 없습니다. 서버를 먼저 띄워주세요. ({e})")
    print(f"  [OK  ] {BASE} 응답")

    # ── 1. 회원가입 · 로그인 ─────────────────────────
    print("\n[1] 회원가입 · 로그인")
    email = f"demo-{uuid.uuid4().hex[:8]}@example.com"
    r = requests.post(f"{BASE}/auth/register",
                      json={"name": "데모", "email": email, "password": "demo1234!"}, timeout=30)
    check("회원가입", r.status_code in (200, 201), f"HTTP {r.status_code}")

    r = requests.post(f"{BASE}/auth/login",
                      json={"email": email, "password": "demo1234!"}, timeout=30)
    if r.status_code != 200:
        die(f"로그인 실패: {r.text[:200]}")
    token = r.json()["access_token"]
    H = {"Authorization": f"Bearer {token}"}
    print("  [OK  ] 로그인, 토큰 발급")

    r = requests.get(f"{BASE}/auth/me", headers=H, timeout=30)
    check("/auth/me 조회", r.status_code == 200)

    # ── 2. 이력서 · JD 등록 ──────────────────────────
    print("\n[2] 이력서 · JD 등록")
    r = requests.post(f"{BASE}/resume", json={"content": RESUME}, headers=H, timeout=30)
    if r.status_code not in (200, 201):
        die(f"이력서 등록 실패: {r.status_code} {r.text[:200]}")
    resume_id = r.json()["resume_id"]
    print(f"  [OK  ] 이력서 등록 (resume_id={resume_id})")

    r = requests.post(f"{BASE}/jd", json={"title": JD_TITLE, "content": JD}, headers=H, timeout=30)
    if r.status_code not in (200, 201):
        die(f"JD 등록 실패: {r.status_code} {r.text[:200]}")
    jd_id = r.json()["jd_id"]
    print(f"  [OK  ] JD 등록 (jd_id={jd_id})")

    # ── 3. 면접 시작 ─────────────────────────────────
    print("\n[3] 면접 시작 (LLM 호출, 1~3분 소요)")
    started = time.time()
    r = requests.post(f"{BASE}/interview/sessions",
                      json={"resume_id": resume_id, "jd_id": jd_id, "persona": PERSONA},
                      headers=H, timeout=300)
    if r.status_code != 200:
        die(f"세션 생성 실패: {r.status_code} {r.text[:300]}")
    body = r.json()
    session_id = body["session_id"]
    first_q = body.get("first_question", "")
    print(f"  [OK  ] 세션 생성 ({time.time() - started:.0f}초)")
    check("첫 질문 생성", bool(first_q.strip()))
    print(f"        Q. {first_q[:70]}...")

    # ── 4. 면접 진행 ─────────────────────────────────
    print("\n[4] 면접 진행")
    follow_ups = 0
    turns = 0
    realtime_ok = False
    finished = False

    for i in range(MAX_TURNS):
        answer = ANSWERS[i % len(ANSWERS)]
        r = requests.post(f"{BASE}/interview/sessions/{session_id}/chat",
                          json={"answer": answer}, headers=H, timeout=300)
        if r.status_code != 200:
            die(f"답변 전송 실패 ({i + 1}턴): {r.status_code} {r.text[:300]}")
        resp = r.json()
        turns += 1
        qtype = resp.get("question_type")

        # 백엔드가 실시간 점수를 실제로 내려주는지 (프론트 연결 여부와 무관)
        score = resp.get("realtime_score") or {}
        if score.get("total") is not None:
            realtime_ok = True

        if qtype == "follow_up":
            follow_ups += 1
        print(f"  {i + 1:2d}턴  type={qtype:9s} total={score.get('total')} "
              f"피드백={len(resp.get('realtime_feedback') or [])}건")

        if qtype == "end":
            finished = True
            break

    check(f"면접 종료 도달 ({turns}턴)", finished)
    check("꼬리질문 생성", follow_ups > 0, f"{follow_ups}회")
    check("실시간 점수 응답에 포함", realtime_ok)
    if not finished:
        die(f"{MAX_TURNS}턴 안에 면접이 끝나지 않았습니다.")

    # ── 5. 결과 리포트 ───────────────────────────────
    print("\n[5] 결과 리포트")
    r = requests.get(f"{BASE}/interview/sessions/{session_id}/result", headers=H, timeout=120)
    if r.status_code != 200:
        die(f"결과 조회 실패: {r.status_code} {r.text[:300]}")
    result = r.json()
    radar = result.get("radar_chart") or {}
    summary = result.get("summary") or {}

    print(f"        resume={result.get('resume_score')} "
          f"interview={result.get('interview_score')} "
          f"total={result.get('total_score')} grade={result.get('grade')}")
    print(f"        radar={radar}")

    check("이력서 점수", isinstance(result.get("resume_score"), int))
    check("면접 점수", isinstance(result.get("interview_score"), int))
    check("역량 5개 점수", len(radar) == 5 and all(v is not None for v in radar.values()))
    check("역량 점수가 전부 0 은 아님", any(v for v in radar.values()))
    check("종합 총평", any(summary.get(k) for k in ("strength", "improvement", "recommendation")))

    expected = round(result["resume_score"] * 0.3 + result["interview_score"] * 0.7)
    check("총점 = 이력서×0.3 + 면접×0.7",
          result["total_score"] == expected,
          f"{result['total_score']} vs {expected}")

    # ── 6. 피드백 보고서 ─────────────────────────────
    print("\n[6] 피드백 보고서")
    r = requests.get(f"{BASE}/interview/sessions/{session_id}/feedback", headers=H, timeout=120)
    if r.status_code != 200:
        die(f"피드백 조회 실패: {r.status_code} {r.text[:300]}")
    fb = r.json()
    items = fb.get("feedbacks") or []
    print(f"        질문 {fb.get('total_questions')}개, 평균 {fb.get('average_score')}점")
    check("질문별 피드백 존재", len(items) > 0)
    if items:
        first = items[0]
        check("질문·답변·모범답안 채워짐",
              all(first.get(k) for k in ("question", "my_answer", "improved_answer")))
        check("질문 번호가 1부터", first.get("question_number") == 1)

    # ── 7. 기록 목록 ─────────────────────────────────
    print("\n[7] 기록 목록 (마이페이지)")
    r = requests.get(f"{BASE}/interview/sessions", headers=H, timeout=60)
    if r.status_code != 200:
        die(f"목록 조회 실패: {r.status_code} {r.text[:300]}")
    listing = r.json()
    sessions = listing.get("sessions") or []
    summary_block = listing.get("summary") or {}
    print(f"        total={listing.get('total')} summary={summary_block}")

    mine = next((s for s in sessions if s["session_id"] == session_id), None)
    check("방금 면접이 목록에 있음", mine is not None)
    if mine:
        check("목록 점수가 결과 리포트와 일치",
              mine["total_score"] == result["total_score"]
              and mine["resume_score"] == result["resume_score"],
              f"목록 {mine['total_score']} vs 리포트 {result['total_score']}")
        check("페르소나 표시", mine.get("persona") == PERSONA)
        check("상태 finished", mine.get("status") == "finished")
    check("통계 집계", summary_block.get("total_interviews", 0) >= 1)

    # ── 8. DB 저장 확인 ──────────────────────────────
    print("\n[8] DB 저장 확인 (컬럼 정규화)")
    from backend.database import SessionLocal
    from backend.models.models import InterviewQuestionFeedback, InterviewResult

    db = SessionLocal()
    try:
        row = (db.query(InterviewResult)
               .filter(InterviewResult.interview_sessions_session_id == session_id).first())
        check("결과 행 저장됨", row is not None)
        if row:
            check("resume_score 컬럼에 저장", row.resume_score == result["resume_score"])
            check("역량 점수 컬럼에 저장", row.logic_score is not None)
            check("raw_report 원본 보존", bool(row.raw_report))
            rows = (db.query(InterviewQuestionFeedback)
                    .filter(InterviewQuestionFeedback.interview_results_result_id
                            == row.result_id).all())
            check("질문별 피드백이 행으로 분리", len(rows) == len(items),
                  f"DB {len(rows)}행 vs 응답 {len(items)}건")

        if not KEEP:
            if row:
                (db.query(InterviewQuestionFeedback)
                 .filter(InterviewQuestionFeedback.interview_results_result_id
                         == row.result_id).delete())
                db.delete(row)
            db.commit()
            print("        테스트 결과 데이터 정리 (--keep 으로 남길 수 있음)")
    finally:
        db.close()

    # ── 결과 ─────────────────────────────────────────
    print("\n" + "=" * 60)
    if _failures:
        print(f"실패 {len(_failures)}건")
        for f in _failures:
            print(f"  - {f}")
        print("=" * 60)
        sys.exit(1)
    print("데모 경로 전체 통과")
    print(f"세션 {session_id} / {turns}턴 / 꼬리질문 {follow_ups}회")
    print("=" * 60)


if __name__ == "__main__":
    main()
