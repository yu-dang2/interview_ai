import streamlit as st
import streamlit.components.v1 as components
from datetime import datetime
from components.sidebar import render_sidebar
from utils.state import init_session, get, handle_session_expired
from utils import api

st.set_page_config(
    page_title="피드백 보고서 | intro",
    layout="wide",
    initial_sidebar_state="collapsed",
)

init_session()
render_sidebar(active="피드백 보고서")

# ── 피드백 데이터 조회 ────────────────────────────────────────────────────────
session_id    = get("session_id")
feedback_data = None

if session_id:
    try:
        feedback_data = api.get_feedback(session_id)
    except api.SessionExpiredError:
        handle_session_expired()
    except Exception:
        feedback_data = None

st.markdown("""
<div style="position:fixed;top:0;right:0;height:60px;
            display:flex;align-items:center;padding:0 24px;z-index:600;">
  <div data-pdf-btn style="background:#3b6def;color:white;font-size:13px;font-weight:500;
              height:36px;padding:0 18px;border-radius:8px;cursor:pointer;
              display:flex;align-items:center;user-select:none;">PDF 다운로드</div>
</div>
""", unsafe_allow_html=True)
components.html("""
<script>
(function () {
    function attach() {
        var doc = window.parent.document;
        var btn = doc.querySelector('[data-pdf-btn]');
        if (!btn) { setTimeout(attach, 300); return; }
        btn.onclick = function () { window.parent.print(); };
    }
    attach();
}());
</script>
""", height=0)

# ── CSS ───────────────────────────────────────────────────────────────────
st.markdown("""<style>
[data-testid="stMainBlockContainer"] {
    padding: 36px 40px 60px 40px !important;
    word-break: keep-all !important;
    overflow-wrap: break-word !important;
}
[data-testid="stVerticalBlock"] { gap: 0 !important; }
[data-testid="stHorizontalBlock"] { gap: 0 !important; }

.st-key-pagination,
.st-key-pagination > div,
.st-key-pagination [data-testid="stVerticalBlockBorderWrapper"],
.st-key-pagination [data-testid="stVerticalBlock"] {
    display: flex !important;
    flex-direction: row !important;
    justify-content: center !important;
    align-items: center !important;
    gap: 20px !important;
}
.st-key-pagination [data-testid="stElementContainer"] {
    width: auto !important;
}
[data-page-number] {
    font-size: 14px !important;
    color: #a6a6a6 !important;
    position: relative !important;
    top: -2px !important;
}
[data-testid="stBaseButton-secondary"] {
    width: auto !important;
}

@media print {
    [data-testid="stSidebar"],
    header, footer,
    [data-testid="stToolbar"],
    [data-testid="stStatusWidget"],
    [data-testid="stDecoration"],
    [data-testid="stHorizontalBlock"],
    [data-pdf-btn] { display: none !important; }
    [data-testid="stMain"] { margin-left: 0 !important; }
    [data-testid="stMainBlockContainer"] { padding: 24px 32px !important; }
    body, [data-testid="stAppViewContainer"] { background: white !important; }
}
</style>""", unsafe_allow_html=True)

