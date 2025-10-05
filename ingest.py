import sys, json, re
from pathlib import Path
from pypdf import PdfReader

def resolve_dirs(argv):
    if len(argv) >= 2:
        input_dir = Path(argv[1])
    else:
        input_dir = Path("data")
    if len(argv) >= 3:
        output_dir = Path(argv[2])
    else:
        output_dir = Path("artifacts")
    output_dir.mkdir(parents=True, exist_ok=True)
    return input_dir, output_dir

def clean(text: str) -> str:
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()

def read_pdf(p: Path, max_pages: int | None = 80) -> str:
    out = []
    with open(p, "rb") as f:
        pdf = PdfReader(f)
        for i, page in enumerate(pdf.pages):
            if max_pages and i >= max_pages:
                break
            out.append(page.extract_text() or "")
    return "\n".join(out)

def read_txt(p: Path) -> str:
    return p.read_text(encoding="utf-8", errors="ignore")

def chunk_text(text: str, max_chars=1800, overlap=150):
    chunks = []
    i = 0
    n = len(text)
    while i < n:
        j = min(n, i + max_chars)
        k = text.rfind(".", i, j)
        if k == -1 or k - i < int(max_chars * 0.6):
            k = j
        chunk = text[i:k].strip()
        if chunk:
            chunks.append(chunk)
        i = max(k - overlap, k)
    return chunks

def main():
    input_dir, output_dir = resolve_dirs(sys.argv)
    docs = []
    for p in input_dir.glob("*"):
        if p.suffix.lower() == ".pdf":
            docs.append((p.name, clean(read_pdf(p))))
        elif p.suffix.lower() in {".txt", ".md"}:
            docs.append((p.name, clean(read_txt(p))))
    if not docs:
        raise SystemExit("No documents found.")
    out = []
    for doc_id, (name, text) in enumerate(docs, start=1):
        for local_id, ch in enumerate(chunk_text(text), start=1):
            out.append({"chunk_id": f"D{doc_id}-C{local_id}", "doc": name, "text": ch})
    (output_dir / "chunks.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    (output_dir / "meta.json").write_text(json.dumps({"docs": [d[0] for d in docs]}, indent=2), encoding="utf-8")
    print(f"Chunks written: {len(out)}")

if __name__ == "__main__":
    main()
