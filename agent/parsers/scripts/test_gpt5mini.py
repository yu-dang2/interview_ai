import os, json
from openai import OpenAI
from agent.parsers.jd_parser_prompt import JD_PARSER_SYSTEM_PROMPT
from agent.parsers.answer_evaluator_prompt import ANSWER_EVALUATOR_SYSTEM_PROMPT

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def call(system, user):
    r = client.chat.completions.create(model="gpt-5-mini",
        messages=[{"role":"system","content":system},{"role":"user","content":user}])
    return r.choices[0].message.content.strip()

def parse(o):
    t=o.strip()
    if t.startswith("```"): t=t.split("\n",1)[1]
    if t.endswith("```"): t=t.rsplit("```",1)[0]
    return json.loads(t.strip())

# 1) JD 파싱 — JSON 잘 나오나
jd = "백엔드 개발자 채용. 자격요건: Python, Django, 3년+. 우대: AWS, MSA."
try:
    d = parse(call(JD_PARSER_SYSTEM_PROMPT, jd))
    print("[OK] JD JSON 파싱 성공 →", list(d.keys()))
except Exception as e:
    print("[FAIL] JD JSON:", e)

# 2) 평가 점수 일관성 — temperature 빠져서 흔들리나 (같은 답변 3회)
q = json.dumps({"question":"자기소개 해주세요",
                "good_answer_criteria":"구체성/직무 연관성",
                "answer":"3년차 백엔드 개발자로 대용량 트래픽 처리 경험이 있습니다."},
               ensure_ascii=False)
scores=[]
for _ in range(3):
    try: scores.append(parse(call(ANSWER_EVALUATOR_SYSTEM_PROMPT, q)).get("eval_score"))
    except Exception as e: scores.append(f"파싱실패:{e}")
print("[평가 점수 3회]", scores, "→ 편차 크면 프롬프트에 '점수 기준' 더 명시 필요")
