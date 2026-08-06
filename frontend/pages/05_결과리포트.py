import time
import streamlit as st
from utils.paths import resource
from datetime import datetime
from components.sidebar import render_sidebar
from utils.state import init_session, get, set as state_set
from utils import api

try:
    import plotly.graph_objects as go
    HAS_PLOTLY = True
except ImportError:
    HAS_PLOTLY = False

st.set_page_config(
    page_title="결과 리포트 | intro",
    layout="wide",
    initial_sidebar_state="collapsed",
)

init_session()

if "webcam_on" in st.query_params:
    st.session_state.webcam_on = st.query_params["webcam_on"] == "1"

render_sidebar(active="결과 리포트")

# ── SVG 아이콘 로드 ────────────────────────────────────────────────────────
def _svg(name: str) -> str:
    try:
        return resource(f"assets/icons/{name}").read_text()
    except Exception:
        return ""

icon_resume  = _svg("Group 8622.svg")
icon_mic     = _svg("Group 8623.svg")
icon_trophy  = _svg("Group 8624.svg")

# ── 결과 데이터 ────────────────────────────────────────────────────────────
result_data = get("result")
session_id  = get("session_id")

if not result_data and session_id:
    try:
        with st.spinner("결과를 불러오는 중..."):
            result_data = api.get_result(session_id)
        state_set("result", result_data)
    except Exception:
        result_data = None

if result_data:
    radar        = result_data.get("radar_chart", {})
    summary_obj  = result_data.get("summary", {})
    CATEGORIES   = ["논리성", "커뮤니케이션", "전문지식", "태도", "문제해결력"]
    MY_SCORES    = [
        radar.get("logic", 0),
        radar.get("communication", 0),
        radar.get("expertise", 0),
        radar.get("attitude", 0),
        radar.get("problem_solving", 0),
    ]
    AVG_SCORES   = [0] * 5
    COMPETENCIES = [(cat, s, 0, "") for cat, s in zip(CATEGORIES, MY_SCORES)]
    summary_text = "\n\n".join(filter(None, [
        summary_obj.get("strength", ""),
        summary_obj.get("improvement", ""),
        summary_obj.get("recommendation", ""),
    ]))
    date_str    = ""
    job_title   = ""
    persona_str = get("interviewer_style") or "기술 리드"
else:
    CATEGORIES   = ["논리성", "커뮤니케이션", "전문지식", "태도", "문제해결력"]
    MY_SCORES    = [59, 62, 61, 57, 62]
    AVG_SCORES   = [76, 69, 76, 74, 78]
    COMPETENCIES = [
        ("논리성",       59, 76, "논리적 흐름은 명확합니다. 결론을 먼저 말하고 근거를 이어가는 두괄식 구성으로 설득력을 높여보세요."),
        ("커뮤니케이션", 62, 69, "전달력은 양호합니다. 기술 개념을 비전문가에게 쉽게 설명하는 비유 연습을 추가하면 평균 이상으로 향상됩니다."),
        ("전문지식",     61, 76, "핵심 개념 이해도는 높습니다. 실무 프로젝트 적용 사례를 수치와 함께 구체적으로 제시하면 더 좋습니다."),
        ("태도",         57, 74, "경청 태도는 긍정적입니다. 질문 후 2초 생각 후 답변하는 습관을 기르면 자신감 있는 인상을 줄 수 있습니다."),
        ("문제해결력",   62, 78, "문제 정의는 잘 합니다. STAR 구조(상황→과제→행동→결과)로 답변을 단계별로 구조화하는 연습이 필요합니다."),
    ]
    summary_text = ""
    date_str     = "2026년 4월 30일"
    persona_str  = get("interviewer_style") or "기술 리드"

interview_score = round(sum(MY_SCORES) / len(MY_SCORES)) if MY_SCORES else 78
_now = datetime.now()
today = f"{_now.month}월 {_now.day}일"
meta_str = f"{today} &nbsp;|&nbsp; {persona_str} 면접관"

