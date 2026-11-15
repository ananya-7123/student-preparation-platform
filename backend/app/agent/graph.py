import concurrent.futures
import os
import re
from typing import Any, List, Optional

from dotenv import load_dotenv
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent

from app.agent.prompts import get_placement_system_prompt
from app.agent.tools import (
    COMPANY_ALIASES,
    get_company_details,
    get_eligibility,
    get_selection_process,
    get_student_performance,
    list_all_companies,
    search_questions,
    search_recruitment_docs,
)

load_dotenv()


# ============================================================================
# LangChain @tool Wrappers (Database + RAG)
# ============================================================================

@tool
def tool_list_companies() -> dict:
    """List all companies registered in the PostgreSQL placement database."""
    return list_all_companies()


@tool
def tool_company_details(company_name: str) -> dict:
    """Retrieve general overview and industry details for a specific company."""
    return get_company_details(company_name)


@tool
def tool_eligibility(company_name: str) -> dict:
    """Retrieve eligibility criteria (CGPA cutoff, allowed backlogs, eligible branches) for a company."""
    return get_eligibility(company_name)


@tool
def tool_selection_process(company_name: str) -> dict:
    """Retrieve ordered recruitment rounds and selection process stages for a company."""
    return get_selection_process(company_name)


@tool
def tool_search_questions(
    company_name: str = "",
    category: str = "",
    topic: str = "",
    question_type: str = "",
    search: str = "",
    limit: int = 5,
) -> dict:
    """Search the Question Bank in PostgreSQL for practice, PYQ, or candidate-reported questions."""
    return search_questions(
        company_name=company_name,
        category=category,
        topic=topic,
        question_type=question_type,
        search=search,
        limit=limit,
    )


@tool
def tool_student_performance(student_identifier: str) -> dict:
    """Retrieve a student's mock test scores, category accuracy, and weakest topics by roll number or name."""
    return get_student_performance(student_identifier)


@tool
def tool_search_recruitment_docs(
    query: str,
    company_name: str = "",
    top_k: int = 4,
) -> dict:
    """Search official recruitment PDFs, brochures, KIIT notices, and company notes (RAG)."""
    return search_recruitment_docs(query=query, company_name=company_name or None, top_k=top_k)


AGENT_TOOLS = [
    tool_list_companies,
    tool_company_details,
    tool_eligibility,
    tool_selection_process,
    tool_search_questions,
    tool_student_performance,
    tool_search_recruitment_docs,
]


# ============================================================================
# Gemini LLM & LangGraph Compilation
# ============================================================================

def is_gemini_configured() -> bool:
    load_dotenv(override=True)
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    # Google AI Studio Gemini API keys always start with AIzaSy.
    # Non-AIzaSy strings cause google.auth to query the 169.254.169.254 metadata server and hang on Windows.
    return bool(api_key and api_key != "your_gemini_api_key_here" and api_key.startswith("AIzaSy"))


def get_llm():
    """Initialize Google Gemini LLM when GEMINI_API_KEY is configured."""
    if not is_gemini_configured():
        return None

    from langchain_google_genai import ChatGoogleGenerativeAI

    load_dotenv(override=True)
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    model_name = os.getenv("GEMINI_MODEL", "gemini-1.5-flash").strip() or "gemini-1.5-flash"
    return ChatGoogleGenerativeAI(
        model=model_name,
        google_api_key=api_key,
        temperature=0.2,
        timeout=10,
        max_retries=1,
    )


def create_placement_graph():
    """Compile and return the LangGraph ReAct agent graph."""
    llm = get_llm()
    if llm is None:
        return None

    return create_react_agent(
        model=llm,
        tools=AGENT_TOOLS,
        messages_modifier=get_placement_system_prompt(),
    )


def _extract_text_content(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict) and "text" in item:
                parts.append(str(item["text"]))
            else:
                parts.append(str(item))
        return "\n".join(parts).strip()
    return str(content)


# ============================================================================
# Deterministic Database + RAG Fallback (Active when GEMINI_API_KEY is unset)
# ============================================================================

