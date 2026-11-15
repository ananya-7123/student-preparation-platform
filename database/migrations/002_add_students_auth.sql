-- ============================================================================
-- Migration 002: Student Authentication Table & MockAttempt Foreign Key
-- Target Database: student_prep_db
-- (Also auto-applied safely at FastAPI startup)
-- ============================================================================

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

ALTER TABLE mock_attempts
    ADD COLUMN IF NOT EXISTS student_id INTEGER REFERENCES students(id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS idx_students_roll_lower ON students (LOWER(roll_number));
CREATE INDEX IF NOT EXISTS idx_mock_attempts_student_id ON mock_attempts (student_id);

