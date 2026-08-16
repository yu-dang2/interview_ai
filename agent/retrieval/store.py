"""
직무 지식 카드 벡터 검색 (RAG 검색 계층)

채용공고(JD)가 질문 생성의 주재료이고, 여기서 검색하는 직무 지식 카드는
"이 직무를 더 전문적으로 파고들 관점"을 보태는 보조 참고자료다.
공고를 대체하지 않는다.

설계 메모:
- chromadb 는 지연 import 한다. 미설치 환경(팀원 PC)에서 이 모듈을 import 했다는
  이유만으로 서버가 죽으면 안 되기 때문이다. backend/routers/uploads.py 가
  pypdf/docx 를 함수 안에서 import 하는 것과 같은 이유.
- 인덱스가 없거나 비어 있으면 예외 대신 빈 리스트 + 경고 로그로 떨어진다.
  RAG 는 품질 보조 기능이라 없으면 질문이 조금 덜 전문적일 뿐, 면접은 굴러가야 한다.
- 임베딩 모델은 text-embedding-3-small 을 명시 지정한다. Chroma 기본 임베딩
  (all-MiniLM-L6-v2)은 한국어 성능이 나빠서 그대로 두면 검색 품질이 통째로 무너진다.
  add/query 양쪽에 항상 우리가 만든 벡터를 넘기므로 Chroma 기본 임베딩은 실행되지 않는다.
- search() 는 async 다. 임베딩이 네트워크 호출이라 동기로 만들면 FastAPI 이벤트 루프를
  블로킹한다. 그래프 노드도 전부 async 이므로 호출부는 `await store.search(...)`.

검색 쿼리 입도(실측으로 정한 것 — 바꾸기 전에 반드시 재실측할 것):
    카드가 '직무 단위' 문서이므로 쿼리도 직무 단위여야 한다. 6개 직무 시나리오로 A/B 한 결과,
      A) match_result 의 interview_topics/missing_skills (세부 기술 단어) → 3/6
      B) jd_parsed 의 job_title + required_skills 를 합친 단일 쿼리      → 6/6
    A 가 무너지는 이유는 짧은 키워드가 여러 직무에 걸쳐 모호하기 때문이다. 예를 들어
    "대용량 트래픽"은 백엔드(서버 부하)와 마케팅(웹 유입) 양쪽에서 진짜 핵심 용어라
    백엔드 0.7407 / 마케팅 0.7478 로 사실상 구분이 안 됐다. build_job_query() 를 쓸 것.
    (카드를 청크로 쪼개 색인하는 방식도 실측했으나 오답이 늘어 폐기했다)

환경 변수(모두 선택, 기본값으로 동작):
    KNOWLEDGE_INDEX_PATH  벡터 인덱스 디렉터리 (기본 ./data/knowledge_index)
    EMBEDDING_MODEL       임베딩 모델      (기본 text-embedding-3-small)
"""

import json
import logging
import os

from agent.graph.utils import get_client

logger = logging.getLogger(__name__)

COLLECTION_NAME = "job_knowledge"

DEFAULT_INDEX_PATH = "./data/knowledge_index"
DEFAULT_EMBEDDING_MODEL = "text-embedding-3-small"

# 프롬프트에 실어 보낼 카드 수 상한. JD 가 주재료이고 이건 보조 참고자료이므로 소수여야 한다.
# 2인 이유: 한 공고가 두 직무에 걸치는 경우("그로스 마케터 겸 데이터 분석")를 커버하되,
# 그 이상은 관련 없는 직무가 섞여 질문이 산만해진다.
DEFAULT_MAX_RESULTS = 2

# 이 거리를 넘으면 "관련 카드 없음"으로 보고 버린다.
# 실측 근거(6개 직무 시나리오): 정답 카드 0.2951~0.4713, 2위 카드 0.5461~0.6486,
# 완전 무관한 쿼리("김치찌개 끓이는 법") 0.7875~0.8392.
# 0.60 은 정답을 전부 통과시키면서 무관한 카드를 걸러내는 지점이다.
# 코퍼스를 늘리면 분포가 달라지므로 재측정할 것.
DEFAULT_MAX_DISTANCE = 0.60

