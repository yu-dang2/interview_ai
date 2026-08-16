"""
직무 지식 카드 → 벡터 인덱스 (오프라인 1회 실행)

그래프 밖에서 도는 스크립트다. 면접 런타임은 이 스크립트가 만들어둔 인덱스를 읽기만 한다.

실행:
    .venv/Scripts/python.exe scripts/build_knowledge_index.py

옵션:
    --source  카드 JSON 경로   (기본 data/job_knowledge.json)
    --path    인덱스 출력 경로 (기본 KNOWLEDGE_INDEX_PATH 또는 ./data/knowledge_index)

카드를 수정하면 다시 실행해야 반영된다. 기존 컬렉션은 삭제 후 새로 만든다
(부분 갱신은 삭제된 카드가 남아 조용히 검색되는 문제가 있어 쓰지 않는다).
"""

import argparse
import asyncio
import json
import os
import sys

from dotenv import load_dotenv

# 스크립트를 프로젝트 루트에서 실행하지 않아도 agent 패키지를 찾을 수 있게 한다.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

load_dotenv()

from agent.retrieval import store  # noqa: E402  (load_dotenv 이후에 import)

DEFAULT_SOURCE = "./data/job_knowledge.json"

REQUIRED_FIELDS = ("id", "job_family")


def load_cards(source: str) -> list[dict]:
    if not os.path.isfile(source):
        raise SystemExit(f"카드 파일을 찾을 수 없습니다: {source}")

    with open(source, encoding="utf-8") as f:
        cards = json.load(f)

    if not isinstance(cards, list) or not cards:
        raise SystemExit(f"카드 파일이 비어 있거나 리스트가 아닙니다: {source}")

    # id 누락·중복은 검색 결과 dedupe 를 망가뜨리므로 색인 전에 막는다.
    seen = set()
    for i, card in enumerate(cards):
        for field in REQUIRED_FIELDS:
            if not card.get(field):
                raise SystemExit(f"[{i}] 필수 필드 누락({field}): {card}")
        if card["id"] in seen:
            raise SystemExit(f"[{i}] id 중복: {card['id']}")
        seen.add(card["id"])

    return cards


async def build(source: str, path: str) -> None:
    import chromadb
    from chromadb.config import Settings

    cards = load_cards(source)
    texts = [store.build_embedding_text(card) for card in cards]

    print(f"카드 {len(cards)}개 로드: {source}")
    print(f"임베딩 모델: {store.embedding_model()}")

    vectors = await store.embed(texts)          # 전체를 한 번의 API 호출로
    print(f"임베딩 완료: {len(vectors)}개 x {len(vectors[0])}차원")

    os.makedirs(path, exist_ok=True)
    client = chromadb.PersistentClient(
        path=path,
        settings=Settings(anonymized_telemetry=False),
    )

    # 재실행 시 이전 내용이 남지 않도록 컬렉션을 통째로 다시 만든다.
    try:
        client.delete_collection(name=store.COLLECTION_NAME)
        print(f"기존 컬렉션 삭제: {store.COLLECTION_NAME}")
    except Exception:
        pass

    collection = client.create_collection(
        name=store.COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )

    # Chroma 메타데이터 값은 스칼라만 허용한다(리스트 불가). 카드 전체는 JSON 문자열로
    # payload 에 넣고, 검색 시 그대로 복원한다.
    collection.add(
        ids=[card["id"] for card in cards],
        embeddings=vectors,
        documents=texts,
        metadatas=[
            {
                "id": card["id"],
                "job_family": card["job_family"],
                "payload": json.dumps(card, ensure_ascii=False),
            }
            for card in cards
        ],
    )

    print(f"\n인덱싱 완료 — {collection.count()}개 카드 → {path}")
    for card in cards:
        print(f"  - {card['id']:<22} {card['job_family']}")


def main() -> None:
    parser = argparse.ArgumentParser(description="직무 지식 카드 벡터 인덱싱")
    parser.add_argument("--source", default=DEFAULT_SOURCE, help="카드 JSON 경로")
    parser.add_argument("--path", default=store.index_path(), help="인덱스 출력 경로")
    args = parser.parse_args()

    if not os.getenv("OPENAI_API_KEY"):
        raise SystemExit(
            "OPENAI_API_KEY가 설정되어 있지 않습니다. .env 파일을 확인해주세요."
        )

    asyncio.run(build(args.source, args.path))


if __name__ == "__main__":
    main()