# ── CSS ───────────────────────────────────────────────────────────────────
st.markdown("""<style>
[data-testid="stMainBlockContainer"] {
    padding: 36px 40px 60px 40px !important;
    word-break: keep-all !important;
    overflow-wrap: break-word !important;
}
[data-testid="stVerticalBlock"] { gap: 0 !important; }
[data-testid="stPlotlyChart"] { padding: 0 !important; margin: 0 10px 0 0 !important; border-left: 1px solid #dedede !important; border-right: 1px solid #dedede !important; overflow: hidden !important; }
[data-testid="stPlotlyChart"] > div { padding: 0 !important; overflow: hidden !important; }
@keyframes shimmer {
  0%   { background-position: -600px 0; }
  100% { background-position:  600px 0; }
}
.sk { background: linear-gradient(90deg,#f0f2f5 25%,#e4e7ec 50%,#f0f2f5 75%); background-size:1200px 100%; animation: shimmer 1.4s infinite; border-radius:6px; }

[data-score-label], [data-panel-header], [data-comp-label], [data-comp-score] {
    white-space: nowrap !important;
}
[data-testid="stBaseButton-primary"],
[data-testid="stBaseButton-secondary"] {
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    width: auto !important;
}
[data-testid="stBaseButton-primary"] p,
[data-testid="stBaseButton-secondary"] p {
    white-space: nowrap !important;
    text-align: center !important;
    overflow: visible !important;
}
.st-key-bottom_actions {
    display: flex !important;
    flex-direction: row !important;
    justify-content: flex-end !important;
    align-items: center !important;
    gap: 12px !important;
}
</style>""", unsafe_allow_html=True)

# ── 헤더 ──────────────────────────────────────────────────────────────────
st.markdown(
    '<div style="margin-bottom:28px;">'
    '<div style="font-size:24px;font-weight:700;color:#1f1f1f;margin:0 0 6px;">면접 결과 리포트</div>'
    f'<p style="font-size:14px;color:#9ca3af;margin:0;">{meta_str}</p>'
    '</div>',
    unsafe_allow_html=True
)

# ── 점수 카드 (단일 카드 3분할) ──────────────────────────────────────────
def _score_section(color, pill_bg, pill_border, label, icon, sublabel, score, fill_pct, badge, sub):
    return (
        f'<div style="flex:1;padding:14px 20px 14px;display:flex;flex-direction:column;justify-content:space-between;">'
        f'<div style="background:{pill_bg};border:1px solid {pill_border};border-radius:10px;height:20px;display:flex;align-items:center;justify-content:center;">'
        f'<span data-score-label style="font-size:9px;font-weight:700;color:{color};">{label}</span>'
        f'</div>'
        f'<div style="display:flex;align-items:center;justify-content:space-between;">'
        f'<div style="display:flex;align-items:center;gap:6px;">{icon}<span data-score-label style="font-size:11px;color:#6b7280;">{sublabel}</span></div>'
        f'<span data-score-label style="font-size:26px;font-weight:700;color:{color};line-height:1;">{score}점</span>'
        f'</div>'
        f'<div style="background:#e5e7eb;height:6px;border-radius:3px;">'
        f'<div style="background:{color};height:6px;border-radius:3px;width:{fill_pct}%;"></div>'
        f'</div>'
        f'<div style="display:flex;align-items:center;gap:6px;">'
        f'<div style="background:{pill_bg};border:1px solid {color};border-radius:9px;padding:0 8px;height:18px;display:flex;align-items:center;">'
        f'<span data-score-label style="font-size:9px;font-weight:700;color:{color};line-height:1;position:relative;top:0.5px;">{badge}</span>'
        f'</div>'
        f'<span data-score-label style="font-size:10px;color:#6b7280;">{sub}</span>'
        f'</div>'
        f'</div>'
    )

_div = '<div style="width:1px;background:#dee3e8;margin:11px 0;flex-shrink:0;"></div>'

st.markdown(
    '<div style="background:white;border:1px solid #e5e7eb;border-radius:8px;overflow:hidden;">'
    '<div style="display:flex;min-height:148px;">'
    + _score_section('#d97706','#fffbeb','rgba(217,119,6,0.3)','1차 서류 전형',icon_resume,'이력서 분석',72,72,'보통','JD 키워드 57% 매칭')
    + _div
    + _score_section('#3b6def','#eef3ff','rgba(59,109,239,0.3)','2차 면접 전형',icon_mic,'AI 면접 코칭',interview_score,interview_score,'우수','상위 23% 수준')
    + _div
    + _score_section('#16a34a','#f0fdf4','rgba(22,163,74,0.3)','최종 종합 평가',icon_trophy,'합산 결과',75,75,'우수','합격 권장 수준')
    + '</div></div><div style="height:32px"></div>',
    unsafe_allow_html=True
)

# ── 레이더 차트 + 종합 총평 ───────────────────────────────────────────────
col_l, col_r = st.columns([485, 635])