_collection = None          # 성공적으로 연 컬렉션 (싱글턴)
_load_warned = False        # 인덱스 부재 경고를 매 호출마다 찍지 않기 위한 플래그


# ── 설정 (import 시점이 아니라 호출 시점에 읽는다) ──────────
# backend.core.config 가 load_dotenv() 를 이미 했든, 스크립트가 직접 했든
# 양쪽 모두에서 동작하게 하려는 것. agent/ 가 backend/ 를 import 하지 않도록
# 여기서는 os.getenv 만 쓴다.

def index_path() -> str:
    return os.getenv("KNOWLEDGE_INDEX_PATH", DEFAULT_INDEX_PATH)


def embedding_model() -> str:
    return os.getenv("EMBEDDING_MODEL", DEFAULT_EMBEDDING_MODEL)


def max_distance() -> float:
    return float(os.getenv("KNOWLEDGE_MAX_DISTANCE", DEFAULT_MAX_DISTANCE))


# ── 검색 쿼리 구성 ─────────────────────────────────────────
def build_job_query(jd_parsed: dict) -> str:
    """
    jd_parsed → 직무 단위 검색 쿼리 1개.

    카드가 직무 단위 문서라 쿼리도 같은 입도여야 한다(모듈 docstring 의 A/B 실측 참고).
    필수 기술만 넣고 우대 기술은 뺀다. 우대는 부수적이라 넣으면 직무 정체성이 흐려진다.
    """
    if not isinstance(jd_parsed, dict):
        return ""

    title = (jd_parsed.get("job_title") or "").strip()
    skills = [s.strip() for s in (jd_parsed.get("required_skills") or []) if str(s).strip()]

    if not title and not skills:
        return ""
    if not skills:
        return title
    return f"{title} / 요구 역량: {', '.join(skills)}"


# ── 임베딩 텍스트 구성 ─────────────────────────────────────
def build_embedding_text(card: dict) -> str:
    """
    카드 하나를 임베딩할 텍스트로 만든다.

    인덱싱 스크립트와 이 모듈이 반드시 같은 함수를 써야 한다. 색인할 때와 검색할 때의
    텍스트 구성이 어긋나면 검색이 조용히 망가진다.

    job_family 만 넣으면 "백엔드 개발" 같은 직무명에만 걸리는데, 실제 검색 쿼리는
    match_result 의 interview_topics/missing_skills 라서 "대용량 트래픽", "Redis" 처럼
    세부 역량·기술명으로 들어온다. 그 간극을 aliases 와 related_keywords 가 메운다.

    interview_perspective 는 일부러 제외한다. 면접관 행동 지시문이라 검색 쿼리와
    매칭될 일이 없고 임베딩에 노이즈만 준다. (반환 payload 에는 그대로 포함된다)
    """
    parts = [
        card.get("job_family", ""),
        " ".join(card.get("aliases", []) or []),
        " ".join(card.get("core_competencies", []) or []),
        " ".join(card.get("related_keywords", []) or []),
        card.get("evaluation_points", ""),
        card.get("industry_trends", ""),
    ]
    return "\n".join(p for p in parts if p)


# ── 임베딩 ────────────────────────────────────────────────
async def embed(texts: list[str]) -> list[list[float]]:
    """여러 텍스트를 한 번의 API 호출로 임베딩한다.

    토픽마다 따로 호출하면 왕복이 토픽 수만큼 늘어난다. 면접 시작 경로에 들어가는
    노드라 그만큼 시작이 느려진다(직전 커밋에서 파서 병렬화로 줄여놓은 시간을 도로
    까먹는다). OpenAI 임베딩 API 는 배열 입력을 받으므로 항상 묶어서 보낸다.
    """
    client = get_client()
    response = await client.embeddings.create(model=embedding_model(), input=texts)
    # API 가 순서를 보장하지만, 방어적으로 index 기준 정렬 후 반환한다.
    return [item.embedding for item in sorted(response.data, key=lambda d: d.index)]


