"""
RAG Document Pipeline for KIIT Placement Preparation Platform.

Loads verified company notes (*.md) and recruitment brochures/notices (*.pdf)
from resources/companies/, chunks them cleanly, and builds a lightweight
TF-IDF + NumPy cosine similarity vector index for fast, grounded retrieval.
"""

from collections import Counter
from dataclasses import dataclass
import csv
import math
from pathlib import Path
import re
from typing import Dict, List, Optional

from langchain_text_splitters import RecursiveCharacterTextSplitter
import numpy as np

try:
    from pypdf import PdfReader

    PYPDF_AVAILABLE = True
except ImportError:
    PdfReader = None  # type: ignore[assignment]
    PYPDF_AVAILABLE = False

PROJECT_ROOT = Path(__file__).resolve().parents[3]
RESOURCES_COMPANIES_DIR = PROJECT_ROOT / "resources" / "companies"

FOLDER_COMPANY_MAP: Dict[str, str] = {
    "accenture": "Accenture",
    "capgemini": "Capgemini",
    "cognizant": "Cognizant",
    "deloitte": "Deloitte",
    "highradius (hrc)": "HighRadius",
    "highradius": "HighRadius",
    "hrc": "HighRadius",
    "ibm": "IBM",
    "infosys": "Infosys",
    "tcs": "TCS",
    "tech mahindra": "Tech Mahindra",
    "techmahindra": "Tech Mahindra",
    "wipro": "Wipro",
}

TOKEN_PATTERN = re.compile(r"[a-z0-9]+")


def normalize_company_name(raw_name: Optional[str]) -> Optional[str]:
    if not raw_name or not raw_name.strip():
        return None
    cleaned = raw_name.strip().lower()
    return FOLDER_COMPANY_MAP.get(cleaned, raw_name.strip())


def tokenize(text: str) -> List[str]:
    return TOKEN_PATTERN.findall(text.lower())


@dataclass
class RagChunk:
    chunk_id: int
    company: str
    doc_type: str
    source_file: str
    relative_path: str
    page: Optional[int]
    content: str


