import numpy as np, faiss, json
from pathlib import Path

ARTIFACT = Path("artifacts")

def main():
    chunks_path = ARTIFACT / "chunks.json"
    embeddings_path = ARTIFACT / "embeddings.npy"
    index_path = ARTIFACT / "index.faiss"
    if not chunks_path.exists():
        raise SystemExit("artifacts/chunks.json not found")
    if not embeddings_path.exists():
        raise SystemExit("artifacts/embeddings.npy not found")
    blocks = json.loads(chunks_path.read_text(encoding="utf-8"))
    embs = np.load(embeddings_path).astype("float32")
    if len(blocks) != len(embs):
        raise SystemExit(f"Mismatch: {len(blocks)} chunks vs {len(embs)} embeddings")
    faiss.normalize_L2(embs)
    index = faiss.IndexFlatIP(embs.shape[1])
    index.add(embs)
    faiss.write_index(index, str(index_path))
    print(f"FAISS index written: {index_path}")

if __name__ == "__main__":
    main()
