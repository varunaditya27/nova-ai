"""ChromaDB vector store wrapper (HttpClient against the dockerised chroma service)."""
from __future__ import annotations

import chromadb

from infra.vector_store.collections import COLLECTIONS


class ChromaVectorStore:
    def __init__(self, host: str, port: int):
        self._client = chromadb.HttpClient(host=host, port=int(port))

    def _collection(self, logical: str):
        spec = COLLECTIONS[logical]
        return self._client.get_or_create_collection(name=spec["name"], metadata=spec["metadata"])

    def add(self, collection, ids, embeddings, metadatas=None, documents=None):
        self._collection(collection).add(
            ids=list(ids), embeddings=list(embeddings),
            metadatas=metadatas, documents=documents)

    def query(self, collection, embedding, n_results=3, where=None) -> list[dict]:
        res = self._collection(collection).query(
            query_embeddings=[list(embedding)], n_results=n_results, where=where)
        ids = res.get("ids", [[]])[0]
        dists = res.get("distances", [[]])[0]
        metas = res.get("metadatas", [[]])[0]
        docs = res.get("documents", [[]])[0]
        return [
            {"id": ids[i], "distance": dists[i] if dists else None,
             "metadata": metas[i] if metas else None,
             "document": docs[i] if docs else None}
            for i in range(len(ids))
        ]

    def delete(self, collection, ids):
        self._collection(collection).delete(ids=list(ids))
