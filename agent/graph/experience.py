import re
from datetime import date

_MONTHS_EN = {m: i for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], 1)}
_OPEN_END = re.compile(r"현재|재직|진행|present|now|current", re.I)
_DATE_TOKEN = re.compile(
    r"(?P<y4>(?:19|20)\d{2})\s*(?:[.\-/]\s*|년\s*)(?P<m4>\d{1,2})"       # 2020.07 / 2020-07 / 2020년 7월
    r"|(?P<mon>[A-Za-z]{3})[a-z]*\.?\s+(?P<ye>(?:19|20)\d{2})"           # Jan 2019 / March 2014
    r"|'?(?P<y2>\d{2})\s*[./]\s*(?P<m2>\d{1,2})(?!\d)"                   # 19/03 / '23.01
)


def parse_period(period: str, today: date):
    """'2020.07 ~ 2022.03', 'Jan 2019 – Present', '2022년 7월 ~ 현재' → ((y, m), (y, m)). 못 읽으면 None."""
    if not period:
        return None
    points = []
    for m in _DATE_TOKEN.finditer(str(period)):
        if m.group("y4"):
            points.append((int(m.group("y4")), int(m.group("m4"))))
        elif m.group("mon") and m.group("mon").lower()[:3] in _MONTHS_EN:
            points.append((int(m.group("ye")), _MONTHS_EN[m.group("mon").lower()[:3]]))
        elif m.group("y2"):
            points.append((2000 + int(m.group("y2")), int(m.group("m2"))))
    if not points:
        return None
    if len(points) == 1:
        if not _OPEN_END.search(str(period)):
            return None
        points.append((today.year, today.month))
    return points[0], points[1]


def months_from_periods(periods: list, today: date):
    """경력 기간들로 총 경력(개월)을 계산한다. 하나도 못 읽으면 None.

    겹치거나 바로 이어지는 기간(다음 시작이 앞 끝의 다음 달 이내)은 한 구간으로 합치고,
    떨어진 구간(공백기)은 따로 세어 더한다. 겸직은 두 번 세지 않고 공백기는 빼는 셈이다.
    구간 길이는 시작~끝 개월 차이다(예: 2020.07~2022.03 = 20개월).
    """
    spans = [s for s in (parse_period(p, today) for p in periods) if s]
    if not spans:
        return None
    idx = sorted((a[0] * 12 + a[1] - 1, b[0] * 12 + b[1] - 1) for a, b in spans)
    merged = [list(idx[0])]
    for s, e in idx[1:]:
        if s <= merged[-1][1] + 1:            # 겹치거나 바로 이어짐 → 합친다
            merged[-1][1] = max(merged[-1][1], e)
        else:                                 # 공백기 → 새 구간
            merged.append([s, e])
    return sum(e - s for s, e in merged)


def recompute_experience_years(resume_parsed: dict, today: date | None = None) -> dict:
    """파서 출력의 experience_years 를 기간으로 계산한 "N년 M개월" 로 바꾼 사본을 돌려준다.

    기간이 비었거나 하나라도 읽지 못하면 모델 값을 그대로 둔다. 일부만 읽고 더하면
    오히려 경력을 짧게 잡기 때문이다.
    """
    if not isinstance(resume_parsed, dict):
        return resume_parsed
    periods = [e.get("period") for e in resume_parsed.get("experience") or [] if isinstance(e, dict)]
    periods = [p for p in periods if p and str(p).strip() and str(p).strip() != "명시되지 않음"]
    today = today or date.today()
    if not periods or any(parse_period(p, today) is None for p in periods):
        return resume_parsed
    months = months_from_periods(periods, today)
    if months is None:
        return resume_parsed
    return {**resume_parsed, "experience_years": f"{months // 12}년 {months % 12}개월"}
