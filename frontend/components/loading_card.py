"""면접 준비 로딩(04_면접_진행) · 결과 분석 로딩(045_결과로딩)이 같이 쓰는 로딩 카드.
"""

LOADING_CSS = """<style>
@keyframes ld_spin { to { transform: rotate(360deg); } }
.ld-wrap { min-height: 100vh; display: flex; align-items: center; justify-content: center; background: #f8fafc;
    padding: 24px; box-sizing: border-box; }
.ld-card { background: #fff; border: 1px solid #e9ecf2; border-radius: 18px; padding: 40px 44px 36px;
    width: 440px; max-width: 100%; box-sizing: border-box; text-align: center;
    font-family: Pretendard, -apple-system, sans-serif; }
.ld-cap { font-size: 12px; font-weight: 800; letter-spacing: .08em; color: #3b6def; }
.ld-spin { width: 52px; height: 52px; border-radius: 50%; border: 4px solid #eef0f4; border-top-color: #3b6def;
    animation: ld_spin .9s linear infinite; margin: 18px auto 20px; box-sizing: border-box; }
.ld-title { font-size: 20px; font-weight: 800; color: #111827; }
.ld-desc { font-size: 14px; color: #6b7280; line-height: 1.7; margin: 10px 0 24px; }
.ld-bar { height: 6px; background: #eef0f4; border-radius: 6px; overflow: hidden; margin-bottom: 22px; }
.ld-bar i { display: block; height: 100%; background: #3b6def; border-radius: 6px; transition: width .4s; }
.ld-list { display: flex; flex-direction: column; gap: 4px; text-align: left; }
.ld-li { display: flex; align-items: center; gap: 12px; padding: 11px 14px; border-radius: 12px; font-size: 14px; color: #9ca3af; }
.ld-li .k { width: 22px; height: 22px; border-radius: 50%; display: flex; align-items: center; justify-content: center;
    flex-shrink: 0; border: 2px solid #e5e7eb; box-sizing: border-box; }
.ld-li.done { color: #4b5563; }
.ld-li.done .k { background: #3b6def; border-color: #3b6def; }
.ld-li.now { background: #f5f8ff; color: #111827; font-weight: 700; }
.ld-li.now .k { border-color: #3b6def; border-top-color: #c7d4fb; animation: ld_spin .9s linear infinite; }
.ld-li .r { margin-left: auto; font-size: 12px; font-weight: 700; color: #3b6def; }
.ld-li.wait { color: #6b7280; }
.ld-li.wait .k { background: #9ca3af; border-color: #9ca3af; color: #fff; font-size: 11px; line-height: 1; }
.ld-li.fail { color: #dc2626; }
.ld-li.fail .k { background: #dc2626; border-color: #dc2626; }
</style>"""

LOADING_CSS_TEXT = LOADING_CSS.replace("<style>", "").replace("</style>", "")

_CHECK_SVG = ('<svg width="12" height="12" viewBox="0 0 256 256" aria-hidden="true">'
              '<path d="M40 144l56 56L216 80" fill="none" stroke="#fff" stroke-width="28" '
              'stroke-linecap="round" stroke-linejoin="round"/></svg>')


def loading_html(cap: str, desc_html: str, stages: list[str], stage_idx: int,
                 *, show_progress: bool = False, done_labels: list[str] | None = None) -> str:
    """stages: 단계 문구("...중..."), stage_idx: 지금 단계.

    show_progress: 진행 막대와 '완료' 글자를 보여 줄지. 실제 진행 신호로 단계가 넘어갈 때만 켠다.
    done_labels: 끝난 단계에 보여 줄 문구(없으면 '중...'을 뗀 문구).
    """
    stage_idx = max(0, min(stage_idx, len(stages) - 1))
    rows = ""
    for i, label in enumerate(stages):
        if i < stage_idx:
            text = done_labels[i] if done_labels else label.replace(" 중...", "").replace("중...", "")
            done_tag = '<span class="r">완료</span>' if show_progress else ""
            rows += f'<div class="ld-li done"><span class="k">{_CHECK_SVG}</span>{text}{done_tag}</div>'
        elif i == stage_idx:
            rows += f'<div class="ld-li now"><span class="k"></span>{label}</div>'
        else:
            text = done_labels[i] if done_labels else label.replace(" 중...", "").replace("중...", "")
            rows += f'<div class="ld-li"><span class="k"></span>{text}</div>'
    bar = ""
    if show_progress:
        pct = round((stage_idx + 0.5) / len(stages) * 100)
        bar = f'<div class="ld-bar"><i style="width:{pct}%"></i></div>'
    return (
        f'<div class="ld-wrap"><div class="ld-card"><div class="ld-cap">{cap}</div><div class="ld-spin"></div>'
        f'<div class="ld-title">{stages[stage_idx]}</div><div class="ld-desc">{desc_html}</div>'
        f'{bar}<div class="ld-list">{rows}</div></div></div>'
    )