# ── 데이터 ────────────────────────────────────────────────────────────────
ALL_QA = [
    {"q": "LangGraph의 상태 관리 방식에 대해 설명해주세요.", "score": 72,
     "my": "LangGraph는 노드와 엣지로 구성되며, State 객체를 기반으로 대화 흐름을 관리합니다.",
     "better": "LangGraph는 TypedDict로 정의된 State 객체를 통해 노드 간 데이터를 공유하며, Conditional Edge로 동적 라우팅을 구현합니다. 실제로 면접 진행 상태·이전 답변 키워드·누적 점수를 State로 관리하여 맥락 유지형 대화를 구현했습니다."},
    {"q": "FastAPI와 비동기 처리를 어떻게 활용했나요?", "score": 65,
     "my": "FastAPI는 비동기 처리를 지원해서 LLM 응답 대기 시간에도 다른 요청을 처리할 수 있습니다.",
     "better": "FastAPI의 async/await 패턴과 StreamingResponse를 결합하여 LLM 토큰을 실시간 전달했습니다. 이를 통해 첫 토큰 기준 응답 대기 시간을 3초에서 0.5초로 단축했습니다."},
    {"q": "RAG 파이프라인 구성 경험이 있으신가요?", "score": 58,
     "my": "RAG는 검색 증강 생성으로 외부 데이터를 LLM에 제공하는 방식입니다.",
     "better": "FAISS 벡터 DB를 구축하고 LangChain의 RetrievalQA 체인으로 채용 공고 데이터를 임베딩하여 질문 생성에 활용했습니다. 청크 사이즈 최적화로 검색 정확도를 18% 향상시켰습니다."},
    {"q": "Pydantic을 사용한 데이터 검증 경험을 설명해주세요.", "score": 71,
     "my": "Pydantic은 Python 타입 힌트를 이용한 데이터 검증 라이브러리입니다.",
     "better": "FastAPI의 Request/Response 모델을 Pydantic BaseModel로 정의하여 타입 안전성을 보장했습니다. 특히 LLM 출력을 구조화된 JSON으로 파싱할 때 ValidationError 핸들링으로 안정성을 높였습니다."},
    {"q": "CI/CD 파이프라인 구축 경험이 있으신가요?", "score": 68,
     "my": "GitHub Actions를 이용해 자동 배포를 구축했습니다.",
     "better": "GitHub Actions에서 pytest → Docker 빌드 → ECR 푸시 → ECS 롤링 업데이트 파이프라인을 구성했습니다. 테스트 커버리지 80% 미달 시 배포를 차단하는 게이트를 추가했습니다."},
    {"q": "팀 협업에서 어려움을 겪었던 경험을 말씀해주세요.", "score": 75,
     "my": "팀원 간 의견 충돌이 있었을 때 소통을 통해 해결했습니다.",
     "better": "백엔드·프론트 간 API 스펙 충돌이 잦았습니다. OpenAPI 스펙을 먼저 합의하고 Mock 서버(Prism)를 도입하여 병렬 개발을 가능하게 했습니다. 결과적으로 통합 오류를 60% 줄였습니다."},
    {"q": "대용량 데이터 처리 경험을 설명해주세요.", "score": 55,
     "my": "Pandas를 이용해서 데이터를 처리한 경험이 있습니다.",
     "better": "1GB 이상 CSV를 처리할 때 chunked reading과 Dask를 활용했습니다. 메모리 사용량을 80% 줄이고 처리 시간을 12분에서 2.3분으로 단축했습니다."},
    {"q": "코드 리뷰 문화를 어떻게 생각하시나요?", "score": 80,
     "my": "코드 리뷰는 코드 품질 향상에 매우 중요하다고 생각합니다.",
     "better": "코드 리뷰는 버그 예방뿐 아니라 팀 지식 공유의 핵심 채널이라 생각합니다. PR 단위를 500줄 이하로 유지하고 Conventional Comments 규칙을 도입하여 리뷰 사이클을 2일→4시간으로 단축한 경험이 있습니다."},
    {"q": "기술 부채를 어떻게 관리하시나요?", "score": 63,
     "my": "기술 부채는 중요하다고 생각하고 꾸준히 리팩터링해야 한다고 생각합니다.",
     "better": "스프린트마다 20% 시간을 기술 부채 해소에 배정했습니다. SonarQube로 코드 스멜을 정량화하고, 임계값 초과 시 스프린트 계획에 의무 포함하는 프로세스를 수립했습니다."},
    {"q": "최근 관심 있게 보고 있는 기술 트렌드는 무엇인가요?", "score": 77,
     "my": "AI와 LLM 관련 기술에 관심이 많습니다.",
     "better": "LLM 기반 에이전트 오케스트레이션에 관심이 있습니다. 특히 LangGraph의 Cyclic Graph로 자기 수정 능력을 갖춘 에이전트를 설계하고 있으며, 이를 면접 코칭 시스템의 핵심 엔진으로 적용 중입니다."},
    {"q": "5년 후 커리어 목표를 말씀해주세요.", "score": 70,
     "my": "AI 분야의 전문가가 되고 싶습니다.",
     "better": "AI 애플리케이션 아키텍트로 성장하고 싶습니다. 단순 LLM 호출을 넘어 에이전트 시스템 설계 능력을 갖추고, 3년 내 AI 서비스 아키텍처를 주도적으로 설계할 수 있는 시니어로 성장하는 것이 목표입니다."},
    {"q": "이 회사에 지원한 이유는 무엇인가요?", "score": 82,
     "my": "카카오의 AI 기술력과 서비스 스케일에 매력을 느꼈습니다.",
     "better": "카카오의 초대규모 AI KoGPT와 실사용 트래픽이 결합된 환경에서 성장하고 싶습니다. 특히 카카오톡 AI 어시스턴트 팀의 실시간 추론 최적화 사례를 분석했으며, 제가 연구한 스트리밍 응답 기술을 이 팀에서 발전시키고 싶습니다."},
]