class RagIndex:
    """In-memory TF-IDF vector index over resources/companies/ documents."""

    def __init__(self, base_dir: Path = RESOURCES_COMPANIES_DIR) -> None:
        self.base_dir = base_dir
        self.chunks: List[RagChunk] = []
        self.vocab: Dict[str, int] = {}
        self.idf: np.ndarray = np.array([], dtype=np.float32)
        self.matrix: np.ndarray = np.zeros((0, 0), dtype=np.float32)
        self.indexed_files: List[str] = []
        self.pdf_files_found: int = 0
        self.pdf_files_extracted: int = 0
        self.warnings: List[str] = []

        self._build_index()

    def _load_documents(self) -> List[dict]:
        docs: List[dict] = []
        if not self.base_dir.exists():
            self.warnings.append(f"Resources directory not found: {self.base_dir}")
            return docs

        splitter = RecursiveCharacterTextSplitter(
            chunk_size=700,
            chunk_overlap=120,
            separators=["\n## ", "\n### ", "\n\n", "\n", ". ", " "],
        )

        # Iterate each company folder inside resources/companies/
        for company_dir in sorted(self.base_dir.iterdir()):
            if not company_dir.is_dir():
                continue

            company_name = normalize_company_name(company_dir.name) or company_dir.name

            for file_path in sorted(company_dir.rglob("*")):
                if not file_path.is_file():
                    continue

                suffix = file_path.suffix.lower()
                fname_lower = file_path.name.lower()
                rel_path = str(file_path.relative_to(PROJECT_ROOT)).replace("\\", "/")

                # Skip empty category placeholder README.md files
                if suffix == ".md" and fname_lower == "readme.md":
                    continue

                if suffix == ".md":
                    text_content = file_path.read_text(encoding="utf-8", errors="ignore").strip()
                    if not text_content:
                        continue
                    self.indexed_files.append(rel_path)
                    for piece in splitter.split_text(text_content):
                        docs.append(
                            {
                                "company": company_name,
                                "doc_type": "notes" if "07_notes" in rel_path else "sources",
                                "source_file": file_path.name,
                                "relative_path": rel_path,
                                "page": None,
                                "content": piece.strip(),
                            }
                        )

                elif suffix == ".pdf":
                    self.pdf_files_found += 1
                    if not PYPDF_AVAILABLE or PdfReader is None:
                        continue

                    try:
                        reader = PdfReader(str(file_path))
                        extracted_any = False
                        for page_idx, page in enumerate(reader.pages, start=1):
                            page_text = (page.extract_text() or "").strip()
                            if not page_text:
                                continue
                            extracted_any = True
                            for piece in splitter.split_text(page_text):
                                docs.append(
                                    {
                                        "company": company_name,
                                        "doc_type": "pdf",
                                        "source_file": file_path.name,
                                        "relative_path": rel_path,
                                        "page": page_idx,
                                        "content": piece.strip(),
                                    }
                                )
                        if extracted_any:
                            self.pdf_files_extracted += 1
                            self.indexed_files.append(rel_path)
                        else:
                            self.warnings.append(
                                f"PDF has no selectable text layer (possibly scanned image): {rel_path}"
                            )
                    except Exception as exc:
                        self.warnings.append(f"Failed to read PDF {rel_path}: {exc}")

        if self.pdf_files_found > 0 and not PYPDF_AVAILABLE:
            self.warnings.append(
                "pypdf is not installed; install pypdf (`pip install pypdf`) to index PDF brochures/notices."
            )

        # Also include dataset_manifest.csv metadata summary if present
        manifest_path = self.base_dir / "dataset_manifest.csv"
        if manifest_path.exists():
            try:
                with manifest_path.open("r", encoding="utf-8-sig", newline="") as fh:
                    rows = list(csv.DictReader(fh))
                if rows:
                    lines = ["Dataset Manifest of Verified Company Resources:"]
                    for r in rows:
                        lines.append(
                            f"- {r.get('company', '')}: {r.get('original_filename', '')} "
                            f"({r.get('content_type', '')})"
                        )
                    rel_manifest = str(manifest_path.relative_to(PROJECT_ROOT)).replace("\\", "/")
                    self.indexed_files.append(rel_manifest)
                    for piece in splitter.split_text("\n".join(lines)):
                        docs.append(
                            {
                                "company": "General",
                                "doc_type": "manifest",
                                "source_file": manifest_path.name,
                                "relative_path": rel_manifest,
                                "page": None,
                                "content": piece.strip(),
                            }
                        )
            except Exception as exc:
                self.warnings.append(f"Failed to read manifest CSV: {exc}")

        return docs

    def _build_index(self) -> None:
        raw_docs = self._load_documents()
        if not raw_docs:
            return

        self.chunks = [
            RagChunk(
                chunk_id=idx,
                company=d["company"],
                doc_type=d["doc_type"],
                source_file=d["source_file"],
                relative_path=d["relative_path"],
                page=d["page"],
                content=d["content"],
            )
            for idx, d in enumerate(raw_docs)
        ]

        tokenized_docs: List[Counter] = []
        df_counts: Counter = Counter()

        for chunk in self.chunks:
            # Include company name & source filename lightly so queries mentioning company name match strongly
            weighted_text = f"{chunk.company} {chunk.source_file} {chunk.content}"
            counts = Counter(tokenize(weighted_text))
            tokenized_docs.append(counts)
            for tok in counts.keys():
                df_counts[tok] += 1

        sorted_terms = sorted(df_counts.keys())
        self.vocab = {term: idx for idx, term in enumerate(sorted_terms)}
        num_docs = len(self.chunks)
        num_terms = len(sorted_terms)

        idf = np.zeros(num_terms, dtype=np.float32)
        for term, idx in self.vocab.items():
            idf[idx] = math.log((1.0 + num_docs) / (1.0 + df_counts[term])) + 1.0
        self.idf = idf

        mat = np.zeros((num_docs, num_terms), dtype=np.float32)
        for doc_idx, counts in enumerate(tokenized_docs):
            for term, tf in counts.items():
                col = self.vocab[term]
                mat[doc_idx, col] = (1.0 + math.log(tf)) * idf[col]

        norms = np.linalg.norm(mat, axis=1, keepdims=True)
        norms[norms == 0.0] = 1.0
        self.matrix = mat / norms

    def _encode_query(self, query: str) -> Optional[np.ndarray]:
        if not self.vocab or self.matrix.shape[0] == 0:
            return None
        counts = Counter(tokenize(query))
        if not counts:
            return None

        vec = np.zeros(len(self.vocab), dtype=np.float32)
        for term, tf in counts.items():
            col = self.vocab.get(term)
            if col is not None:
                vec[col] = (1.0 + math.log(tf)) * self.idf[col]

        norm = float(np.linalg.norm(vec))
        if norm == 0.0:
            return None
        return vec / norm

    def search(
        self,
        query: str,
        company_name: Optional[str] = None,
        top_k: int = 4,
    ) -> List[dict]:
        if not self.chunks:
            return []

        query_vec = self._encode_query(query)
        target_company = normalize_company_name(company_name)

        if target_company:
            candidate_indices = [
                i
                for i, c in enumerate(self.chunks)
                if c.company.lower() == target_company.lower()
            ]
        else:
            candidate_indices = list(range(len(self.chunks)))

        if not candidate_indices:
            return []

        if query_vec is None:
            scored = [(i, 0.0) for i in candidate_indices]
        else:
            sub_mat = self.matrix[candidate_indices]
            cos_scores = sub_mat @ query_vec
            q_tokens = set(tokenize(query))
            scored = []
            for local_idx, chunk_idx in enumerate(candidate_indices):
                base_score = float(cos_scores[local_idx])
                chunk = self.chunks[chunk_idx]
                content_tokens = set(tokenize(chunk.content))
                overlap = (
                    len(q_tokens & content_tokens) / max(1, len(q_tokens))
                    if q_tokens
                    else 0.0
                )
                if chunk.doc_type in ("notes", "pdf"):
                    doc_boost = 0.14
                elif chunk.doc_type in ("sources", "manifest"):
                    doc_boost = -0.12
                else:
                    doc_boost = 0.0
                combined_score = round(max(0.0, base_score + 0.15 * overlap + doc_boost), 4)
                scored.append((chunk_idx, combined_score))

        scored.sort(key=lambda item: item[1], reverse=True)
        top_results: List[dict] = []
        for chunk_idx, score in scored[: max(1, top_k)]:
            if query_vec is not None and score <= 0.0:
                continue
            c = self.chunks[chunk_idx]
            top_results.append(
                {
                    "chunk_id": c.chunk_id,
                    "company": c.company,
                    "doc_type": c.doc_type,
                    "source_file": c.source_file,
                    "relative_path": c.relative_path,
                    "page": c.page,
                    "score": score,
                    "content": c.content,
                }
            )
        return top_results


_INDEX_INSTANCE: Optional[RagIndex] = None


def get_rag_index(force_rebuild: bool = False) -> RagIndex:
    global _INDEX_INSTANCE
    if _INDEX_INSTANCE is None or force_rebuild:
        _INDEX_INSTANCE = RagIndex()
    return _INDEX_INSTANCE
