import streamlit as st
import streamlit.components.v1 as components
from components.sidebar import render_sidebar
from utils.state import init_session

try:
    import plotly.graph_objects as go
    import plotly.io as pio
    HAS_PLOTLY = True
except ImportError:
    HAS_PLOTLY = False

st.set_page_config(
    page_title="마이페이지 | intro",
    layout="wide",
    initial_sidebar_state="collapsed",
)

init_session()
render_sidebar(active="마이페이지")

# ── 데이터 ───────────────────────────────────────────────────────────────
HISTORY = [
    {"date": "04.30", "style": "기술 리드",   "resume": 72, "iv": 78, "total": 75, "has_video": True,  "video_url": ""},
    {"date": "04.24", "style": "인사 담당자", "resume": 70, "iv": 65, "total": 68, "has_video": False, "video_url": ""},
    {"date": "04.18", "style": "기술 리드",   "resume": 75, "iv": 82, "total": 79, "has_video": True,  "video_url": ""},
    {"date": "04.10", "style": "임원 면접관", "resume": 68, "iv": 71, "total": 70, "has_video": False, "video_url": ""},
    {"date": "04.03", "style": "기술 리드",   "resume": 60, "iv": 58, "total": 59, "has_video": True,  "video_url": ""},
]

VERSIONS = [
    {"v": "v3.0", "date": "2026.04.30", "score": 72, "active": True},
    {"v": "v2.1", "date": "2026.04.18", "score": 68, "active": False},
    {"v": "v2.0", "date": "2026.04.10", "score": 63, "active": False},
    {"v": "v1.0", "date": "2026.03.28", "score": 55, "active": False},
]

def score_color(s: int) -> str:
    if s >= 80: return "#16a34a"
    if s >= 75: return "#3b6def"
    if s >= 65: return "#d97706"
    return "#dc2626"


# ── CSS ──────────────────────────────────────────────────────────────────
st.markdown("""<style>
[data-testid="stMainBlockContainer"] { padding: 32px 40px 80px 40px !important; }
[data-testid="stVerticalBlock"] { gap: 0 !important; }
[data-testid="stHorizontalBlock"] { gap: 0 !important; }
[data-testid="stColumn"] { padding: 0 !important; }
/* st.container 없이 첫 번째 column 자체를 차트 카드로 스타일링 */
[data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:first-child {
    background: white !important;
    border: 1px solid #e5e7eb !important;
    border-radius: 8px !important;
    padding: 15px 19px 10px !important;
    box-sizing: border-box !important;
}
[data-testid="stPlotlyChart"] { border: none !important; outline: none !important; }
[data-testid="stPlotlyChart"] > div { border: none !important; }
</style>""", unsafe_allow_html=True)


# ── 헤더 ─────────────────────────────────────────────────────────────────
st.markdown(
    '<div style="margin-bottom:28px;">'
    '<p style="font-size:22px;font-weight:700;color:#111827;margin:0 0 4px;'
    'font-family:Pretendard,-apple-system,sans-serif;">마이페이지</p>'
    '<p style="font-size:14px;color:#6b7280;margin:0;'
    'font-family:Pretendard,-apple-system,sans-serif;">'
    '면접 히스토리, 점수 추이, 이력서 버전을 관리하세요</p>'
    '</div>',
    unsafe_allow_html=True,
)


# ── 통계 카드 4개 ─────────────────────────────────────────────────────────
_ICON_GROUP = (
    '<svg width="24" height="24" viewBox="0 0 24 24" fill="none">'
    '<path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" stroke="#3b6def" stroke-width="1.8"'
    ' stroke-linecap="round" stroke-linejoin="round"/>'
    '<circle cx="9" cy="7" r="4" stroke="#3b6def" stroke-width="1.8"/>'
    '<path d="M23 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75"'
    ' stroke="#3b6def" stroke-width="1.8" stroke-linecap="round"/>'
    '</svg>'
)
_ICON_MIC = (
    '<svg width="24" height="24" viewBox="0 0 24 24" fill="none">'
    '<rect x="9" y="2" width="6" height="11" rx="3" stroke="#16a34a" stroke-width="1.8"/>'
    '<path d="M5 10a7 7 0 0 0 14 0" stroke="#16a34a" stroke-width="1.8" stroke-linecap="round"/>'
    '<line x1="12" y1="17" x2="12" y2="21" stroke="#16a34a" stroke-width="1.8" stroke-linecap="round"/>'
    '<line x1="9" y1="21" x2="15" y2="21" stroke="#16a34a" stroke-width="1.8" stroke-linecap="round"/>'
    '</svg>'
)
_ICON_ORDER = (
    '<svg width="24" height="24" viewBox="0 0 24 24" fill="none">'
    '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"'
    ' stroke="#7c3aed" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>'
    '<polyline points="14 2 14 8 20 8" stroke="#7c3aed" stroke-width="1.8"'
    ' stroke-linecap="round" stroke-linejoin="round"/>'
    '<line x1="8" y1="13" x2="16" y2="13" stroke="#7c3aed" stroke-width="1.8" stroke-linecap="round"/>'
    '<line x1="8" y1="17" x2="13" y2="17" stroke="#7c3aed" stroke-width="1.8" stroke-linecap="round"/>'
    '</svg>'
)
_ICON_LINEUP = (
    '<svg width="24" height="24" viewBox="0 0 24 24" fill="none">'
    '<polyline points="23 6 13.5 15.5 8.5 10.5 1 18"'
    ' stroke="#d97706" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>'
    '<polyline points="17 6 23 6 23 12"'
    ' stroke="#d97706" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>'
    '</svg>'
)