# ── 컬렉션 로드 ───────────────────────────────────────────
def get_collection():
    """읽기용 컬렉션을 반환한다. 없으면 None (예외를 던지지 않는다)."""
    global _collection, _load_warned

    if _collection is not None:
        return _collection

    path = index_path()
    try:
        import chromadb
        from chromadb.config import Settings

        if not os.path.isdir(path):
            raise FileNotFoundError(f"인덱스 디렉터리가 없습니다: {path}")

        client = chromadb.PersistentClient(
            path=path,
            settings=Settings(anonymized_telemetry=False),
        )
        # get_or_create 가 아니라 get 을 쓴다. 읽기 경로에서 빈 컬렉션을 만들어두면
        # "인덱스가 있다"고 착각하게 되고 원인 파악이 어려워진다.
        collection = client.get_collection(name=COLLECTION_NAME)

        if collection.count() == 0:
            raise ValueError(f"컬렉션이 비어 있습니다: {COLLECTION_NAME}")

        _collection = collection
        logger.info(
            "직무 지식 인덱스 로드 완료 (%d개 카드, path=%s)", collection.count(), path
        )
        return _collection

    except Exception as e:
        if not _load_warned:
            _load_warned = True
            logger.warning(
                "직무 지식 인덱스를 열 수 없습니다 — RAG 참고자료 없이 동작합니다 "
                "(%s: %s). 'python scripts/build_knowledge_index.py' 로 인덱스를 "
                "생성하세요.",
                type(e).__name__, e,
            )
        return None


def reset_cache() -> None:
    """싱글턴 캐시를 비운다. 인덱스를 다시 만든 뒤 재로드할 때 사용."""
    global _collection, _load_warned
    _collection = None
    _load_warned = False


# ── 검색 ──────────────────────────────────────────────────
async def search(
    queries: list[str],
    k: int = 3,
    max_results: int = DEFAULT_MAX_RESULTS,
    max_dist: float | None = None,
) -> list[dict]:
    """
    직무 지식 카드를 검색해 중복 제거·거리 필터를 거친 목록을 반환한다.

    queries     검색어 목록. 보통 build_job_query() 결과 하나를 리스트로 감싸 넘긴다.
    k           쿼리 하나당 가져올 카드 수
    max_results 최종 반환 상한 (프롬프트 비대화 방지)
    max_dist    이 거리를 넘는 카드는 버린다. None 이면 max_distance() 기본값.

    반환 원소 = 카드 원본 + 검색 메타(_distance, _matched_query).
    인덱스가 없거나, 쿼리가 비었거나, 관련 카드가 없으면 빈 리스트.
    """
    cleaned = [q.strip() for q in (queries or []) if isinstance(q, str) and q.strip()]
    if not cleaned:
        return []

    collection = get_collection()
    if collection is None:
        return []

    # 쿼리 전체를 한 번에 임베딩 (왕복 1회)
    vectors = await embed(cleaned)

    result = collection.query(
        query_embeddings=vectors,
        n_results=min(k, collection.count()),
        include=["metadatas", "distances"],
    )

    # 쿼리별 결과를 카드 id 기준으로 합치되, 가장 가까운(작은) 거리만 남긴다.
    best: dict[str, dict] = {}
    for query, metadatas, distances in zip(
        cleaned, result["metadatas"], result["distances"]
    ):
        for metadata, distance in zip(metadatas, distances):
            payload = metadata.get("payload")
            if not payload:
                continue
            try:
                card = json.loads(payload)
            except json.JSONDecodeError:
                logger.warning("카드 payload 파싱 실패 — 건너뜁니다: %s", metadata.get("id"))
                continue

            card_id = card.get("id") or metadata.get("id")
            previous = best.get(card_id)
            if previous is None or distance < previous["_distance"]:
                best[card_id] = {**card, "_distance": distance, "_matched_query": query}

    limit = max_distance() if max_dist is None else max_dist
    ranked = sorted(best.values(), key=lambda c: c["_distance"])
    kept = [c for c in ranked if c["_distance"] <= limit]

    if ranked and not kept:
        # 코퍼스에 없는 직무의 공고. 억지로 끼워 맞춘 카드를 넘기면 엉뚱한 관점이
        # 질문에 섞이므로 아무것도 주지 않는 편이 낫다.
        logger.info(
            "관련 직무 카드 없음 — 참고자료 없이 진행합니다 (최근접 %s, 거리 %.4f > %.2f)",
            ranked[0].get("job_family"), ranked[0]["_distance"], limit,
        )

    return kept[:max_results]