with col_l:
    st.markdown(
        '<div style="background:white;border:1px solid #dedede;border-radius:12px 12px 0 0;padding:19px 23px 16px;margin-right:10px;">'
        '<div data-panel-header style="font-size:15px;font-weight:600;color:#1f1f1f;padding-bottom:12px;border-bottom:1px solid #dedede;">역량 레이더 차트</div>'
        '</div>',
        unsafe_allow_html=True
    )
    if HAS_PLOTLY:
        cats     = CATEGORIES + [CATEGORIES[0]]
        vals     = MY_SCORES  + [MY_SCORES[0]]
        avg_vals = AVG_SCORES + [AVG_SCORES[0]]
        fig = go.Figure()
        fig.add_trace(go.Scatterpolar(
            r=avg_vals, theta=cats, fill="none",
            line=dict(color="#d1d5db", width=1.5, dash="dot"),
            name="평균", showlegend=False,
        ))
        fig.add_trace(go.Scatterpolar(
            r=vals, theta=cats, fill="toself",
            fillcolor="rgba(59,109,239,0.12)",
            line=dict(color="#3b6def", width=2),
            name="내 점수", showlegend=False,
        ))
        fig.update_layout(
            polar=dict(
                radialaxis=dict(visible=True, range=[0, 100],
                                tickfont=dict(size=9), gridcolor="#f1f5f9"),
                angularaxis=dict(tickfont=dict(size=11, color="#a6a6a6")),
                bgcolor="white",
            ),
            margin=dict(l=90, r=90, t=55, b=70),
            paper_bgcolor="white", height=380,
        )
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
    st.markdown(
        '<div style="background:white;border:1px solid #dedede;border-top:none;border-radius:0 0 12px 12px;height:20px;margin-right:10px;"></div>',
        unsafe_allow_html=True
    )

with col_r:
    if summary_text:
        st.markdown(
            '<div style="background:white;border:1px solid #dedede;border-radius:12px;padding:19px 23px;min-height:445px;box-sizing:border-box;margin-left:10px;">'
            '<div data-panel-header style="font-size:15px;font-weight:600;color:#1f1f1f;padding-bottom:12px;border-bottom:1px solid #dedede;margin-bottom:16px;">종합 총평</div>'
            f'<div style="font-size:13px;color:#374151;line-height:1.8;white-space:pre-wrap;">{summary_text}</div>'
            '</div>',
            unsafe_allow_html=True
        )
    else:
        st.markdown(
            '<div style="background:white;border:1px solid #dedede;border-radius:12px;padding:19px 23px;min-height:445px;box-sizing:border-box;margin-left:10px;">'
            '<div data-panel-header style="font-size:15px;font-weight:600;color:#1f1f1f;padding-bottom:12px;border-bottom:1px solid #dedede;margin-bottom:16px;">종합 총평</div>'
            '<div style="margin-bottom:16px;">'
            '<div data-panel-header style="font-size:13px;font-weight:600;color:#3b6def;margin-bottom:6px;">강점</div>'
            '<div style="font-size:12px;color:#1f1f1f;line-height:1.7;">논리적 사고와 태도가 우수합니다. LangGraph 기반 상태 관리 개념을 명확히 이해하고 있습니다.</div>'
            '</div>'
            '<div style="background:#dedede;height:1px;margin-bottom:16px;"></div>'
            '<div style="margin-bottom:16px;">'
            '<div data-panel-header style="font-size:13px;font-weight:600;color:#3b6def;margin-bottom:6px;">개선점</div>'
            '<div style="font-size:12px;color:#1f1f1f;line-height:1.7;">답변 구체성이 부족합니다. 실제 수치와 프로젝트 성과를 포함한 답변을 연습하세요.</div>'
            '</div>'
            '<div style="background:#dedede;height:1px;margin-bottom:16px;"></div>'
            '<div>'
            '<div data-panel-header style="font-size:13px;font-weight:600;color:#3b6def;margin-bottom:6px;">추천 학습</div>'
            '<div style="font-size:12px;color:#1f1f1f;line-height:1.7;">Pydantic 심화 학습 및 RAG 파이프라인 구현 경험을 추가하면 직무 전문성이 향상됩니다.</div>'
            '</div>'
            '</div>',
            unsafe_allow_html=True
        )

# ── 면접 역량 평가 ────────────────────────────────────────────────────────
comp_rows = ""
for label, score, avg, comment in COMPETENCIES:
    s = min(max(score, 0), 100)
    a = min(max(avg, 0), 100)
    comp_rows += (
        '<div style="position:relative;background:#fbfcff;border:1px solid #e5e8ec;border-left:4px solid #3b6ef0;border-radius:8px;min-height:65px;display:flex;align-items:center;margin-bottom:7px;">'
        '<div style="width:140px;padding:0 0 0 12px;flex-shrink:0;">'
        f'<div data-comp-label style="font-size:13px;font-weight:600;color:#38455c;margin-bottom:3px;">{label}</div>'
        f'<span data-comp-score style="font-size:12px;font-weight:600;color:#3b6ef0;">{score}점</span>'
        f'<span data-comp-score style="font-size:11px;color:#9ca3b0;"> / 평균 {avg}</span>'
        '</div>'
        '<div style="flex:1;padding:0 16px;position:relative;">'
        f'<div style="font-size:10px;color:#3b6ef0;position:absolute;top:calc(50% - 20px);left:calc(16px + {s}% - 8px);">{score}</div>'
        '<div style="background:#e5e8eb;height:5px;border-radius:3px;position:relative;">'
        f'<div style="background:#3b6ef0;height:5px;border-radius:3px;width:{s}%;"></div>'
        f'<div style="position:absolute;left:{a}%;top:-4px;width:2px;height:13px;background:rgba(191,196,204,0.8);transform:translateX(-50%);border-radius:1px;"></div>'
        '</div>'
        '</div>'
        '<div style="width:1px;align-self:stretch;margin:10px 0;background:#e5e8eb;flex-shrink:0;"></div>'
        f'<div style="flex:1;padding:12px 16px;font-size:11.5px;color:#5e6673;line-height:18px;">{comment}</div>'
        '</div>'
    )

