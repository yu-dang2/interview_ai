"""
면접 생성 품질 평가 하네스 (RAGAS 스타일 LLM-judge)

목적
----
question_generator / answer_evaluator / report_generator 가 만들어내는 출력의 품질을
정량적으로 평가한다.

RAGAS(라가스) 기본 지표(context precision/recall 등)는 "검색 -> 답변" QA 파이프라인을
전제하므로 우리 생성 파이프라인엔 그대로 맞지 않는다. 그래서 우리 출력에 맞는 LLM-judge
지표 4종을 정의해 점수화한다. (아래 3번 faithfulness 는 RAGAS faithfulness 의 정신 -
"출력이 실제 근거에 기반하는가" - 을 그대로 따른다.)

지표 (각 0~100점 + 근거 1문장)
------------------------------
1. question_job_relevance   질문이 JD/직무 검증에 관련되는가            (answer_relevancy 계열)
2. question_realism         질문이 실제 면접처럼 현실적/답변가능한가     (#51 품질 기준 반영)
3. evaluation_faithfulness  평가 피드백이 지원자가 실제 말한 것에 근거하는가 (환각 검출 = RAGAS faithfulness)
4. feedback_usefulness      모범답안(improved_answer)이 구체적이고 유용한가

추가로 '규칙 준수 체크'(질문 대상)를 수행한다. 점수가 아니라 규칙별 위반 여부를 세어,
프롬프트 규칙(한 질문 하나만·물음표 종료·괄호 금지·암송/수치강요 금지) 위반이
평균 점수에 묻히지 않고 몇 번째 질문인지까지 그대로 드러난다.

실행
----
    # 프로젝트 루트에서, OPENAI_API_KEY 가 설정된 상태로
    python -m agent.eval.quality_eval --dataset agent/eval/eval_dataset.sample.json
    python -m agent.eval.quality_eval --dataset <내데이터> --limit 5 --detail

주의
----
- LLM-judge 라 (레코드의 질문 수 x 지표 수) 만큼 gpt-5-mini 호출이 나간다. 비용 발생.
- 판정 모델과 생성 모델이 같으면(self-preference) 점수가 후해질 수 있다. 발표/논문에
  쓸 때는 판정 모델을 분리하는 것도 고려할 것. (JUDGE_MODEL 만 바꾸면 됨)
"""

import argparse
import asyncio
import json
import logging
import statistics
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

# 프로젝트의 기존 LLM 클라이언트를 그대로 재사용한다.
# (JSON 파싱 + 지수 백오프 재시도가 이미 들어 있어 판정 호출도 안정적이다.)
from agent.graph.utils import call_llm

# OPENAI_API_KEY 를 .env 에서 읽는다 (get_client 가 os.getenv 로 참조).
# override=True: 셸에 남아 있는 옛 키가 .env 를 덮어써 크레딧 소진(429)으로 오인되는
# 사고를 막기 위해, 이 평가 도구는 .env 값을 우선한다.
load_dotenv(override=True)

logger = logging.getLogger(__name__)

# 동시 판정 호출 상한. 너무 높이면 rate limit 에 걸린다.
_CONCURRENCY = 5
_sem = asyncio.Semaphore(_CONCURRENCY)


# ---------------------------------------------------------------------------
# 판정(LLM-judge) 프롬프트 — 지표별 루브릭
#   각 프롬프트는 반드시 {"score": <0-100 정수>, "reason": "<한 문장>"} 만 출력하게 한다.
# ---------------------------------------------------------------------------
_RELEVANCE_SYS = """당신은 채용 면접 질문의 품질을 평가하는 심사관입니다.
주어진 채용공고(JD)와 면접 질문을 보고, 그 질문이 해당 직무의 역량을 검증하는 데
얼마나 관련성 있는지 0~100점으로 평가하세요.
- 90~100: 직무의 핵심 역량을 정확히 겨냥함
- 70~89 : 관련은 있으나 다소 일반적임
- 40~69 : 느슨하게만 관련됨
- 0~39  : 직무와 사실상 무관함
반드시 아래 JSON 형식만 출력하세요. 다른 말은 붙이지 마세요.
{"score": <0-100 정수>, "reason": "<한 문장 근거>"}"""

