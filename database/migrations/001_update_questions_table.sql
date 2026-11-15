-- ============================================================================
-- Migration 001: Update Existing 'questions' Table for Question Bank Import
-- Target Database: student_prep_db
-- Run this once in pgAdmin 4 Query Tool before executing import_questions.py
-- ============================================================================

-- 1. Drop any existing CHECK constraint on questions.question_type
DO $$
DECLARE
    constraint_rec RECORD;
BEGIN
    FOR constraint_rec IN
        SELECT conname
        FROM pg_constraint
        WHERE conrelid = 'questions'::regclass
          AND contype = 'c'
          AND pg_get_constraintdef(oid) ILIKE '%question_type%'
    LOOP
        EXECUTE format('ALTER TABLE questions DROP CONSTRAINT IF EXISTS %I', constraint_rec.conname);
    END LOOP;
END $$;

-- 2. Re-add the updated CHECK constraint allowing PYQ, Practice, PRACTICE, and REPORTED
ALTER TABLE questions
    ADD CONSTRAINT chk_question_type
    CHECK (question_type IN ('PYQ', 'Practice', 'PRACTICE', 'REPORTED'));

-- 3. Widen questions.source from VARCHAR(150) to TEXT (some CSV source URLs exceed 150 chars)
ALTER TABLE questions
    ALTER COLUMN source TYPE TEXT;

