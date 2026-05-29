"""Load documents from JSONL corpus and uploaded files."""

import json
import re
from pathlib import Path

from dotenv import load_dotenv
from llama_index.core import Document
from pypdf import PdfReader

load_dotenv()


def _guess_document_type(filename: str, text: str) -> str:
    name = filename.lower()
    if any(k in name for k in ("curriculum", "syllabus", "course")):
        return "curriculum"
    if any(k in name for k in ("admission", "fee", "apply")):
        return "admission"
    if any(k in name for k in ("placement", "report", "career")):
        return "placement"
    if any(k in name for k in ("student", "ug", "pgp", "tbm")):
        return "program"
    sample = text[:2000].lower()
    if re.search(r"\b(curriculum|syllabus|courses? offered|programme structure)\b", sample):
        return "curriculum"
    if re.search(r"\b(admission|eligibility|application|fees?)\b", sample):
        return "admission"
    return "general"


def load_documents_from_jsonl(jsonl_file: str = "final_rag_input.jsonl") -> list[Document]:
    documents = []
    path = Path(jsonl_file)
    if not path.exists():
        return documents

    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            data = json.loads(line.strip())
            source = data.get("source", "Unknown")
            text = (data.get("text") or "").strip()
            if len(text) < 30:
                continue
            documents.append(
                Document(
                    text=text,
                    metadata={
                        "file_name": source,
                        "source": source,
                        "document_type": _guess_document_type(source, text),
                    },
                )
            )
    return documents


def _read_pdf(path: Path) -> str:
    reader = PdfReader(str(path))
    pages = []
    for page in reader.pages:
        extracted = (page.extract_text() or "").strip()
        if extracted:
            pages.append(extracted)
    return "\n\n".join(pages)


def load_documents(data_dir: str = "data") -> list[Document]:
    data_path = Path(data_dir)
    if not data_path.exists():
        return []

    documents = []
    for path in sorted(data_path.rglob("*")):
        if path.is_dir():
            continue

        text = None
        suffix = path.suffix.lower()
        if suffix in {".txt", ".md"}:
            try:
                text = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                text = path.read_text(encoding="latin-1")
        elif suffix == ".pdf":
            try:
                text = _read_pdf(path)
            except Exception as exc:
                print(f"Warning: could not read PDF {path.name}: {exc}")
                continue

        text = (text or "").strip()
        if len(text) < 30:
            print(f"Warning: skipping empty or tiny file {path.name}")
            continue

        doc_type = _guess_document_type(path.name, text)
        documents.append(
            Document(
                text=text,
                metadata={
                    "file_name": path.name,
                    "source": str(path),
                    "document_type": doc_type,
                },
            )
        )
    return documents


def load_all_documents(
    jsonl_file: str = "final_rag_input.jsonl",
    data_dir: str = "data",
) -> list[Document]:
    """Merge built-in corpus with user uploads in data/."""
    documents = load_documents_from_jsonl(jsonl_file)
    uploads = load_documents(data_dir)

    seen = {d.metadata.get("file_name") for d in documents}
    for doc in uploads:
        name = doc.metadata.get("file_name")
        if name not in seen:
            documents.append(doc)
            seen.add(name)

    return documents
