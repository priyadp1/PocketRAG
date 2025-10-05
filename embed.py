import os, json, numpy as np
from pathlib import Path
import google.generativeai as genai

ARTIFACT = Path("artifacts")

def main():
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise SystemExit("GOOGLE_API_KEY not set")
    genai.configure(api_key=api_key)
    chunks = json.loads((ARTIFACT / "chunks.json").read_text(encoding="utf-8"))
    texts = [c["text"] for c in chunks]
    embs = []
    for t in texts:
        r = genai.embed_content(model="text-embedding-004", content=t)
        embs.append(r["embedding"])
    arr = np.array(embs, dtype="float32")
    np.save(ARTIFACT / "embeddings.npy", arr)
    print(f"Saved embeddings: {arr.shape}")

if __name__ == "__main__":
    main()
