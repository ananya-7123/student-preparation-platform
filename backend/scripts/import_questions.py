"""
Idempotent importer for Ruptanu's MASTER_QUESTION_INDEX.csv and additional PRACTICE MCQs.

Usage:
    .\venv\Scripts\python backend/scripts/import_questions.py           # Run live import into PostgreSQL
    .\venv\Scripts\python backend/scripts/import_questions.py --dry-run # Validate CSV + MCQs without DB writes
"""

import argparse
import csv
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from sqlalchemy import func, text
from sqlalchemy.exc import SQLAlchemyError

# Ensure "backend/" is on sys.path whether executed directly or via module path
BACKEND_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.database import SessionLocal  # noqa: E402
from app.models import Company, Question  # noqa: E402
from app.schemas import QuestionCreate  # noqa: E402

CSV_PATH = PROJECT_ROOT / "question_bank" / "MASTER_QUESTION_INDEX.csv"
COMMON_COMPANY_LABEL = "Common / Multiple companies"

# 20 clearly labelled PRACTICE MCQs so mock tests have sufficient MCQs per category
PRACTICE_MCQS: List[dict] = [
    # ---- Aptitude (+5 -> 8 total Aptitude MCQs) ----
    {
        "company_name": None,
        "category": "Aptitude",
        "topic": "Profit & Loss",
        "difficulty": "Easy",
        "question_type": "PRACTICE",
        "source": "Internal Practice Question Bank",
        "question_text": "A shopkeeper buys an article for Rs. 800 and sells it for Rs. 920. What is his profit percentage?",
        "option_a": "12%",
        "option_b": "15%",
        "option_c": "18%",
        "option_d": "20%",
        "correct_option": "B",
        "explanation": "Profit = 920 - 800 = Rs. 120. Profit percentage = (120 / 800) * 100 = 15%.",
    },
    {
        "company_name": "TCS",
        "category": "Aptitude",
        "topic": "Time Speed & Distance",
        "difficulty": "Medium",
        "question_type": "PRACTICE",
        "source": "Internal Practice Question Bank",
        "question_text": "A train 180 meters long crosses a telegraph pole in 12 seconds. What is the speed of the train in km/hr?",
        "option_a": "48 km/hr",
        "option_b": "52 km/hr",
        "option_c": "54 km/hr",
        "option_d": "60 km/hr",
        "correct_option": "C",
        "explanation": "Speed = 180 / 12 = 15 m/s. Converting to km/hr: 15 * (18 / 5) = 54 km/hr.",
    },
    {
        "company_name": "Accenture",
        "category": "Aptitude",
        "topic": "Ratio & Proportion",
        "difficulty": "Easy",
        "question_type": "PRACTICE",
        "source": "Internal Practice Question Bank",
        "question_text": "If A : B = 2 : 3 and B : C = 4 : 5, what is the combined ratio A : B : C?",
        "option_a": "8 : 12 : 15",
        "option_b": "6 : 12 : 15",
        "option_c": "8 : 10 : 15",
        "option_d": "4 : 6 : 5",
        "correct_option": "A",
        "explanation": "Make the common term B equal: A:B = 8:12 and B:C = 12:15, so A:B:C = 8:12:15.",
    },
    {
        "company_name": "Infosys",
        "category": "Aptitude",
        "topic": "Permutations & Combinations",
        "difficulty": "Medium",
        "question_type": "PRACTICE",
        "source": "Internal Practice Question Bank",
        "question_text": "In how many distinct ways can the letters of the word 'APPLE' be arranged?",
        "option_a": "120",
        "option_b": "60",
        "option_c": "24",
        "option_d": "30",
        "correct_option": "B",
        "explanation": "There are 5 letters in 'APPLE' with 'P' repeated twice: 5! / 2! = 120 / 2 = 60 ways.",
    },
    {
        "company_name": "IBM",
        "category": "Aptitude",
        "topic": "Averages & Mixtures",
        "difficulty": "Hard",
        "question_type": "PRACTICE",
        "source": "Internal Practice Question Bank",
        "question_text": "The average weight of 8 persons increases by 2.5 kg when a new person replaces one of them weighing 65 kg. What is the weight of the new person?",
        "option_a": "75 kg",
        "option_b": "80 kg",
        "option_c": "85 kg",
        "option_d": "90 kg",
        "correct_option": "C",
        "explanation": "Total weight increase = 8 * 2.5 = 20 kg. Weight of the new person = 65 + 20 = 85 kg.",
    },
    # ---- Reasoning (+4 -> 6 total Reasoning MCQs) ----
    {
        "company_name": None,
        "category": "Reasoning",
        "topic": "Coding-Decoding",
        "difficulty": "Easy",
        "question_type": "PRACTICE",
        "source": "Internal Practice Question Bank",
        "question_text": "In a certain code language, 'CAT' is written as 'DBU'. How will 'DOG' be written in that code?",
        "option_a": "EPH",
        "option_b": "DPH",
        "option_c": "EOG",
        "option_d": "EPI",
        "correct_option": "A",
        "explanation": "Each letter shifts forward by 1 position in the alphabet: D->E, O->P, G->H, giving 'EPH'.",
    },
    {
        "company_name": "Capgemini",
        "category": "Reasoning",
        "topic": "Syllogisms",
        "difficulty": "Medium",
        "question_type": "PRACTICE",
        "source": "Internal Practice Question Bank",
        "question_text": "Statements: All laptops are computers. Some computers are tablets. Which conclusion(s) necessarily follow? I. Some laptops are tablets. II. Some tablets are computers.",
        "option_a": "Only I follows",
        "option_b": "Only II follows",
        "option_c": "Both I and II follow",
        "option_d": "Neither I nor II follows",
        "correct_option": "B",
        "explanation": "'Some computers are tablets' directly implies its converse 'Some tablets are computers' (II). Laptops and tablets do not necessarily overlap (I does not follow).",
    },
    {
        "company_name": "TCS",
        "category": "Reasoning",
        "topic": "Direction Sense",
        "difficulty": "Easy",
        "question_type": "PRACTICE",
        "source": "Internal Practice Question Bank",
        "question_text": "Ravi walks 10 meters North, turns right and walks 15 meters, and then turns right and walks 10 meters. How far and in which direction is he from his starting point?",
        "option_a": "15 meters North",
        "option_b": "15 meters West",
        "option_c": "15 meters East",
        "option_d": "25 meters East",
        "correct_option": "C",
        "explanation": "North 10 m, then East 15 m, then South 10 m cancels the vertical displacement, leaving him 15 meters East of the start.",
    },
    {
        "company_name": "Deloitte",
        "category": "Reasoning",
        "topic": "Seating Arrangement",
        "difficulty": "Hard",
        "question_type": "PRACTICE",
        "source": "Internal Practice Question Bank",
        "question_text": "Five friends P, Q, R, S, and T are sitting in a row facing North. T is at an extreme end. P sits immediately to the right of T. Q sits between P and R. Who sits at the other extreme end?",
        "option_a": "Q",
        "option_b": "R",
        "option_c": "P",
        "option_d": "S",
        "correct_option": "D",
        "explanation": "Since P is immediately right of T (facing North), T must be at the left end. Order from left to right is T, P, Q, R, S; thus S sits at the other extreme end.",
    },
    # ---- Verbal (+5 -> 6 total Verbal MCQs) ----
    {
        "company_name": None,
        "category": "Verbal",
        "topic": "Vocabulary",
        "difficulty": "Easy",
        "question_type": "PRACTICE",
        "source": "Internal Practice Question Bank",
        "question_text": "Choose the word closest in meaning (synonym) to 'CONCISE':",
        "option_a": "Lengthy",
        "option_b": "Brief",
        "option_c": "Vague",
        "option_d": "Complex",
        "correct_option": "B",
        "explanation": "'Concise' means expressing much in few words; clear and brief.",
    },
    {
        "company_name": "Accenture",
        "category": "Verbal",
        "topic": "Grammar & Error Spotting",
        "difficulty": "Medium",
        "question_type": "PRACTICE",
        "source": "Internal Practice Question Bank",
        "question_text": "Identify the part of the sentence that contains a grammatical error: \"One of my friends (A) / are planning to join (B) / the upcoming placement workshop tomorrow. (C) / No error (D)\"",
        "option_a": "One of my friends",
        "option_b": "are planning to join",
        "option_c": "the upcoming placement workshop tomorrow.",
        "option_d": "No error",
        "correct_option": "B",
        "explanation": "The subject 'One' is singular, so it takes the singular verb 'is planning to join' instead of 'are planning to join'.",
    },
    {
        "company_name": "Cognizant",
        "category": "Verbal",
        "topic": "Grammar & Prepositions",
        "difficulty": "Easy",
        "question_type": "PRACTICE",
        "source": "Internal Practice Question Bank",
        "question_text": "Fill in the blank with the most appropriate option: \"The software team succeeded ____ deploying the patch before midnight.\"",
        "option_a": "on",
        "option_b": "at",
        "option_c": "in",
        "option_d": "with",
        "correct_option": "C",
        "explanation": "The verb 'succeed' pairs with the preposition 'in' followed by a gerund ('succeeded in deploying').",
    },
    {
        "company_name": "HighRadius",
        "category": "Verbal",
        "topic": "Sentence Ordering",
        "difficulty": "Medium",
        "question_type": "PRACTICE",
        "source": "Internal Practice Question Bank",
        "question_text": "Arrange parts P, Q, R, S to complete the sentence coherently: \"To prepare effectively for technical interviews, (P) focus on core concepts / (Q) rather than memorizing / (R) and problem-solving patterns / (S) isolated code snippets.\"",
        "option_a": "P R Q S",
        "option_b": "Q S P R",
        "option_c": "P Q R S",
        "option_d": "R P Q S",
        "correct_option": "A",
        "explanation": "The coherent order is: 'focus on core concepts (P) and problem-solving patterns (R) rather than memorizing (Q) isolated code snippets (S).'",
    },
    {
        "company_name": "Wipro",
        "category": "Verbal",
        "topic": "Active & Passive Voice",
        "difficulty": "Medium",
        "question_type": "PRACTICE",
        "source": "Internal Practice Question Bank",
        "question_text": "Choose the correct passive voice form of the sentence: \"The interviewer asked the candidate two coding questions.\"",
        "option_a": "The candidate is asked two coding questions by the interviewer.",
        "option_b": "The candidate was asked two coding questions by the interviewer.",
        "option_c": "The candidate was being asked two coding questions by the interviewer.",
        "option_d": "The candidate had been asked two coding questions by the interviewer.",
        "correct_option": "B",
        "explanation": "The active sentence is in simple past tense ('asked'), which converts to 'was asked' in passive voice.",
    },
    # ---- Technical (+6 -> 9 total Technical MCQs) ----
    {
        "company_name": "TCS",
        "category": "Technical",
        "topic": "SQL DBMS",
        "difficulty": "Medium",
        "question_type": "PRACTICE",
        "source": "Internal Practice Question Bank",
        "question_text": "In SQL, which clause is specifically used to filter groups created by a GROUP BY clause based on aggregate conditions?",
        "option_a": "WHERE",
        "option_b": "HAVING",
        "option_c": "ORDER BY",
        "option_d": "DISTINCT",
        "correct_option": "B",
        "explanation": "HAVING filters grouped rows after GROUP BY using aggregate conditions, whereas WHERE filters individual rows before grouping.",
    },
    {
        "company_name": "Infosys",
        "category": "Technical",
        "topic": "Programming OOP",
        "difficulty": "Easy",
        "question_type": "PRACTICE",
        "source": "Internal Practice Question Bank",
        "question_text": "Which object-oriented programming concept allows a subclass to provide a specific implementation of a method already defined in its parent class?",
        "option_a": "Method Overloading",
        "option_b": "Encapsulation",
        "option_c": "Method Overriding",
        "option_d": "Abstraction",
        "correct_option": "C",
        "explanation": "Method overriding lets a child class redefine an inherited method with the same signature to customize runtime behavior.",
    },
    {
        "company_name": "Tech Mahindra",
        "category": "Technical",
        "topic": "Computer Networks",
        "difficulty": "Medium",
        "question_type": "PRACTICE",
        "source": "Internal Practice Question Bank",
        "question_text": "Which protocol operates at the Transport Layer and provides connection-oriented, reliable, ordered delivery of data?",
        "option_a": "UDP",
        "option_b": "IP",
        "option_c": "HTTP",
        "option_d": "TCP",
        "correct_option": "D",
        "explanation": "TCP (Transmission Control Protocol) provides connection-oriented, reliable, in-order byte-stream delivery at the Transport Layer.",
    },
    {
        "company_name": None,
        "category": "Technical",
        "topic": "Algorithms",
        "difficulty": "Easy",
        "question_type": "PRACTICE",
        "source": "Internal Practice Question Bank",
        "question_text": "What is the worst-case time complexity of Binary Search on a sorted array of n elements?",
        "option_a": "O(1)",
        "option_b": "O(log n)",
        "option_c": "O(n)",
        "option_d": "O(n log n)",
        "correct_option": "B",
        "explanation": "Binary search halves the remaining search interval at each comparison, resulting in O(log n) worst-case time complexity.",
    },
    {
        "company_name": "IBM",
        "category": "Technical",
        "topic": "Data Structures",
        "difficulty": "Medium",
        "question_type": "PRACTICE",
        "source": "Internal Practice Question Bank",
        "question_text": "Which data structure is primarily used to perform a Breadth-First Search (BFS) traversal on a graph?",
        "option_a": "Stack",
        "option_b": "Queue",
        "option_c": "Binary Search Tree",
        "option_d": "Priority Heap",
        "correct_option": "B",
        "explanation": "BFS visits vertices level-by-level in FIFO order, which is managed using a Queue.",
    },
    {
        "company_name": "Deloitte",
        "category": "Technical",
        "topic": "Programming OOP",
        "difficulty": "Hard",
        "question_type": "PRACTICE",
        "source": "Internal Practice Question Bank",
        "question_text": "In Python, what is the output of: list(map(lambda x: x * 2, filter(lambda x: x % 2 == 1, [1, 2, 3, 4, 5])))?",
        "option_a": "[2, 6, 10]",
        "option_b": "[4, 8]",
        "option_c": "[1, 3, 5]",
        "option_d": "[2, 4, 6, 8, 10]",
        "correct_option": "A",
        "explanation": "filter keeps odd integers [1, 3, 5], and map doubles each element to produce [2, 6, 10].",
    },
]


