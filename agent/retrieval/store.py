import json
import logging
import os

from agent.graph.utils import get_client

logger = logging.getLogger(__name__)

COLLECTION_NAME = "job_knowledge"

DEFAULT_INDEX_PATH = "./data/knowledge_index"
DEFAULT_EMBEDDING_MODEL = "text-embedding-3-small"

# 실제 채용공고로 측정해 정한 값. 카드를 추가하거나 임베딩 모델을 바꾸면 다시 측정할 것.
DEFAULT_MAX_RESULTS = 1
DEFAULT_MAX_DISTANCE = 0.48

_collection = None
_load_warned = False


def index_path() -> str:
    return os.getenv("KNOWLEDGE_INDEX_PATH", DEFAULT_INDEX_PATH)


def embedding_model() -> str:
    return os.getenv("EMBEDDING_MODEL", DEFAULT_EMBEDDING_MODEL)


def max_distance() -> float:
    return float(os.getenv("KNOWLEDGE_MAX_DISTANCE", DEFAULT_MAX_DISTANCE))


def build_job_query(jd_parsed: dict) -> str:
    """카드가 직무 단위 문서라 쿼리도 직무 단위(직무명 + 필수 기술)여야 한다. 우대 기술은 넣지 않는다."""
    if not isinstance(jd_parsed, dict):
        return ""

    title = (jd_parsed.get("job_title") or "").strip()
    skills = [s.strip() for s in (jd_parsed.get("required_skills") or []) if str(s).strip()]

    if not title and not skills:
        return ""
    if not skills:
        return title
    return f"{title} / 요구 역량: {', '.join(skills)}"


def build_embedding_text(card: dict) -> str:
    """인덱스 빌드(scripts/build_knowledge_index.py)도 이 함수를 써야 한다. 검색용 필드만 넣는다."""
    parts = [
        card.get("job_family", ""),
        " ".join(card.get("aliases", []) or []),
        card.get("scope_summary", ""),
        " ".join(card.get("related_keywords", []) or []),
        # 구 스키마 호환
        " ".join(card.get("core_competencies", []) or []),
        card.get("evaluation_points", ""),
        card.get("industry_trends", ""),
    ]
    return "\n".join(p for p in parts if p)


async def embed(texts: list[str]) -> list[list[float]]:
    client = get_client()
    response = await client.embeddings.create(model=embedding_model(), input=texts)
    return [item.embedding for item in sorted(response.data, key=lambda d: d.index)]


def get_collection():
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
        # get_or_create 를 쓰면 빈 컬렉션이 생겨 인덱스 부재를 알아차리기 어렵다.
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
    global _collection, _load_warned
    _collection = None
    _load_warned = False


async def search(
    queries: list[str],
    k: int = 3,
    max_results: int = DEFAULT_MAX_RESULTS,
    max_dist: float | None = None,
) -> list[dict]:
    cleaned = [q.strip() for q in (queries or []) if isinstance(q, str) and q.strip()]
    if not cleaned:
        return []

    collection = get_collection()
    if collection is None:
        return []

    vectors = await embed(cleaned)

    result = collection.query(
        query_embeddings=vectors,
        n_results=min(k, collection.count()),
        include=["metadatas", "distances"],
    )

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
        logger.info(
            "관련 직무 카드 없음 — 참고자료 없이 진행합니다 (최근접 %s, 거리 %.4f > %.2f)",
            ranked[0].get("job_family"), ranked[0]["_distance"], limit,
        )

    return kept[:max_results]