_REALISM_SYS = """당신은 실제 면접관 경험이 풍부한 심사관입니다.
주어진 면접 질문이 '실제 면접에서 지원자가 말로 답할 수 있는' 현실적인 질문인지
0~100점으로 평가하세요.
[감점 요인]
- 코드/설정파일/YAML 을 그대로 읊으라고 요구
- 과도하게 정확한 수치·설정값을 강요
- 한 문장에 여러 질문을 몰아넣음
- 괄호를 남발하거나 지나치게 길고 장황함
[가점 요인]
- 짧고 명확함, 한 번에 하나의 개념만 물음
- 판단 근거·경험·문제 해결 과정을 묻는 형태
반드시 아래 JSON 형식만 출력하세요.
{"score": <0-100 정수>, "reason": "<한 문장 근거>"}"""

_FAITHFULNESS_SYS = """당신은 면접 평가의 사실성(faithfulness)을 검증하는 심사관입니다.
'지원자 답변'과 그에 대한 '평가 피드백'을 비교해, 피드백이 지원자가 실제로 말한
내용에만 근거하는지 0~100점으로 평가하세요.
- 100: 전적으로 지원자 답변에 근거함
- 50 : 일부는 근거하나 일부는 답변에 없는 내용
- 0  : 지원자가 말하지 않은 것을 지어내 언급하거나('~라고 하셨는데' 식 날조),
       답변에 없는 사실을 근거로 평가함(환각)
지어낸 내용이 있으면 크게 감점하세요.
반드시 아래 JSON 형식만 출력하세요.
{"score": <0-100 정수>, "reason": "<한 문장 근거>"}"""

_USEFULNESS_SYS = """당신은 취업 코칭 전문가입니다.
질문, 지원자 답변, 그리고 제시된 '모범답안(개선안)'을 보고, 그 모범답안이 지원자에게
실질적으로 도움이 되는지 0~100점으로 평가하세요.
[가점] 구체적임, 지원자 답변의 부족한 점을 실제로 보완함, 지원자가 실제로 말할 수 있는
       자연스러운 형태임
[감점] 뻔한 일반론, 지원자 상황과 무관, 과장되거나 날조된 성과를 넣음
반드시 아래 JSON 형식만 출력하세요.
{"score": <0-100 정수>, "reason": "<한 문장 근거>"}"""

_COMPLIANCE_SYS = """당신은 면접 질문이 작성 규칙을 지켰는지 검사하는 검사관입니다.
주어진 질문을 아래 두 항목으로만 판정하세요.
- request_count: 질문에 담긴 서로 다른 요청(물어보는 것)의 개수. 하나의 개념만 물으면 1,
  서로 다른 것을 여러 개 이어 물으면 2 이상.
  (예: "A는 무엇이고, B는 어떻게 했으며, C도 말해 주세요" = 3)
- has_recite_demand: 코드/설정파일/YAML 을 그대로 외워 말하라거나, 정확한 설정값·수치를
  기억해 답하라고 요구하면 true, 아니면 false.
반드시 아래 JSON 형식만 출력하세요.
{"request_count": <정수>, "has_recite_demand": <true/false>, "reason": "<한 문장 근거>"}"""


# ---------------------------------------------------------------------------
# 판정 실행 헬퍼
# ---------------------------------------------------------------------------
def _clip_score(value):
    """LLM 이 준 점수를 0~100 정수로 정규화한다. 이상값이면 None."""
    try:
        return max(0, min(100, int(round(float(value)))))
    except (TypeError, ValueError):
        return None


async def _judge(system_prompt: str, payload: dict) -> dict:
    """지표 하나를 판정한다. 실패해도 예외를 올리지 않고 score=None 으로 떨어진다."""
    async with _sem:
        try:
            res = await call_llm(system_prompt, json.dumps(payload, ensure_ascii=False))
        except Exception as e:  # noqa: BLE001 - 한 지표 실패가 전체를 막지 않게 격리
            logger.warning("판정 호출 실패: %s: %s", type(e).__name__, e)
            return {"score": None, "reason": f"판정 실패: {type(e).__name__}"}
    return {"score": _clip_score(res.get("score")), "reason": str(res.get("reason", ""))}


async def _judge_raw(system_prompt: str, payload: dict) -> dict:
    """판정 결과 dict 를 그대로 반환한다(점수 정규화 없음). 실패 시 빈 dict."""
    async with _sem:
        try:
            return await call_llm(system_prompt, json.dumps(payload, ensure_ascii=False))
        except Exception as e:  # noqa: BLE001
            logger.warning("규칙 검사 호출 실패: %s: %s", type(e).__name__, e)
            return {}