def _detect_company_in_text(query: str, explicit_company: Optional[str] = None) -> Optional[str]:
    if explicit_company and explicit_company.strip():
        return explicit_company.strip()

    q_lower = query.lower()

    # Check known aliases first
    for alias, target in COMPANY_ALIASES.items():
        if re.search(rf"\b{re.escape(alias)}\b", q_lower):
            return target

    # Match against live companies in PostgreSQL (longest name first)
    all_comps = list_all_companies().get("companies", [])
    names = sorted([c["name"] for c in all_comps], key=len, reverse=True)
    for name in names:
        if re.search(rf"\b{re.escape(name.lower())}\b", q_lower):
            return name
    return None


def _detect_roll_or_student(query: str, explicit_student: Optional[str] = None) -> Optional[str]:
    if explicit_student and explicit_student.strip():
        return explicit_student.strip()
    # Common KIIT roll number pattern (7-10 digits)
    match = re.search(r"\b\d{6,10}\b", query)
    if match:
        return match.group(0)
    return None


def _run_local_tool_agent(
    user_query: str,
    student_identifier: Optional[str] = None,
    company_name: Optional[str] = None,
    fallback_reason: Optional[str] = None,
) -> dict:
    """
    Deterministic DB + RAG router so the assistant always returns grounded answers
    from PostgreSQL and indexed company documents even before GEMINI_API_KEY is set.
    """
    q_lower = user_query.lower()
    tools_used: List[str] = []
    sources: List[str] = []
    sections: List[str] = []

    detected_company = _detect_company_in_text(user_query, explicit_company=company_name)
    detected_student = _detect_roll_or_student(user_query, explicit_student=student_identifier)

    wants_list = any(kw in q_lower for kw in ["list compan", "which compan", "all compan", "supported compan"])
    wants_perf = any(
        kw in q_lower
        for kw in ["performance", "score", "accuracy", "weak", "progress", "my mock", "attempt"]
    )
    wants_questions = any(
        kw in q_lower
        for kw in ["question", "pyq", "reported", "practice", "coding problem", "mcq", "sample problem"]
    )
    wants_elig = any(
        kw in q_lower
        for kw in ["eligib", "cgpa", "cutoff", "backlog", "branch", "criteria", "arrear", "percentage"]
    )
    wants_rounds = any(
        kw in q_lower
        for kw in ["round", "selection", "process", "stage", "interview", "hiring steps"]
    )
    wants_docs = any(
        kw in q_lower
        for kw in [
            "ctc", "package", "salary", "lpa", "stipend", "pattern", "syllabus",
            "duration", "minute", "deadline", "date", "apply", "nextstep", "bond",
            "brochure", "notice", "role", "track", "prime", "digital", "ninja", "genc",
        ]
    )

    # 1. Performance tracking queries
    if wants_perf:
        if detected_student:
            tools_used.append("tool_student_performance")
            perf = get_student_performance(detected_student)
            if "error" in perf:
                sections.append(f"**Performance Lookup:** {perf['error']}")
            else:
                lines = [
                    f"### Performance Summary for {perf['student_name']}"
                    + (f" (`{perf['student_roll_number']}`)" if perf.get("student_roll_number") else ""),
                    f"- **Completed Attempts:** {perf['completed_attempts']} (Total started: {perf['total_attempts']})",
                    f"- **Average Score:** {perf['average_score_percentage']}% | **Best Score:** {perf['best_score_percentage']}%",
                ]
                if perf.get("category_accuracy"):
                    lines.append("- **Category Accuracy:**")
                    for cat in perf["category_accuracy"]:
                        lines.append(
                            f"  - {cat['category']}: {cat['correct']}/{cat['attempted']} ({cat['accuracy_percentage']}%)"
                        )
                if perf.get("weakest_topics"):
                    lines.append("- **Topics Needing Focus (Lowest Accuracy First):**")
                    for wt in perf["weakest_topics"]:
                        lines.append(
                            f"  - {wt['topic']} ({wt['category']}): {wt['accuracy_percentage']}% ({wt['correct']}/{wt['attempted']})"
                        )
                sections.append("\n".join(lines))
        else:
            sections.append(
                "**Performance Lookup:** Please include your roll number or student name (or fill in `student_identifier`) so I can check your mock test history."
            )

    # 2. Company list query
    if wants_list and not detected_company:
        tools_used.append("tool_list_companies")
        comp_data = list_all_companies()
        comps = comp_data.get("companies", [])
        with_elig = [c["name"] for c in comps if c["has_eligibility"]]
        qbank_only = [c["name"] for c in comps if not c["has_eligibility"]]
        sections.append(
            "### Registered Companies in Database\n"
            f"- **Verified Placement Criteria & Rounds ({len(with_elig)}):** {', '.join(with_elig)}\n"
            f"- **Question Bank Coverage ({len(qbank_only)}):** {', '.join(qbank_only)}"
        )

    # 3. Question Bank search
    if wants_questions:
        cat_filter = ""
        for cat_candidate in ["Aptitude", "Coding", "Technical", "Reasoning", "Verbal"]:
            if cat_candidate.lower() in q_lower:
                cat_filter = cat_candidate
                break
        qtype_filter = ""
        for qt in ["REPORTED", "PYQ", "PRACTICE"]:
            if qt.lower() in q_lower:
                qtype_filter = qt
                break

        tools_used.append("tool_search_questions")
        q_res = search_questions(
            company_name=detected_company or "",
            category=cat_filter,
            question_type=qtype_filter,
            limit=5,
        )
        qs = q_res.get("questions", [])
        if qs:
            q_lines = [
                f"### Question Bank Matches (showing {len(qs)} of {q_res.get('total_matching', len(qs))})"
            ]
            for item in qs:
                q_lines.append(
                    f"- **[{item['question_type']}]** ({item['company']} | {item['category']} - {item['topic'] or 'General'}): "
                    f"{item['question_text']}\n  *Source: {item['source'] or 'Internal'}*"
                )
            sections.append("\n".join(q_lines))
        else:
            sections.append(
                f"**Question Bank:** No matching questions found for company=`{detected_company or 'Any'}`, category=`{cat_filter or 'Any'}`."
            )

    # 4. Company structured details + eligibility + rounds + RAG documents
    if detected_company and not (wants_questions and not (wants_elig or wants_rounds or wants_docs)):
        tools_used.append("tool_company_details")
        comp_details = get_company_details(detected_company)
        if "error" in comp_details:
            sections.append(f"**Company Lookup:** {comp_details['error']}")
        else:
            canon_name = comp_details["name"]
            if not wants_elig and not wants_rounds and not wants_docs and not wants_questions:
                # General company inquiry: show overview + eligibility + rounds + top RAG docs
                wants_elig = True
                wants_rounds = True
                wants_docs = True

            header_lines = [f"### {canon_name}"]
            if comp_details.get("industry"):
                header_lines.append(f"- **Industry:** {comp_details['industry']}")
            if comp_details.get("description"):
                header_lines.append(f"- **Overview:** {comp_details['description']}")
            sections.append("\n".join(header_lines))

            if wants_elig:
                tools_used.append("tool_eligibility")
                elig = get_eligibility(canon_name)
                if "error" in elig:
                    sections.append(
                        f"**Eligibility Criteria:** Not currently available in the platform database for {canon_name} "
                        "(registered from Question Bank without invented cutoffs)."
                    )
                else:
                    sections.append(
                        f"**Eligibility Criteria ({canon_name}):**\n"
                        f"- **CGPA Cutoff:** {elig['cgpa_cutoff']}\n"
                        f"- **Max Active Backlogs Allowed:** {elig['backlogs_allowed']}\n"
                        f"- **Eligible Branches:** {elig['branches']}\n"
                        + (f"- **Notes:** {elig['additional_notes']}" if elig.get("additional_notes") else "")
                    )

            if wants_rounds:
                tools_used.append("tool_selection_process")
                proc = get_selection_process(canon_name)
                if "error" in proc:
                    sections.append(
                        f"**Selection Process:** Not currently stored in the platform database for {canon_name}."
                    )
                else:
                    r_lines = [f"**Selection Rounds ({canon_name}):**"]
                    for r in proc["round_details"]:
                        r_lines.append(f"{r['round_number']}. **{r['round_name']}** — {r['description'] or ''}")
                    sections.append("\n".join(r_lines))

            if wants_docs or wants_elig or wants_rounds:
                tools_used.append("tool_search_recruitment_docs")
                rag_res = search_recruitment_docs(
                    query=user_query,
                    company_name=canon_name,
                    top_k=3,
                )
                for chunk in rag_res.get("results", []):
                    page_note = f" (p.{chunk['page']})" if chunk.get("page") else ""
                    sources.append(f"{chunk['relative_path']}{page_note}")
                if wants_docs and rag_res.get("results"):
                    doc_lines = [f"**Relevant Recruitment Document Excerpts ({canon_name}):**"]
                    for chunk in rag_res["results"][:3]:
                        doc_lines.append(f"- *{chunk['source_file']}:* {chunk['content']}")
                    sections.append("\n".join(doc_lines))

    elif not sections:
        # Unmatched general query: try RAG across all company documents
        tools_used.append("tool_search_recruitment_docs")
        rag_res = search_recruitment_docs(query=user_query, company_name=None, top_k=3)
        hits = rag_res.get("results", [])
        if hits:
            doc_lines = ["### Relevant Information from Recruitment Documents"]
            for chunk in hits:
                page_note = f" (p.{chunk['page']})" if chunk.get("page") else ""
                src = f"{chunk['relative_path']}{page_note}"
                sources.append(src)
                doc_lines.append(f"- **[{chunk['company']} — {chunk['source_file']}]** {chunk['content']}")
            sections.append("\n".join(doc_lines))
        else:
            sections.append(
                "I can help with **company eligibility & selection rounds** (e.g., TCS, IBM, Cognizant, Accenture, Deloitte, HighRadius, Tech Mahindra), "
                "**Question Bank practice** across 22 companies, **recruitment document details** (CTC, test pattern, deadlines), "
                "and **your mock test performance analytics** (using your roll number or name)."
            )

    footer = (
        "\n\n---\n*Mode: Database + Document RAG Fallback*"
        + (f" ({fallback_reason})" if fallback_reason else " (Add a valid `GEMINI_API_KEY` in `.env` to enable full Gemini AI synthesis.)")
    )

    return {
        "response": "\n\n".join(sections) + footer,
        "mode": "database_rag_fallback",
        "tools_used": list(dict.fromkeys(tools_used)),
        "sources": list(dict.fromkeys(sources)),
    }


