import logging
import os
import pickle
from pathlib import Path

import faiss
import numpy as np
from openai import OpenAI

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

CORPUS_DIR = Path(__file__).parent.parent / "rag_corpus"
INDEX_DIR = CORPUS_DIR / "faiss_index"
CHUNK_SIZE = 500
EMBEDDING_MODEL = "text-embedding-3-small"


def load_corpus_files(corpus_dir: Path) -> list[dict]:
    docs = []
    for path in sorted(corpus_dir.glob("*.txt")):
        text = path.read_text(encoding="utf-8")
        docs.append({"source": path.name, "text": text})
        logging.info("loaded %s (%d chars)", path.name, len(text))
    if not docs:
        raise ValueError(f"No .txt files found in {corpus_dir}")
    return docs


def chunk_documents(docs: list[dict], chunk_size: int) -> list[dict]:
    chunks = []
    for doc in docs:
        words = doc["text"].split()
        for i in range(0, len(words), chunk_size):
            chunk_text = " ".join(words[i : i + chunk_size])
            chunks.append(
                {
                    "source": doc["source"],
                    "text": chunk_text,
                    "chunk_index": i // chunk_size,
                }
            )
    logging.info("created %d chunks from %d documents", len(chunks), len(docs))
    return chunks


def embed_texts(client: OpenAI, texts: list[str]) -> np.ndarray:
    batch_size = 100
    all_embeddings = []
    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        response = client.embeddings.create(model=EMBEDDING_MODEL, input=batch)
        batch_embeddings = [item.embedding for item in response.data]
        all_embeddings.extend(batch_embeddings)
        logging.info("embedded batch %d-%d", i, i + len(batch) - 1)
    return np.array(all_embeddings, dtype=np.float32)


def build_faiss_index(embeddings: np.ndarray) -> faiss.Index:
    dim = embeddings.shape[1]
    index = faiss.IndexFlatIP(dim)
    faiss.normalize_L2(embeddings)
    index.add(embeddings)
    logging.info("built FAISS index with %d vectors (dim=%d)", index.ntotal, dim)
    return index


def save_index(index: faiss.Index, chunks: list[dict], index_dir: Path) -> None:
    index_dir.mkdir(exist_ok=True)
    faiss.write_index(index, str(index_dir / "index.faiss"))
    with open(index_dir / "chunks.pkl", "wb") as f:
        pickle.dump(chunks, f)
    logging.info("saved index to %s", index_dir)


def main() -> None:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable is not set")

    client = OpenAI(api_key=api_key)
    docs = load_corpus_files(CORPUS_DIR)
    chunks = chunk_documents(docs, CHUNK_SIZE)
    texts = [c["text"] for c in chunks]
    embeddings = embed_texts(client, texts)
    index = build_faiss_index(embeddings)
    save_index(index, chunks, INDEX_DIR)
    logging.info("RAG index build complete")


if __name__ == "__main__":
    main()
