# 면접 생성 품질 평가 (RAGAS 스타일 LLM-judge)

`question_generator` / `answer_evaluator` / `report_generator` 의 출력 품질을 정량 평가하는
독립 하네스입니다. 다른 모듈 코드를 건드리지 않고, 평가셋(JSON)만 넣으면 돌아갑니다.

## 왜 RAGAS 를 그대로 안 쓰나
RAGAS(라가스) 기본 지표(context precision/recall 등)는 "검색 → 답변" QA 파이프라인을
전제합니다. 우리는 생성 파이프라인(질문 생성·답변 평가·리포트)이라 그대로 매핑되지 않아,
우리 출력에 맞는 LLM-judge 지표 4종으로 재구성했습니다. (`평가 사실성`은 RAGAS
faithfulness 의 정신을 그대로 따릅니다.)

## 지표 (각 0~100점)
| 지표 | 무엇을 보나 | 대상 |
|---|---|---|
| 질문 직무관련성 | 질문이 JD/직무 검증에 관련되나 | question_generator |
| 질문 현실성 | 실제 면접처럼 답변 가능한가 (#51 기준) | question_generator |
| 평가 사실성 | 피드백이 실제 답변에 근거하나 (환각 검출) | answer_evaluator |
| 피드백 유용성 | 모범답안이 구체적·유용한가 | report_generator |

## 실행
프로젝트 루트에서, `OPENAI_API_KEY` 가 설정된 상태로:

```bash
python -m agent.eval.quality_eval --dataset agent/eval/eval_dataset.sample.json
```

옵션:
- `--limit N` : 앞에서 N개 레코드만
- `--detail`  : 질문별 상세 점수·근거 출력
- `--out DIR` : 결과 JSON 저장 위치 (기본 `agent/eval/results/`)

> LLM-judge 라 (질문 수 × 지표 수) 만큼 gpt-5-mini 호출이 나갑니다. 비용이 발생하니
> 큰 평가셋은 `--limit` 로 먼저 확인하세요.

## 평가셋 형식
`eval_dataset.sample.json` 참고. 최상위는 레코드 배열이고, 각 레코드는:

```json
{
  "jd": { "job_title": "...", "required_skills": ["..."], "summary": "..." },
  "qa": [
    {
      "question": "면접 질문",
      "candidate_answer": "지원자 답변",
      "evaluation": { "score": 82, "feedback": "평가 피드백" },
      "improved_answer": "모범답안(개선안)"
    }
  ]
}
```
- `candidate_answer`/`evaluation`/`improved_answer` 가 없는 지표는 자동으로 건너뜁니다(부분 평가 허용).
- 실제 면접 세션 결과(리포트 JSON)를 이 형식으로 뽑아 넣으면 그대로 평가됩니다.