# 규칙 준수 항목 (질문 대상). True=지킴 / False=위반 / None=판정불가
_COMPLIANCE_RULES = ["물음표로 끝남", "괄호 없음", "요청 1개만", "암송·수치강요 없음"]


async def check_compliance(question: str) -> dict:
    """질문 하나가 작성 규칙(프롬프트 규칙 3·7·10·11)을 지켰는지 규칙별로 판정한다.

    물음표·괄호는 문자열로 정확히 검사하고, '요청 개수'·'암송/수치강요'는 LLM 으로 판정한다.
    점수(0~100)가 아니라 규칙별 True/False 라, 위반이 평균에 묻히지 않고 그대로 드러난다.
    """
    q = (question or "").strip()
    raw = await _judge_raw(_COMPLIANCE_SYS, {"질문": q})
    try:
        req = int(raw.get("request_count"))
    except (TypeError, ValueError):
        req = None
    recite = raw.get("has_recite_demand")
    return {
        "물음표로 끝남": q.endswith("?"),
        "괄호 없음": ("(" not in q) and (")" not in q),
        "요청 1개만": (req <= 1) if req is not None else None,
        "암송·수치강요 없음": (not recite) if isinstance(recite, bool) else None,
        "_request_count": req,
        "_reason": str(raw.get("reason", "")),
    }


def _jd_to_str(jd) -> str:
    """JD(dict 또는 str)를 판정 프롬프트에 넣을 짧은 문자열로 만든다."""
    if isinstance(jd, str):
        return jd
    if not isinstance(jd, dict):
        return ""
    parts = []
    if jd.get("job_title"):
        parts.append(f"직무: {jd['job_title']}")
    if jd.get("required_skills"):
        parts.append("필수역량: " + ", ".join(jd["required_skills"]))
    if jd.get("summary"):
        parts.append(jd["summary"])
    return "\n".join(parts)


async def eval_one_qa(jd_str: str, qa: dict) -> dict:
    """
    질문-답변 한 건에 대해 적용 가능한 지표를 모두 판정한다.
    답변/피드백/모범답안이 없는 지표는 건너뛴다(부분 평가 허용).
    """
    question = (qa.get("question") or "").strip()
    answer = (qa.get("candidate_answer") or "").strip()
    improved = (qa.get("improved_answer") or "").strip()
    feedback = ((qa.get("evaluation") or {}).get("feedback") or "").strip()

    jobs = {}
    if question:
        jobs["question_job_relevance"] = _judge(_RELEVANCE_SYS, {"JD": jd_str, "질문": question})
        jobs["question_realism"] = _judge(_REALISM_SYS, {"질문": question})
    if answer and feedback:
        jobs["evaluation_faithfulness"] = _judge(
            _FAITHFULNESS_SYS, {"지원자 답변": answer, "평가 피드백": feedback}
        )
    if answer and improved:
        jobs["feedback_usefulness"] = _judge(
            _USEFULNESS_SYS,
            {"질문": question, "지원자 답변": answer, "모범답안": improved},
        )

    keys = list(jobs)
    results = await asyncio.gather(*jobs.values())
    compliance = await check_compliance(question) if question else {}
    return {"question": question, "metrics": dict(zip(keys, results)), "compliance": compliance}


# 리포트에 고정으로 나오는 지표 순서
_METRIC_ORDER = [
    "question_job_relevance",
    "question_realism",
    "evaluation_faithfulness",
    "feedback_usefulness",
]
_METRIC_LABEL = {
    "question_job_relevance": "질문 직무관련성",
    "question_realism": "질문 현실성",
    "evaluation_faithfulness": "평가 사실성",
    "feedback_usefulness": "피드백 유용성",
}