if feedback_data and feedback_data.get("feedbacks"):
    ALL_QA = [
        {
            "q":      fb["question"],
            "score":  fb["score"],
            "my":     fb["my_answer"],
            "better": fb["improved_answer"],
        }
        for fb in feedback_data["feedbacks"]
    ]

ITEMS_PER_PAGE = 3

if "fb_page" not in st.session_state:
    st.session_state.fb_page = 0

_now         = datetime.now()
today        = f"{_now.month}월 {_now.day}일"
avg_score    = round(sum(qa["score"] for qa in ALL_QA) / len(ALL_QA))
total_pages  = (len(ALL_QA) + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE
page_idx     = st.session_state.fb_page
current_qa   = ALL_QA[page_idx * ITEMS_PER_PAGE : (page_idx + 1) * ITEMS_PER_PAGE]

# ── 헤더 ──────────────────────────────────────────────────────────────────
st.markdown(
    '<div style="margin-bottom:28px;">'
    '<div style="font-size:24px;font-weight:700;color:#1f1f1f;margin:0 0 6px;">질문별 피드백 보고서</div>'
    f'<p style="font-size:14px;color:#a6a6a6;margin:0;">총 {len(ALL_QA)}개 질문 &nbsp;|&nbsp; 평균 점수 {avg_score}점 &nbsp;|&nbsp; {today}</p>'
    '</div>',
    unsafe_allow_html=True
)

# ── QA 카드 ───────────────────────────────────────────────────────────────
cards_html = ""
for i, qa in enumerate(current_qa):
    q_num = page_idx * ITEMS_PER_PAGE + i + 1
    score = qa["score"]
    if score >= 70:
        badge_bg, badge_color = "#def7de", "#2ea647"
    else:
        badge_bg, badge_color = "#ffedde", "#eb8c14"

    cards_html += (
        '<div style="background:white;border:1px solid #dedede;border-radius:12px;overflow:hidden;margin-bottom:12px;">'
        '<div style="display:flex;justify-content:space-between;align-items:flex-start;padding:15px 19px 13px;">'
        f'<div style="font-size:14px;font-weight:600;color:#1f1f1f;flex:1;margin-right:12px;line-height:1.5;">Q{q_num}. {qa["q"]}</div>'
        f'<div style="background:{badge_bg};border-radius:13px;height:26px;min-width:56px;padding:0 10px;display:flex;align-items:center;justify-content:center;flex-shrink:0;">'
        f'<span style="font-size:12px;font-weight:500;color:{badge_color};">{score}점</span>'
        '</div>'
        '</div>'
        '<div style="height:1px;background:#dedede;margin:0 19px;"></div>'
        '<div style="padding:13px 19px 13px;">'
        '<div style="font-size:11px;font-weight:500;color:#a6a6a6;margin-bottom:6px;">내 답변</div>'
        f'<div style="font-size:13px;color:#1f1f1f;line-height:1.65;">{qa["my"]}</div>'
        '</div>'
        '<div style="height:1px;background:#e0edff;margin:0 19px;"></div>'
        '<div style="padding:13px 19px 16px;">'
        '<div style="font-size:11px;font-weight:500;color:#3d78f2;margin-bottom:6px;">개선 답변 제안</div>'
        f'<div style="font-size:13px;color:#264db2;line-height:21px;">{qa["better"]}</div>'
        '</div>'
        '</div>'
    )

st.markdown(cards_html + '<div style="height:16px"></div>', unsafe_allow_html=True)

# ── 페이지네이션 ──────────────────────────────────────────────────────────
with st.container(key="pagination"):
    if st.button("＜", disabled=(page_idx == 0)):
        st.session_state.fb_page -= 1
        st.rerun()
    st.markdown(
        f'<span data-page-number>{page_idx + 1} / {total_pages}</span>',
        unsafe_allow_html=True,
    )
    if st.button("＞", disabled=(page_idx >= total_pages - 1)):
        st.session_state.fb_page += 1
        st.rerun()
