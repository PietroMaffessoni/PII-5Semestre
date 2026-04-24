from qdrant_client import QdrantClient


def create_client(url: str = "http://localhost:6333") -> QdrantClient:
    return QdrantClient(url=url)
