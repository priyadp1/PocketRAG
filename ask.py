import os, json, numpy as np, faiss
from pathlib import Path
import google.generativeai as genai

ARTIFACT = Path("artifacts")

def embed_one(text: str) -> np.ndarray:
    r = genai.embed_content(model="text-embedding-004", content=text)
    return np.array(r["embedding"], dtype="float32")

def build_prompt(context_blocks, question):
    ctx = "\n\n".join(f"{tag}: {txt}" for tag, txt in context_blocks)
    return (
        "Answer using ONLY the provided context. If not present, say: 'Not found in the provided sources.'\n\n"
        f"Context:\n{ctx}\n\nQuestion: {question}\n\n"
        "Return a concise answer (3–6 sentences) followed by citations like [S1], [S2]."
    )

def main(question: str, k: int = 4):
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise SystemExit("GOOGLE_API_KEY not set")
    genai.configure(api_key=api_key)
    chunks = json.loads((ARTIFACT / "chunks.json").read_text(encoding="utf-8"))
    index = faiss.read_index(str(ARTIFACT / "index.faiss"))
    qv = embed_one(question).reshape(1, -1).astype("float32")
    faiss.normalize_L2(qv)
    D, I = index.search(qv, k)
    ctx = []
    for rank, idx in enumerate(I[0].tolist(), start=1):
        ch = chunks[idx]
        tag = f"S{rank}:{ch['doc']}:{ch['chunk_id']}"
        txt = ch["text"][:1200]
        ctx.append((tag, txt))
    model = genai.GenerativeModel("gemini-2.5-flash")
    prompt = build_prompt(ctx, question)
    resp = model.generate_content(prompt)
    answer = resp.text.strip()
    out = {"question": question, "citations": [t[0] for t in ctx], "answer": answer}
    (ARTIFACT / "last_answer.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(out, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python ask.py \"Your question here\"")
        raise SystemExit(1)
    main(" ".join(sys.argv[1:]))