def load_csv_questions(csv_path: Path) -> List[dict]:
    """Read and validate rows from MASTER_QUESTION_INDEX.csv using UTF-8 BOM handling."""
    if not csv_path.exists():
        raise FileNotFoundError(f"Question bank CSV not found at: {csv_path}")

    parsed_rows: List[dict] = []
    with csv_path.open("r", encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        for idx, row in enumerate(reader, start=2):
            company_raw = (row.get("Company") or "").strip()
            section = (row.get("Section") or "").strip()
            topic = (row.get("Topic") or "").strip()
            question_text = (row.get("Question") or "").strip()
            source = (row.get("Source") or "").strip() or None
            question_status = (row.get("Question status") or "").strip()

            if not question_text or not section:
                raise ValueError(f"Missing required Section/Question at CSV line {idx}.")

            company_name = None if company_raw == COMMON_COMPANY_LABEL else company_raw

            # Validate payload against Pydantic QuestionCreate schema
            validated = QuestionCreate(
                company_id=None,
                category=section,
                topic=topic or None,
                difficulty="Medium",
                question_type=question_status,
                year=None,
                source=source,
                question_text=question_text,
                option_a=None,
                option_b=None,
                option_c=None,
                option_d=None,
                correct_option=None,
                explanation=None,
            )

            parsed_rows.append(
                {
                    "company_name": company_name,
                    "schema": validated,
                }
            )

    return parsed_rows


def validate_practice_mcqs(mcqs: List[dict]) -> List[dict]:
    """Validate all practice MCQ dictionaries against QuestionCreate schema."""
    validated_mcqs: List[dict] = []
    for idx, item in enumerate(mcqs, start=1):
        validated = QuestionCreate(
            company_id=None,
            category=item["category"],
            topic=item["topic"],
            difficulty=item["difficulty"],
            question_type=item["question_type"],
            year=None,
            source=item["source"],
            question_text=item["question_text"],
            option_a=item["option_a"],
            option_b=item["option_b"],
            option_c=item["option_c"],
            option_d=item["option_d"],
            correct_option=item["correct_option"],
            explanation=item["explanation"],
        )
        if not all([validated.option_a, validated.option_b, validated.option_c, validated.option_d, validated.correct_option]):
            raise ValueError(f"Practice MCQ #{idx} is missing options or correct_option.")
        validated_mcqs.append({"company_name": item["company_name"], "schema": validated})
    return validated_mcqs


def check_live_schema_compatibility(db) -> None:
    """
    Verify that database/migrations/001_update_questions_table.sql has been applied
    (questions.source is TEXT and question_type allows REPORTED/PRACTICE).
    """
    source_type = db.execute(
        text(
            """
            SELECT data_type
            FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name = 'questions'
              AND column_name = 'source'
            """
        )
    ).scalar()

    if source_type != "text":
        raise RuntimeError(
            "Schema mismatch: questions.source is "
            f"'{source_type}' instead of 'text'. "
            "Please run database/migrations/001_update_questions_table.sql in pgAdmin 4 first."
        )

    constraint_defs = db.execute(
        text(
            """
            SELECT pg_get_constraintdef(oid)
            FROM pg_constraint
            WHERE conrelid = 'questions'::regclass
              AND contype = 'c'
              AND pg_get_constraintdef(oid) ILIKE '%question_type%'
            """
        )
    ).scalars().all()

    if not any("REPORTED" in c and "PRACTICE" in c for c in constraint_defs):
        raise RuntimeError(
            "Schema mismatch: questions.question_type CHECK constraint does not yet allow 'PRACTICE' and 'REPORTED'. "
            "Please run database/migrations/001_update_questions_table.sql in pgAdmin 4 first."
        )


def run_import(dry_run: bool = False) -> None:
    csv_records = load_csv_questions(CSV_PATH)
    mcq_records = validate_practice_mcqs(PRACTICE_MCQS)

    csv_companies = sorted({r["company_name"] for r in csv_records if r["company_name"]})
    mcq_companies = sorted({r["company_name"] for r in mcq_records if r["company_name"]})

    if dry_run:
        print("=== DRY RUN MODE (No database connection or writes) ===")
        print(f"CSV file              : {CSV_PATH}")
        print(f"CSV rows validated    : {len(csv_records)}")
        print(f"Distinct CSV companies: {len(csv_companies)} -> {csv_companies}")
        print(f"Extra PRACTICE MCQs   : {len(mcq_records)} (companies referenced: {mcq_companies})")
        return

    db = SessionLocal()
    try:
        check_live_schema_compatibility(db)

        # 1. Load existing companies (case-insensitive map)
        existing_companies = db.query(Company).all()
        company_map: Dict[str, Company] = {c.name.strip().lower(): c for c in existing_companies}

        # 2. Register missing companies found in CSV (without inventing eligibility or rounds)
        newly_registered_companies: List[str] = []
        for comp_name in sorted(set(csv_companies) | set(mcq_companies)):
            key = comp_name.strip().lower()
            if key not in company_map:
                new_company = Company(name=comp_name, industry=None, description=None)
                db.add(new_company)
                db.flush()  # Populate new_company.id immediately
                company_map[key] = new_company
                newly_registered_companies.append(comp_name)

        # 3. Track existing (company_id, question_text) pairs to keep script idempotent
        existing_pairs: set[Tuple[Optional[int], str]] = {
            (row.company_id, row.question_text.strip())
            for row in db.query(Question.company_id, Question.question_text).all()
        }

        def insert_batch(records: List[dict]) -> Tuple[int, int]:
            inserted = 0
            skipped = 0
            for item in records:
                comp_name = item["company_name"]
                company_id = company_map[comp_name.strip().lower()].id if comp_name else None
                q = item["schema"]
                dedup_key = (company_id, q.question_text.strip())
                if dedup_key in existing_pairs:
                    skipped += 1
                    continue

                db_q = Question(
                    company_id=company_id,
                    category=q.category,
                    topic=q.topic,
                    difficulty=q.difficulty,
                    question_type=q.question_type,
                    year=q.year,
                    source=q.source,
                    question_text=q.question_text,
                    option_a=q.option_a,
                    option_b=q.option_b,
                    option_c=q.option_c,
                    option_d=q.option_d,
                    correct_option=q.correct_option,
                    explanation=q.explanation,
                )
                db.add(db_q)
                existing_pairs.add(dedup_key)
                inserted += 1
            return inserted, skipped

        csv_inserted, csv_skipped = insert_batch(csv_records)
        mcq_inserted, mcq_skipped = insert_batch(mcq_records)

        db.commit()

        # 4. Print final database verification counts
        total_companies = db.query(func.count(Company.id)).scalar()
        total_questions = db.query(func.count(Question.id)).scalar()
        total_mcqs = (
            db.query(func.count(Question.id))
            .filter(Question.correct_option.isnot(None))
            .scalar()
        )
        type_counts = dict(
            db.query(Question.question_type, func.count(Question.id))
            .group_by(Question.question_type)
            .order_by(Question.question_type)
            .all()
        )

        print("=== Import Completed Successfully ===")
        print(f"Newly registered companies ({len(newly_registered_companies)}): {newly_registered_companies}")
        print(f"CSV questions   -> inserted: {csv_inserted}, skipped (already present): {csv_skipped}")
        print(f"Practice MCQs   -> inserted: {mcq_inserted}, skipped (already present): {mcq_skipped}")
        print(f"Database totals -> companies: {total_companies} | questions: {total_questions} | valid MCQs: {total_mcqs}")
        print(f"By question_type -> {type_counts}")

    except (SQLAlchemyError, RuntimeError, ValueError, FileNotFoundError) as exc:
        db.rollback()
        print(f"[ERROR] Import aborted: {exc}", file=sys.stderr)
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Import Question Bank CSV and Practice MCQs into PostgreSQL.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse and validate CSV + MCQs locally without writing to PostgreSQL.",
    )
    args = parser.parse_args()
    run_import(dry_run=args.dry_run)