# ============================================================================
# Unified Entry Point
# ============================================================================

def run_placement_agent(
    user_query: str,
    student_identifier: Optional[str] = None,
    company_name: Optional[str] = None,
    history: Optional[List[dict]] = None,
) -> dict:
    """
    Execute the Placement Preparation Agent for a student query.
    Uses LangGraph + Gemini when GEMINI_API_KEY is configured, and cleanly
    falls back to grounded Database + RAG execution when offline/unconfigured.
    """
    if not is_gemini_configured():
        return _run_local_tool_agent(
            user_query=user_query,
            student_identifier=student_identifier,
            company_name=company_name,
        )

    agent_graph = create_placement_graph()
    if agent_graph is None:
        return _run_local_tool_agent(
            user_query=user_query,
            student_identifier=student_identifier,
            company_name=company_name,
            fallback_reason="Gemini graph initialization returned None",
        )

    # Build message list cleanly with optional context hints
    messages: List[tuple] = []
    for turn in (history or [])[-6:]:
        role = turn.get("role", "user")
        content = (turn.get("content") or "").strip()
        if content and role in {"user", "assistant"}:
            messages.append((role, content))

    context_hints = []
    if company_name and company_name.strip():
        context_hints.append(f"Selected company context: {company_name.strip()}")
    if student_identifier and student_identifier.strip():
        context_hints.append(f"Student identifier (roll/name): {student_identifier.strip()}")

    enriched_query = user_query
    if context_hints:
        enriched_query = f"[{'; '.join(context_hints)}]\n\n{user_query}"
    messages.append(("user", enriched_query))

    try:
        result = agent_graph.invoke({"messages": messages})
        out_messages = result.get("messages", [])
        tools_used: List[str] = []
        for msg in out_messages:
            if getattr(msg, "type", "") == "tool":
                t_name = getattr(msg, "name", None)
                if t_name and t_name not in tools_used:
                    tools_used.append(t_name)

        final_text = (
            _extract_text_content(out_messages[-1].content)
            if out_messages
            else "No response generated by the agent."
        )
        return {
            "response": final_text,
            "mode": "langgraph_gemini",
            "tools_used": tools_used,
            "sources": [],
        }
    except Exception as exc:
        return _run_local_tool_agent(
            user_query=user_query,
            student_identifier=student_identifier,
            company_name=company_name,
            fallback_reason=f"Gemini API call failed ({type(exc).__name__}); answered using verified Database & RAG tools",
        )