STAT_CARDS = [
    {"v": "5회",    "lbl": "총 면접 횟수",       "color": "#3b6def", "bg": "#eef3ff", "icon": _ICON_GROUP},
    {"v": "74.8점", "lbl": "평균 면접 점수",     "color": "#16a34a", "bg": "#f0fdf4", "icon": _ICON_MIC},
    {"v": "72점",   "lbl": "현재 이력서 점수",   "color": "#7c3aed", "bg": "#f5f3ff", "icon": _ICON_ORDER},
    {"v": "+16.8",  "lbl": "최근 30일 점수 향상", "color": "#d97706", "bg": "#fffbeb", "icon": _ICON_LINEUP},
]

stat_html = '<div style="display:flex;gap:17px;padding-bottom:32px;">'
for s in STAT_CARDS:
    stat_html += (
        f'<div style="flex:1;background:white;border:1px solid #e5e7eb;border-radius:8px;'
        f'height:90px;padding:16px 19px 14px;display:flex;flex-direction:column;'
        f'justify-content:space-between;box-sizing:border-box;">'
        f'<div style="display:flex;align-items:center;gap:10px;">'
        f'<div style="width:36px;height:36px;border-radius:8px;background:{s["bg"]};'
        f'flex-shrink:0;display:flex;align-items:center;justify-content:center;">{s["icon"]}</div>'
        f'<p style="margin:0;font-size:22px;font-weight:700;color:{s["color"]};'
        f'font-family:Pretendard,-apple-system,sans-serif;line-height:1;white-space:nowrap;">{s["v"]}</p>'
        f'</div>'
        f'<p style="margin:0;font-size:11px;color:#6b7280;'
        f'font-family:Pretendard,-apple-system,sans-serif;">{s["lbl"]}</p>'
        f'</div>'
    )
stat_html += '</div>'
st.markdown(stat_html, unsafe_allow_html=True)

# ── 점수 추이 차트 + 이력서 버전 관리 ──────────────────────────────────────
col_chart, _gap, col_ver = st.columns([35, 1, 21])

with col_chart:
    if HAS_PLOTLY:
        x_labels = ["04.03", "04.10", "04.18", "04.24", "04.30"]
        iv_scores = [h["iv"] for h in reversed(HISTORY)]

        def ann_style(s):
            if s >= 80: return {"color": "#16a34a", "size": 11}
            if s < 65:  return {"color": "#dc2626", "size": 11}
            return {"color": "#374151", "size": 9}

        def dot_color(s):
            if s >= 80: return "#16a34a"
            if s < 65:  return "#dc2626"
            return "#3b6def"

        fig = go.Figure()

        fig.add_trace(go.Scatter(
            x=x_labels, y=iv_scores,
            fill="tozeroy", fillcolor="rgba(59,109,239,0.07)",
            line=dict(color="#3b6def", width=2),
            mode="lines+markers",
            marker=dict(
                size=[14 if (s >= 80 or s < 65) else 10 for s in iv_scores],
                color=[dot_color(s) for s in iv_scores],
                line=dict(color="white", width=2),
            ),
            showlegend=False,
        ))

        fig.add_shape(type="line", x0=-0.45, x1=4.45, y0=70, y1=70,
                      line=dict(color="#94a3b8", width=1))
        fig.add_annotation(
            x=4.55, y=70, text="기준<br>70",
            showarrow=False, xanchor="left", yanchor="middle",
            font=dict(size=8, color="#94a3b8", family="Pretendard"),
            align="center",
        )

        # 카테고리 축에서 annotation yshift가 불안정해서 text scatter trace 사용
        fig.add_trace(go.Scatter(
            x=x_labels,
            y=[s + 4 for s in iv_scores],
            mode="text",
            text=[str(s) for s in iv_scores],
            textposition="top center",
            textfont=dict(
                size=[ann_style(s)["size"] for s in iv_scores],
                color=[ann_style(s)["color"] for s in iv_scores],
                family="Pretendard",
            ),
            showlegend=False,
        ))

        fig.update_layout(
            title=dict(
                text="<b>점수 추이</b>",
                x=0, xanchor="left",
                font=dict(size=13, color="#374151",
                          family="Pretendard,-apple-system,sans-serif"),
                pad=dict(l=2, t=0, b=4),
            ),
            margin=dict(l=28, r=38, t=36, b=28),
            height=258,
            paper_bgcolor="white", plot_bgcolor="white",
            yaxis=dict(
                range=[35, 112],
                tickvals=[40, 60, 80, 100],
                gridcolor="#f3f4f6",
                tickfont=dict(size=9, color="#9ca3af", family="Pretendard"),
                showgrid=True, zeroline=False, showline=False,
            ),
            xaxis=dict(
                type="category",
                tickfont=dict(size=8, color="#9ca3af", family="Pretendard"),
                showgrid=False, zeroline=False, showline=False,
            ),
            font=dict(family="Pretendard, sans-serif"),
        )
        chart_html = pio.to_html(
            fig, include_plotlyjs="cdn", full_html=False,
            config={"displayModeBar": False},
        )
        components.html(
            f"""
            <link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.css">
            <style>* {{ margin:0; padding:0; font-family:'Pretendard',-apple-system,sans-serif !important; }}</style>
            {chart_html}
            """,
            height=275,
            scrolling=False,
        )
    else:
        st.info("pip install plotly 후 차트를 확인할 수 있습니다.")

