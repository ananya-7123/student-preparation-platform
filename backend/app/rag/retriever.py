"""
High-level RAG retrieval functions used by both API routes and LangGraph agent tools.
"""

from typing import Optional

from app.rag.pipeline import PYPDF_AVAILABLE, get_rag_index, normalize_company_name


def search_company_docs(
    query: str,
    company_name: Optional[str] = None,
    top_k: int = 4,
) -> dict:
    """
    Search recruitment documents (company notes, PDF notices/brochures, sources)
    in resources/companies/ for relevant grounded excerpts.
    """
    cleaned_query = (query or "").strip()
    if not cleaned_query:
        return {"error": "Search query cannot be empty."}

    index = get_rag_index()
    normalized_company = normalize_company_name(company_name)
    results = index.search(
        query=cleaned_query,
        company_name=normalized_company,
        top_k=max(1, min(top_k, 10)),
    )

    return {
        "query": cleaned_query,
        "company_filter": normalized_company,
        "pypdf_installed": PYPDF_AVAILABLE,
        "total_results": len(results),
        "results": results,
    }


def get_rag_status() -> dict:
    """
    Return diagnostic information about indexed documents and chunk counts.
    """
    index = get_rag_index()
    indexed_companies = sorted({c.company for c in index.chunks if c.company != "General"})
    return {
        "pypdf_installed": PYPDF_AVAILABLE,
        "indexed_files_count": len(index.indexed_files),
        "pdf_files_found": index.pdf_files_found,
        "pdf_files_extracted": index.pdf_files_extracted,
        "total_chunks": len(index.chunks),
        "indexed_companies": indexed_companies,
        "indexed_files": index.indexed_files,
        "warnings": index.warnings,
    }

