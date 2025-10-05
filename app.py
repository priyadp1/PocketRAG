from flask import Flask, render_template, request, redirect, url_for, flash, abort
from werkzeug.utils import secure_filename
from pathlib import Path
import os, sys, json, subprocess, uuid, shutil

APP_DIR = Path(__file__).parent.resolve()
ROOT_DATA = APP_DIR / "data"
ROOT_ART = APP_DIR / "artifacts"
UPLOAD_ALLOWED = {".pdf", ".txt", ".md"}

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-secret")
app.config["MAX_CONTENT_LENGTH"] = 100 * 1024 * 1024

def run(cmd, cwd: Path):
    p = subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError(f"Command failed: {' '.join(cmd)}\nCWD: {cwd}\nSTDOUT:\n{p.stdout}\nSTDERR:\n{p.stderr}")
    return p.stdout

def slugify(name: str) -> str:
    base = Path(name).stem.lower()
    safe = "".join(ch if ch.isalnum() or ch in "-_." else "-" for ch in base)
    return safe or uuid.uuid4().hex[:8]

def ensure_doc_workspace(doc_id: str) -> Path:
    d = ROOT_ART / doc_id
    (d / "data").mkdir(parents=True, exist_ok=True)
    (d / "artifacts").mkdir(parents=True, exist_ok=True)
    return d

def build_index_for_file(src_file: Path, doc_id: str):
    doc_dir = ensure_doc_workspace(doc_id)
    ROOT_DATA.mkdir(exist_ok=True)
    shutil.copy2(src_file, ROOT_DATA / src_file.name)
    dst = doc_dir / "data" / src_file.name
    shutil.copy2(src_file, dst)
    (doc_dir / "artifacts" / "meta.json").write_text(json.dumps({"source_file": src_file.name}, indent=2))
    run([sys.executable, str(APP_DIR / "ingest.py"), "data", "artifacts"], cwd=doc_dir)
    run([sys.executable, str(APP_DIR / "embed.py")], cwd=doc_dir)
    run([sys.executable, str(APP_DIR / "faissIndx.py")], cwd=doc_dir)

def make_summary_with_ask(doc_id: str):
    doc_dir = ROOT_ART / doc_id
    prompt = "Summarize this document into concise, study-friendly notes. Use short headings and bullet points. Base only on the document. Keep 8–15 bullets."
    run([sys.executable, str(APP_DIR / "ask.py"), prompt], cwd=doc_dir)
    last = json.loads((doc_dir / "artifacts" / "last_answer.json").read_text(encoding="utf-8"))
    (doc_dir / "artifacts" / "summary.md").write_text(last.get("answer", "").strip(), encoding="utf-8")

def run_doc_question(doc_id: str, q: str):
    d = ROOT_ART / doc_id
    run([sys.executable, str(APP_DIR / "ask.py"), q], cwd=d)
    last = json.loads((d / "artifacts" / "last_answer.json").read_text(encoding="utf-8"))
    return last.get("answer", ""), last.get("citations", [])

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST" and "file" in request.files:
        f = request.files["file"]
        if not f or f.filename == "":
            flash("No file selected.", "err")
            return redirect(url_for("index"))
        ext = Path(f.filename).suffix.lower()
        if ext not in UPLOAD_ALLOWED:
            flash(f"Unsupported file type: {ext}. Allowed: {', '.join(sorted(UPLOAD_ALLOWED))}", "err")
            return redirect(url_for("index"))
        tmp = APP_DIR / "_uploads"
        tmp.mkdir(exist_ok=True)
        filename = secure_filename(f.filename)
        saved = tmp / filename
        f.save(saved)
        doc_id = slugify(filename)
        try:
            build_index_for_file(saved, doc_id)
            make_summary_with_ask(doc_id)
            flash(f"Uploaded and indexed: {filename}", "ok")
            return redirect(url_for("doc_page", doc_id=doc_id))
        except Exception as e:
            flash(f"Indexing failed: {e}", "err")
            return redirect(url_for("index"))
    docs = []
    if ROOT_ART.exists():
        for p in sorted(ROOT_ART.iterdir()):
            if (p / "artifacts" / "index.faiss").exists():
                docs.append(p.name)
    return render_template("index.html", docs=docs)

@app.route("/doc/<doc_id>", methods=["GET", "POST"])
def doc_page(doc_id):
    d = ROOT_ART / doc_id
    if not d.exists():
        abort(404, "Unknown document.")
    meta = d / "artifacts" / "meta.json"
    summary_p = d / "artifacts" / "summary.md"
    filename = None
    if meta.exists():
        try:
            filename = json.loads(meta.read_text()).get("source_file")
        except Exception:
            filename = None
    summary = summary_p.read_text(encoding="utf-8") if summary_p.exists() else ""
    answer, citations, q = None, [], ""
    if request.method == "POST" and "q" in request.form:
        q = request.form.get("q", "").strip()
        if q:
            try:
                answer, citations = run_doc_question(doc_id, q)
            except Exception as e:
                answer = f"Error: {e}"
    return render_template("doc.html", doc_id=doc_id, filename=filename, summary=summary, q=q, answer=answer, citations=citations)

@app.route("/health")
def health():
    return {"ok": True}

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5050, debug=True)
