import os
import sys
import unittest
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Ensure `backend` is importable regardless of where tests are invoked from
PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = PROJECT_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

# Force in-memory database for isolated offline testing
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ.setdefault("GEMINI_API_KEY", "your_gemini_api_key_here")

import app.main as main_module
import app.agent.tools as agent_tools
import app.auth_utils as auth_utils_module
from app.database import Base, get_db
from app.models import (
    Company,
    EligibilityCriteria,
    Question,
    SelectionRound,
)


class StudentPrepPlatformAPITests(unittest.TestCase):
    """End-to-end API & RAG test suite using an isolated in-memory SQLite database."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        cls.TestingSessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=cls.engine,
        )
        Base.metadata.create_all(bind=cls.engine)
        cls._seed_test_data()

        cls._orig_ensure_auth = main_module.ensure_auth_schema
        cls._orig_tools_session = agent_tools.SessionLocal
        main_module.ensure_auth_schema = lambda: None
        import app.auth_utils as auth_utils_module
        auth_utils_module.ensure_auth_schema = lambda: None
        agent_tools.SessionLocal = cls.TestingSessionLocal

        def override_get_db():
            db = cls.TestingSessionLocal()
            try:
                yield db
            finally:
                db.close()

        main_module.app.dependency_overrides[get_db] = override_get_db
        cls.client = TestClient(main_module.app)

    @classmethod
    def tearDownClass(cls) -> None:
        main_module.app.dependency_overrides.clear()
        main_module.ensure_auth_schema = cls._orig_ensure_auth
        agent_tools.SessionLocal = cls._orig_tools_session
        cls.engine.dispose()

    @classmethod
    def _seed_test_data(cls) -> None:
        db = cls.TestingSessionLocal()
        try:
            tcs = Company(
                name="TCS",
                description="Tata Consultancy Services campus recruitment via TCS NQT.",
                industry="IT Services",
            )
            amazon = Company(
                name="Amazon",
                description=(
                    "Registered from Ruptanu's Master Question Bank. "
                    "Verified KIIT eligibility and selection rounds are not documented yet."
                ),
                industry="Not Verified (Question Bank Only)",
            )
            db.add_all([tcs, amazon])
            db.flush()

            db.add(
                EligibilityCriteria(
                    company_id=tcs.id,
                    cgpa_cutoff=6.0,
                    backlogs_allowed=1,
                    branches="All B.Tech, B.E., MCA",
                    additional_notes="60% throughout academics.",
                )
            )
            db.add_all(
                [
                    SelectionRound(
                        company_id=tcs.id,
                        round_number=1,
                        round_name="TCS NQT Integrated Test",
                        description="Foundation + Advanced Coding (190 mins)",
                    ),
                    SelectionRound(
                        company_id=tcs.id,
                        round_number=2,
                        round_name="Technical & HR Interview",
                        description="Project + Core CS",
                    ),
                ]
            )

            db.add_all(
                [
                    Question(
                        company_id=tcs.id,
                        category="Aptitude",
                        topic="Percentages",
                        difficulty="Easy",
                        question_type="PYQ",
                        year=2025,
                        source="TCS NQT",
                        question_text="If price increases by 25%, by what percentage must consumption drop?",
                        option_a="20%",
                        option_b="25%",
                        option_c="15%",
                        option_d="10%",
                        correct_option="A",
                        explanation="25 / 125 * 100 = 20%.",
                    ),
                    Question(
                        company_id=tcs.id,
                        category="Aptitude",
                        topic="Probability",
                        difficulty="Medium",
                        question_type="PRACTICE",
                        source="Platform Practice",
                        question_text="Probability of sum 8 when throwing two fair dice?",
                        option_a="5/36",
                        option_b="1/6",
                        option_c="4/36",
                        option_d="7/36",
                        correct_option="A",
                        explanation="5 favorable outcomes out of 36.",
                    ),
                    Question(
                        company_id=None,
                        category="Technical",
                        topic="DBMS",
                        difficulty="Medium",
                        question_type="PRACTICE",
                        source="Common CS Practice",
                        question_text="Which normal form removes transitive dependencies?",
                        option_a="1NF",
                        option_b="2NF",
                        option_c="3NF",
                        option_d="UNF",
                        correct_option="C",
                        explanation="3NF eliminates non-key transitive dependencies.",
                    ),
                    Question(
                        company_id=amazon.id,
                        category="Coding",
                        topic="Arrays",
                        difficulty="Medium",
                        question_type="REPORTED",
                        source="candidate-reported / LeetCode",
                        question_text="Two Sum: Return indices of two numbers adding up to target.",
                        option_a=None,
                        option_b=None,
                        option_c=None,
                        option_d=None,
                        correct_option=None,
                        explanation=None,
                    ),
                ]
            )
            db.commit()
        finally:
            db.close()

    def test_01_root_and_ui_mounted(self) -> None:
        root_res = self.client.get("/")
        self.assertEqual(root_res.status_code, 200)
        self.assertIn("Welcome", root_res.json()["message"])

        ui_res = self.client.get("/ui/")
        self.assertEqual(ui_res.status_code, 200)
        self.assertIn("KIIT PrepAI", ui_res.text)

    def test_02_company_endpoints_and_honest_missing_eligibility(self) -> None:
        list_res = self.client.get("/companies/")
        self.assertEqual(list_res.status_code, 200)
        names = [c["name"] for c in list_res.json()]
        self.assertEqual(names, ["Amazon", "TCS"])

        tcs_elig = self.client.get("/companies/TCS/eligibility")
        self.assertEqual(tcs_elig.status_code, 200)
        self.assertEqual(tcs_elig.json()["cgpa_cutoff"], 6.0)

        tcs_rounds = self.client.get("/companies/TCS/selection-process")
        self.assertEqual(tcs_rounds.status_code, 200)
        self.assertEqual(len(tcs_rounds.json()["rounds"]), 2)

        # Q-Bank-only company must NOT invent eligibility or selection rounds
        amazon_elig = self.client.get("/companies/Amazon/eligibility")
        self.assertEqual(amazon_elig.status_code, 404)
        amazon_rounds = self.client.get("/companies/Amazon/selection-process")
        self.assertEqual(amazon_rounds.status_code, 404)

    def test_03_questions_filters_and_provenance(self) -> None:
        filters_res = self.client.get("/questions/filters")
        self.assertEqual(filters_res.status_code, 200)
        filters_data = filters_res.json()
        self.assertEqual(filters_data["total_questions"], 4)
        self.assertEqual(filters_data["total_mcqs"], 3)
        self.assertEqual(filters_data["total_non_mcqs"], 1)

        reported_res = self.client.get("/questions/?question_type=REPORTED")
        self.assertEqual(reported_res.status_code, 200)
        reported_qs = reported_res.json()["questions"]
        self.assertEqual(len(reported_qs), 1)
        self.assertEqual(reported_qs[0]["question_type"], "REPORTED")
        self.assertEqual(reported_qs[0]["company_name"], "Amazon")

    def test_04_mock_anti_leakage_grading_and_auth_linking(self) -> None:
        # Step 1: Unauthenticated guest starts a Mixed mock test with roll 22059999
        start_res = self.client.post(
            "/mock/start",
            json={
                "student_name": "Guest Tester",
                "student_roll_number": "22059999",
                "category": "Mixed",
                "num_questions": 3,
            },
        )
        self.assertEqual(start_res.status_code, 201)
        start_data = start_res.json()
        attempt_id = start_data["attempt_id"]
        self.assertEqual(start_data["total_questions"], 3)

        # Non-MCQ Coding question must NOT appear; correct_option/explanation must NOT leak
        for q in start_data["questions"]:
            self.assertNotIn("correct_option", q)
            self.assertNotIn("explanation", q)
            self.assertNotEqual(q["category"], "Coding")

        # Pre-submission GET must also hide answers
        pre_get = self.client.get(f"/mock/{attempt_id}")
        self.assertEqual(pre_get.status_code, 200)
        self.assertNotIn("results", pre_get.json())

        # Submitting an unknown question ID must return 400
        bad_submit = self.client.post(
            f"/mock/{attempt_id}/submit",
            json={"answers": [{"question_id": 99999, "selected_option": "A"}]},
        )
        self.assertEqual(bad_submit.status_code, 400)

        # Submit valid answers (2 correct, 1 intentionally wrong)
        submitted_answers = []
        for q in start_data["questions"]:
            if q["topic"] == "Percentages":
                submitted_answers.append({"question_id": q["id"], "selected_option": "A"})
            elif q["topic"] == "Probability":
                submitted_answers.append({"question_id": q["id"], "selected_option": "A"})
            else:
                submitted_answers.append({"question_id": q["id"], "selected_option": "D"})  # DBMS is C

        submit_res = self.client.post(
            f"/mock/{attempt_id}/submit",
            json={"answers": submitted_answers, "time_taken_seconds": 45},
        )
        self.assertEqual(submit_res.status_code, 200)
        submit_data = submit_res.json()
        self.assertEqual(submit_data["correct_answers"], 2)
        self.assertAlmostEqual(submit_data["score_percentage"], 66.67, places=1)
        self.assertEqual(len(submit_data["results"]), 3)

        # Double-submit must fail with 400
        resubmit = self.client.post(
            f"/mock/{attempt_id}/submit",
            json={"answers": submitted_answers},
        )
        self.assertEqual(resubmit.status_code, 400)

        # Step 2: Sign up with same roll 22059999 -> prior attempt auto-links!
        signup_res = self.client.post(
            "/auth/signup",
            json={
                "full_name": "Anurag Student",
                "roll_number": "22059999",
                "email": "22059999@kiit.ac.in",
                "branch": "CSE",
                "cgpa": 8.75,
                "password": "password123",
            },
        )
        self.assertEqual(signup_res.status_code, 201)
        token = signup_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Duplicate roll signup -> 409
        dup_res = self.client.post(
            "/auth/signup",
            json={
                "full_name": "Duplicate",
                "roll_number": "22059999",
                "password": "password123",
            },
        )
        self.assertEqual(dup_res.status_code, 409)

        # Invalid login -> 401; valid login -> 200
        bad_login = self.client.post(
            "/auth/login",
            json={"identifier": "22059999", "password": "wrongpassword"},
        )
        self.assertEqual(bad_login.status_code, 401)

        good_login = self.client.post(
            "/auth/login",
            json={"identifier": "22059999@kiit.ac.in", "password": "password123"},
        )
        self.assertEqual(good_login.status_code, 200)

        me_res = self.client.get("/auth/me", headers=headers)
        self.assertEqual(me_res.status_code, 200)
        self.assertEqual(me_res.json()["roll_number"], "22059999")

        # Step 3: Authenticated /performance/me sees linked guest attempt & weakest topic first
        perf_me = self.client.get("/performance/me", headers=headers)
        self.assertEqual(perf_me.status_code, 200)
        perf_data = perf_me.json()
        self.assertEqual(perf_data["completed_attempts"], 1)
        self.assertEqual(perf_data["topic_breakdown"][0]["topic"], "DBMS")
        self.assertEqual(perf_data["topic_breakdown"][0]["accuracy_percentage"], 0.0)

    def test_05_rag_and_agent_endpoints(self) -> None:
        rag_status = self.client.get("/agent/rag/status")
        self.assertEqual(rag_status.status_code, 200)
        status_data = rag_status.json()
        self.assertGreater(status_data["total_chunks"], 0)
        self.assertIn("TCS", status_data["indexed_companies"])

        rag_search = self.client.get(
            "/agent/rag/search",
            params={"query": "TCS NQT Prime", "company_name": "TCS", "top_k": 2},
        )
        self.assertEqual(rag_search.status_code, 200)
        self.assertGreaterEqual(rag_search.json()["total_results"], 1)

        chat_res = self.client.post(
            "/agent/chat",
            json={"message": "What is TCS eligibility criteria and CGPA cutoff?", "company_name": "TCS"},
        )
        self.assertEqual(chat_res.status_code, 200)
        chat_data = chat_res.json()
        self.assertIn("6.0", chat_data["response"])
        self.assertIn("get_company_eligibility", chat_data["tools_used"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