with col_ver:
    ver_rows = ""
    for v in VERSIONS:
        if v["active"]:
            row_bg = "background:#eef3ff;border:1.5px solid #3b6def;"
            v_color = "#3b6def"
            s_color = "#3b6def"
        else:
            row_bg = "background:#f9fafb;border:1px solid #e5e7eb;"
            v_color = "#374151"
            s_color = "#6b7280"
        ver_rows += (
            f'<div style="{row_bg}border-radius:6px;height:36px;'
            f'display:flex;align-items:center;padding:0 16px;margin-bottom:8px;">'
            f'<span style="font-size:12px;font-weight:700;color:{v_color};'
            f'min-width:36px;font-family:Pretendard,-apple-system,sans-serif;">{v["v"]}</span>'
            f'<span style="font-size:10px;color:#6b7280;flex:1;margin-left:18px;'
            f'font-family:Pretendard,-apple-system,sans-serif;">{v["date"]}</span>'
            f'<span style="font-size:11px;font-weight:700;color:{s_color};'
            f'font-family:Pretendard,-apple-system,sans-serif;">{v["score"]}점</span>'
            f'</div>'
        )
    st.markdown(
        '<div style="background:white;border:1px solid #e5e7eb;border-radius:8px;'
        'padding:15px 19px;">'
        '<p style="font-size:13px;font-weight:600;color:#374151;margin:0 0 14px;'
        'font-family:Pretendard,-apple-system,sans-serif;">이력서 버전 관리</p>'
        + ver_rows +
        '</div>',
        unsafe_allow_html=True,
    )


# ── 면접 히스토리 ──────────────────────────────────────────────────────────
COLS = "175px 196px 165px 156px 174px 174px 1fr"

def _play_btn(video_url: str) -> str:
    return (
        f'<div data-video-url="{video_url}" style="display:inline-flex;align-items:center;gap:6px;'
        'background:#eef2ff;border:1px solid #c6d2f4;border-radius:12px;'
        'height:24px;padding:0 10px;box-sizing:border-box;cursor:pointer;">'
        '<span style="width:0;height:0;border-style:solid;border-width:3.5px 0 3.5px 6px;'
        'border-color:transparent transparent transparent #3b6def;flex-shrink:0;"></span>'
        '<span style="font-size:11px;font-weight:600;color:#3b6def;'
        'font-family:Pretendard,-apple-system,sans-serif;line-height:1;">영상</span>'
        '</div>'
    )

_HDR_STYLE = (
    'font-size:11px;font-weight:600;color:#6b7280;'
    'font-family:Pretendard,-apple-system,sans-serif;'
)

header_html = (
    f'<div style="display:grid;grid-template-columns:{COLS};'
    f'align-items:center;padding:0 0 10px 0;border-bottom:1px solid #e5e7eb;margin-bottom:0;">'
    f'<span style="{_HDR_STYLE}padding-left:16px;">날짜</span>'
    f'<span style="{_HDR_STYLE}padding-left:16px;">면접관 스타일</span>'
    f'<span style="{_HDR_STYLE}text-align:center;">이력서</span>'
    f'<span style="{_HDR_STYLE}text-align:center;">면접</span>'
    f'<span style="{_HDR_STYLE}text-align:center;">종합</span>'
    f'<span style="{_HDR_STYLE}text-align:center;">영상</span>'
    f'<span style="{_HDR_STYLE}"></span>'
    f'</div>'
)