async def run_eval(dataset: list, limit: int | None) -> dict:
    """평가셋 전체를 돌려 레코드별/전체 집계를 반환한다."""
    records = dataset[:limit] if limit else dataset

    # 모든 레코드의 모든 QA 를 평평하게 펼쳐 동시에 판정한다(세마포어로 상한 제어).
    tasks, index = [], []
    for r_i, record in enumerate(records):
        jd_str = _jd_to_str(record.get("jd", ""))
        for q_i, qa in enumerate(record.get("qa", [])):
            tasks.append(eval_one_qa(jd_str, qa))
            index.append((r_i, q_i))

    flat = await asyncio.gather(*tasks)

    # 지표별 점수 + 규칙 준수 수집
    buckets = {m: [] for m in _METRIC_ORDER}
    compliance_stats = {r: {"checked": 0, "violations": []} for r in _COMPLIANCE_RULES}
    per_qa = []
    for (r_i, q_i), res in zip(index, flat):
        row = {"record": r_i, "qa": q_i, "question": res["question"], "scores": {}}
        for m, judged in res["metrics"].items():
            score = judged["score"]
            row["scores"][m] = judged
            if score is not None:
                buckets[m].append(score)
        comp = res.get("compliance") or {}
        row["compliance"] = comp
        for r in _COMPLIANCE_RULES:
            v = comp.get(r)
            if v is None:
                continue                       # 판정 불가는 집계에서 제외
            compliance_stats[r]["checked"] += 1
            if v is False:
                compliance_stats[r]["violations"].append(
                    {"record": r_i, "qa": q_i, "question": res["question"]}
                )
        per_qa.append(row)

    summary = {}
    for m in _METRIC_ORDER:
        scores = buckets[m]
        summary[m] = {
            "mean": round(statistics.mean(scores), 1) if scores else None,
            "n": len(scores),
        }

    return {"summary": summary, "compliance": compliance_stats, "per_qa": per_qa}


# ---------------------------------------------------------------------------
# 출력
# ---------------------------------------------------------------------------
def print_report(result: dict, detail: bool) -> None:
    summary = result["summary"]
    print("\n" + "=" * 52)
    print("  면접 생성 품질 평가 결과 (RAGAS 스타일 LLM-judge)")
    print("=" * 52)
    for m in _METRIC_ORDER:
        s = summary[m]
        mean = f"{s['mean']:>5}" if s["mean"] is not None else "  N/A"
        print(f"  {_METRIC_LABEL[m]:<10} {mean} 점   (n={s['n']})")
    print("=" * 52)

    # 규칙 준수 (질문 대상) — 점수가 아니라 규칙별 위반 건수
    comp = result.get("compliance", {})
    if comp:
        print("\n[규칙 준수 (질문 대상)]")
        for r in _COMPLIANCE_RULES:
            st = comp.get(r, {})
            checked = st.get("checked", 0)
            viols = st.get("violations", [])
            mark = "" if not viols else "  <-- 위반"
            print(f"  {r:<12} 위반 {len(viols)}/{checked}{mark}")
            for v in viols:
                print(f"      · (레코드 {v['record']}, 질문 {v['qa']}) {v['question'][:45]}")

    if detail:
        print("\n[질문별 상세]")
        for row in result["per_qa"]:
            print(f"\n- (레코드 {row['record']}, 질문 {row['qa']}) {row['question'][:40]}...")
            for m in _METRIC_ORDER:
                if m in row["scores"]:
                    j = row["scores"][m]
                    sc = j["score"] if j["score"] is not None else "N/A"
                    print(f"    · {_METRIC_LABEL[m]}: {sc}  — {j['reason']}")


def save_result(result: dict, out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = out_dir / f"eval_result_{stamp}.json"
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main() -> None:
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(message)s")

    parser = argparse.ArgumentParser(description="면접 생성 품질 평가 (RAGAS 스타일 LLM-judge)")
    parser.add_argument(
        "--dataset",
        default="agent/eval/eval_dataset.sample.json",
        help="평가셋 JSON 경로 (기본: 샘플셋)",
    )
    parser.add_argument("--limit", type=int, default=None, help="앞에서 N개 레코드만 평가")
    parser.add_argument("--detail", action="store_true", help="질문별 상세 점수 출력")
    parser.add_argument(
        "--out", default="agent/eval/results", help="결과 JSON 저장 디렉터리"
    )
    args = parser.parse_args()

    dataset_path = Path(args.dataset)
    if not dataset_path.exists():
        raise SystemExit(f"평가셋을 찾을 수 없습니다: {dataset_path}")

    dataset = json.loads(dataset_path.read_text(encoding="utf-8"))
    if not isinstance(dataset, list):
        raise SystemExit("평가셋 최상위는 레코드 배열이어야 합니다.")

    result = asyncio.run(run_eval(dataset, args.limit))
    result["_meta"] = {
        "dataset": str(dataset_path),
        "records": len(dataset[: args.limit] if args.limit else dataset),
        "evaluated_at": datetime.now().isoformat(timespec="seconds"),
    }

    print_report(result, args.detail)
    saved = save_result(result, Path(args.out))
    print(f"\n결과 저장: {saved}")


if __name__ == "__main__":
    main()
