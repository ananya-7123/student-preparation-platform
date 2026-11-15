-- ============================================================================
-- Student Preparation Platform - PostgreSQL Database Schema
-- Target Database: student_prep_db
-- ============================================================================

-- 1. Companies Table
CREATE TABLE IF NOT EXISTS companies (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    industry VARCHAR(100),
    description TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. Eligibility Criteria Table (1-to-1 with companies)
CREATE TABLE IF NOT EXISTS eligibility_criteria (
    id SERIAL PRIMARY KEY,
    company_id INTEGER NOT NULL UNIQUE REFERENCES companies(id) ON DELETE CASCADE,
    cgpa_cutoff DECIMAL(4, 2) NOT NULL CHECK (cgpa_cutoff >= 0 AND cgpa_cutoff <= 10),
    backlogs_allowed INTEGER NOT NULL DEFAULT 0 CHECK (backlogs_allowed >= 0),
    branches TEXT NOT NULL,
    additional_notes TEXT
);

-- 3. Selection Rounds Table (1-to-Many with companies)
CREATE TABLE IF NOT EXISTS selection_rounds (
    id SERIAL PRIMARY KEY,
    company_id INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    round_number INTEGER NOT NULL CHECK (round_number >= 1),
    round_name VARCHAR(150) NOT NULL,
    description TEXT,
    CONSTRAINT uq_company_round UNIQUE (company_id, round_number)
);

-- 4. Questions Table (Practice & PYQ Question Bank)
CREATE TABLE IF NOT EXISTS questions (
    id SERIAL PRIMARY KEY,
    company_id INTEGER REFERENCES companies(id) ON DELETE SET NULL,
    category VARCHAR(50) NOT NULL,
    topic VARCHAR(100),
    difficulty VARCHAR(20) NOT NULL DEFAULT 'Medium'
        CHECK (difficulty IN ('Easy', 'Medium', 'Hard')),
    question_type VARCHAR(20) NOT NULL DEFAULT 'Practice',
    year INTEGER CHECK (year IS NULL OR (year >= 2000 AND year <= 2100)),
    source TEXT,
    CONSTRAINT chk_question_type CHECK (question_type IN ('PYQ', 'Practice', 'PRACTICE', 'REPORTED')),
    question_text TEXT NOT NULL,
    option_a TEXT,
    option_b TEXT,
    option_c TEXT,
    option_d TEXT,
    correct_option CHAR(1)
        CHECK (correct_option IS NULL OR correct_option IN ('A', 'B', 'C', 'D')),
    explanation TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 5. Students Table (Authentication & Profile)
CREATE TABLE IF NOT EXISTS students (
    id SERIAL PRIMARY KEY,
    full_name VARCHAR(100) NOT NULL,
    roll_number VARCHAR(50) NOT NULL UNIQUE,
    email VARCHAR(150) UNIQUE,
    branch VARCHAR(80),
    cgpa DECIMAL(4, 2) CHECK (cgpa IS NULL OR (cgpa >= 0 AND cgpa <= 10)),
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 6. Mock Attempts Table (Dynamic Mock Test Sessions)
CREATE TABLE IF NOT EXISTS mock_attempts (
    id SERIAL PRIMARY KEY,
    student_id INTEGER REFERENCES students(id) ON DELETE SET NULL,
    student_name VARCHAR(100) NOT NULL,
    student_roll_number VARCHAR(50),
    company_id INTEGER REFERENCES companies(id) ON DELETE SET NULL,
    category VARCHAR(50) NOT NULL DEFAULT 'Mixed',
    total_questions INTEGER NOT NULL CHECK (total_questions > 0),
    correct_answers INTEGER NOT NULL DEFAULT 0 CHECK (correct_answers >= 0),
    score_percentage DECIMAL(5, 2) NOT NULL DEFAULT 0.00
        CHECK (score_percentage >= 0 AND score_percentage <= 100),
    started_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    time_taken_seconds INTEGER CHECK (time_taken_seconds IS NULL OR time_taken_seconds >= 0),
    CONSTRAINT chk_correct_le_total CHECK (correct_answers <= total_questions)
);

-- 7. Attempt Answers Table (Per-question responses inside a mock attempt)
CREATE TABLE IF NOT EXISTS attempt_answers (
    id SERIAL PRIMARY KEY,
    attempt_id INTEGER NOT NULL REFERENCES mock_attempts(id) ON DELETE CASCADE,
    question_id INTEGER NOT NULL REFERENCES questions(id) ON DELETE CASCADE,
    selected_option CHAR(1)
        CHECK (selected_option IS NULL OR selected_option IN ('A', 'B', 'C', 'D')),
    written_answer TEXT,
    is_correct BOOLEAN NOT NULL DEFAULT FALSE,
    CONSTRAINT uq_attempt_question UNIQUE (attempt_id, question_id)
);

-- ============================================================================
-- Indexes for Query Performance
-- ============================================================================

CREATE INDEX IF NOT EXISTS idx_companies_name_lower ON companies (LOWER(name));
CREATE INDEX IF NOT EXISTS idx_students_roll_lower ON students (LOWER(roll_number));
CREATE INDEX IF NOT EXISTS idx_questions_company_id ON questions (company_id);
CREATE INDEX IF NOT EXISTS idx_questions_category_difficulty ON questions (category, difficulty);
CREATE INDEX IF NOT EXISTS idx_questions_type ON questions (question_type);
CREATE INDEX IF NOT EXISTS idx_mock_attempts_student_id ON mock_attempts (student_id);
CREATE INDEX IF NOT EXISTS idx_mock_attempts_student_roll ON mock_attempts (student_roll_number);
CREATE INDEX IF NOT EXISTS idx_mock_attempts_student_name ON mock_attempts (student_name);
CREATE INDEX IF NOT EXISTS idx_mock_attempts_company_id ON mock_attempts (company_id);
CREATE INDEX IF NOT EXISTS idx_attempt_answers_question_id ON attempt_answers (question_id);