rows_html = ""
for i, h in enumerate(HISTORY):
    row_bg = "#f9fafb" if i % 2 == 0 else "white"
    iv_c   = score_color(h["iv"])
    tot_c  = score_color(h["total"])
    rows_html += (
        f'<div style="display:grid;grid-template-columns:{COLS};'
        f'align-items:center;height:42px;background:{row_bg};'
        f'margin:0 -19px;padding:0 19px;box-sizing:border-box;">'
        f'<span style="font-size:11px;color:#6b7280;padding-left:16px;'
        f'font-family:Pretendard,-apple-system,sans-serif;">{h["date"]}</span>'
        f'<span style="font-size:11px;color:#6b7280;padding-left:16px;'
        f'font-family:Pretendard,-apple-system,sans-serif;">{h["style"]}</span>'
        f'<span style="font-size:11px;font-weight:700;color:#3b6def;text-align:center;'
        f'font-family:Pretendard,-apple-system,sans-serif;">{h["resume"]}</span>'
        f'<span style="font-size:11px;font-weight:700;color:{iv_c};text-align:center;'
        f'font-family:Pretendard,-apple-system,sans-serif;">{h["iv"]}</span>'
        f'<span style="font-size:11px;font-weight:700;color:{tot_c};text-align:center;'
        f'font-family:Pretendard,-apple-system,sans-serif;">{h["total"]}</span>'
        f'<div style="display:flex;justify-content:center;">'
        f'{_play_btn(h["video_url"]) if h["has_video"] else ""}'
        f'</div>'
        f'<a href="/결과리포트" target="_self" style="font-size:11px;font-weight:600;'
        f'color:#3b6def;text-decoration:none;text-align:right;padding-right:24px;'
        f'font-family:Pretendard,-apple-system,sans-serif;">결과 보기</a>'
        f'</div>'
    )

st.markdown(
    '<div style="background:white;border:1px solid #e5e7eb;border-radius:8px;'
    'padding:15px 19px;margin-top:20px;">'
    '<p style="font-size:13px;font-weight:600;color:#374151;margin:0 0 12px;'
    'font-family:Pretendard,-apple-system,sans-serif;">면접 히스토리</p>'
    + header_html + rows_html +
    '</div>',
    unsafe_allow_html=True,
)

components.html("""
<script>
(function () {
    var doc = window.parent.document;
    if (doc._videoModalReady) return;
    doc._videoModalReady = true;

    function closeModal() {
        var m = doc.getElementById('_video_modal');
        if (m) m.remove();
    }

    function openModal(url) {
        closeModal();

        var modal = doc.createElement('div');
        modal.id = '_video_modal';
        modal.style.cssText = 'position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.75);z-index:99999;display:flex;align-items:center;justify-content:center;';

        var box = doc.createElement('div');
        box.style.cssText = 'background:white;border-radius:16px;padding:24px;max-width:760px;width:90%;position:relative;box-sizing:border-box;';

        var closeBtn = doc.createElement('button');
        closeBtn.textContent = '✕';
        closeBtn.style.cssText = 'position:absolute;top:14px;right:16px;background:none;border:none;font-size:22px;cursor:pointer;color:#9ca3af;line-height:1;';
        closeBtn.addEventListener('click', closeModal);

        var title = doc.createElement('p');
        title.textContent = '면접 영상';
        title.style.cssText = 'font-size:15px;font-weight:600;color:#1f1f1f;margin:0 0 16px;';

        box.appendChild(closeBtn);
        box.appendChild(title);

        if (url) {
            var video = doc.createElement('video');
            video.controls = true;
            video.autoplay = true;
            video.src = url;
            video.style.cssText = 'width:100%;max-height:70vh;border-radius:8px;background:#000;display:block;';
            box.appendChild(video);
        } else {
            var ph = doc.createElement('div');
            ph.style.cssText = 'display:flex;flex-direction:column;align-items:center;justify-content:center;height:200px;color:#9ca3af;gap:12px;';
            ph.innerHTML = '<svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="#d1d5db" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z"/><circle cx="12" cy="13" r="4"/></svg><span style="font-size:14px;">저장된 영상이 없습니다</span>';
            box.appendChild(ph);
        }

        modal.appendChild(box);
        modal.addEventListener('click', function (e) { if (e.target === modal) closeModal(); });
        doc.body.appendChild(modal);
    }

    doc.addEventListener('click', function (e) {
        var btn = e.target.closest('[data-video-url]');
        if (btn) openModal(btn.getAttribute('data-video-url'));
    });
}());
</script>
""", height=0)