st.markdown(
    '<div style="height:32px"></div>'
    '<div style="background:white;border:1px solid #e5e7eb;border-radius:8px;padding:19px 23px 12px;">'
    '<div style="font-size:15px;font-weight:600;color:#111827;margin-bottom:4px;">면접 역량 평가</div>'
    '<div style="font-size:12px;color:#6b7280;margin-bottom:12px;padding-bottom:12px;border-bottom:1px solid #e5e8eb;">AI 면접관이 분석한 5가지 역량 — 점수 및 개선 코멘트</div>'
    + comp_rows
    + '</div><div style="height:32px"></div>',
    unsafe_allow_html=True
)

# ── AI 영상 분석 코멘트 (웹캠 ON일 때) ───────────────────────────────────
if st.session_state.get("webcam_on", False):
    if not st.session_state.get("webcam_result_ready", False):
        st.markdown(
            '<div style="background:white;border:1px solid #e5e7eb;border-radius:12px;box-shadow:0 2px 8px rgba(0,0,0,0.04);'
            'display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center;padding:24px 23px;min-height:152px;box-sizing:border-box;">'
            '<p style="font-size:15px;font-weight:600;color:#121827;margin:0 0 10px;">영상 분석 중입니다...</p>'
            '<p style="font-size:13px;color:#6b7280;line-height:20px;margin:0;">'
            '면접 영상을 바탕으로 AI가 시선 처리를 분석하고 있습니다.<br>'
            '분석이 완료되면 결과가 자동으로 표시됩니다.<br>'
            '잠시만 기다려 주세요.'
            '</p>'
            '</div><div style="height:32px"></div>',
            unsafe_allow_html=True
        )
        time.sleep(3.0)
        st.session_state.webcam_result_ready = True
        st.rerun()
    else:
        WEBCAM_RESULTS = [
            ("시선 처리", "카메라 방향으로 시선을 더 맞추면 자신감이 높아 보여요."),
            ("발화 속도", "적정 속도로 발화했어요. 듣기 편한 속도입니다."),
        ]
        webcam_rows = ""
        for i, (metric, comment) in enumerate(WEBCAM_RESULTS):
            top_border = "" if i == 0 else "padding-top:20px;"
            webcam_rows += (
                f'<div style="display:flex;align-items:center;gap:0;{top_border}">'
                f'<span style="font-size:12px;font-weight:600;color:#3b6def;white-space:nowrap;min-width:48px;">{metric}</span>'
                '<div style="width:1px;height:22px;background:#cbd2da;flex-shrink:0;margin:0 10px;"></div>'
                f'<span style="font-size:12px;color:#5e6673;">{comment}</span>'
                '</div>'
            )
        st.markdown(
            '<div style="background:white;border:1px solid #e5e8ec;border-radius:8px;overflow:hidden;">'
            '<div style="padding:16px 19px 0;">'
            '<div data-panel-header style="font-size:15px;font-weight:600;color:#1f1f1f;padding-bottom:12px;border-bottom:1px solid #dedede;">AI 영상 분석 코멘트</div>'
            '</div>'
            f'<div style="padding:16px 19px 16px;">{webcam_rows}</div>'
            '</div><div style="height:32px"></div>',
            unsafe_allow_html=True
        )

# ── 하단 버튼 ─────────────────────────────────────────────────────────────
with st.container(key="bottom_actions"):
    if st.button("다시 면접하기"):
        state_set("session_id",     None)
        state_set("first_question", None)
        state_set("result",         None)
        state_set("interview_done", False)
        if "iv_messages" in st.session_state:
            del st.session_state["iv_messages"]
        st.switch_page("pages/03_면접_환경설정.py")
    if st.button("피드백 보고서 보기", type="primary"):
        st.switch_page("pages/06_피드백보고서.py")
