-- ============================================================================
-- Student Preparation Platform - Initial & Verified Company Seed Data
-- Target Database: student_prep_db
-- Sources: Existing platform baseline + verified KIIT notices/notes in resources/companies/
-- ============================================================================

-- 1. Seed / Update Companies (10 companies: 7 from resources/companies + Infosys, Wipro, Capgemini)
INSERT INTO companies (name, industry, description) VALUES
(
    'TCS',
    'IT Services',
    'Tata Consultancy Services is a global leader in IT services. KIIT 2027 hiring runs via TCS NQT (Prime: 9.09 LPA UG, Digital: 7.09 LPA UG, Ninja: 3.46 LPA UG).'
),
(
    'Accenture',
    'Consulting & IT',
    'Accenture is a global professional services company operating across Strategy & Consulting, Technology, Operations, Industry X, and Song (KIIT 2026/2027 profiles: ASE, AASE, AAE).'
),
(
    'Cognizant',
    'IT Services & Consulting',
    'Cognizant is a multinational IT services and consulting company conducting 2027 Campus Hiring via Digital Nurture 5.0 (GenC: Programmer Analyst Trainee, GenC Next: Programmer Analyst).'
),
(
    'Deloitte',
    'Consulting & Advisory',
    'Deloitte provides audit, consulting, tax, and Technology & Transformation Analyst roles (Engineering, AI & Data, PDI/EAD, Customer, and Oracle Cloud; ~7.6 to 8.2 LPA).'
),
(
    'HighRadius',
    'FinTech & Enterprise AI SaaS',
    'HighRadius runs an AI agentic platform for the Office of the CFO. KIIT 2027 drive includes a 12-month Internship-cum-PPO (Marketing ABM Intern, 27,000/month stipend, 8.00 LPA CTC).'
),
(
    'IBM',
    'Technology & Consulting',
    'IBM Consulting builds enterprise hybrid-cloud and AI solutions. KIIT 2027 hybrid drive offers Associate System Engineer (4.50 LPA + INR 25,000 one-time settling allowance).'
),
(
    'Tech Mahindra',
    'IT Services & Digital Transformation',
    'Tech Mahindra is part of the Mahindra Group delivering enterprise digital transformation. KIIT 2027 drive offers Digital Catalyst - AI Engineer (8.00 LPA + 2 Lakh retention bonus).'
),
(
    'Infosys',
    'IT Services & Consulting',
    'Infosys is a global leader in next-generation digital services and consulting.'
),
(
    'Wipro',
    'IT Services & Consulting',
    'Wipro Limited is a leading global information technology, consulting, and business process services company.'
),
(
    'Capgemini',
    'Consulting & Technology',
    'Capgemini is a global leader in consulting, digital transformation, technology, and engineering services.'
)
ON CONFLICT (name) DO UPDATE SET
    industry = EXCLUDED.industry,
    description = EXCLUDED.description,
    updated_at = CURRENT_TIMESTAMP;


-- 2. Seed / Update Eligibility Criteria (1-to-1 with companies)
INSERT INTO eligibility_criteria (company_id, cgpa_cutoff, backlogs_allowed, branches, additional_notes)
SELECT id, 6.00, 1, 'All B.Tech, B.E., M.Tech, M.E., MCA, M.Sc./M.S. disciplines',
       'KIIT Notice (KIIT-DU/T&P/26/352): 60% or 6.0 CGPA throughout academics; max 1 active backlog at selection (0 at joining); max 24-month gap; full-time only; age 18-28.'
FROM companies WHERE name = 'TCS'
ON CONFLICT (company_id) DO UPDATE SET
    cgpa_cutoff = EXCLUDED.cgpa_cutoff,
    backlogs_allowed = EXCLUDED.backlogs_allowed,
    branches = EXCLUDED.branches,
    additional_notes = EXCLUDED.additional_notes;

INSERT INTO eligibility_criteria (company_id, cgpa_cutoff, backlogs_allowed, branches, additional_notes)
SELECT id, 6.50, 0, 'B.Tech (All Branches), M.Tech (All Branches), MCA',
       'Full-time education only; no active backlogs; no degree gaps; <= 23 months experience; valid PAN card with photo mandatory (CGPA baseline 6.5; verify per drive notice).'
FROM companies WHERE name = 'Accenture'
ON CONFLICT (company_id) DO UPDATE SET
    cgpa_cutoff = EXCLUDED.cgpa_cutoff,
    backlogs_allowed = EXCLUDED.backlogs_allowed,
    branches = EXCLUDED.branches,
    additional_notes = EXCLUDED.additional_notes;

INSERT INTO eligibility_criteria (company_id, cgpa_cutoff, backlogs_allowed, branches, additional_notes)
SELECT id, 6.00, 0, 'B.E/B.Tech/M.E/M.Tech in CS, IT, or Circuit streams',
       'Cognizant DN 5.0 Brochure: Min 60% in X, XII, Diploma, and UG (59.9% not rounded off); no standing arrears; PAN, Aadhar & Passport/Voter ID mandatory for onboarding.'
FROM companies WHERE name = 'Cognizant'
ON CONFLICT (company_id) DO UPDATE SET
    cgpa_cutoff = EXCLUDED.cgpa_cutoff,
    backlogs_allowed = EXCLUDED.backlogs_allowed,
    branches = EXCLUDED.branches,
    additional_notes = EXCLUDED.additional_notes;

INSERT INTO eligibility_criteria (company_id, cgpa_cutoff, backlogs_allowed, branches, additional_notes)
SELECT id, 6.00, 0, 'CSE, Cyber Security, EEE, ECE, IT, ICT, IS, Math & Computing, Mech, Civil, M.Tech, MCA',
       'Data & Analytics JD specifies min 60% / 6.0 CGPA with no active backlog. Some roles require willingness for shifts/client locations.'
FROM companies WHERE name = 'Deloitte'
ON CONFLICT (company_id) DO UPDATE SET
    cgpa_cutoff = EXCLUDED.cgpa_cutoff,
    backlogs_allowed = EXCLUDED.backlogs_allowed,
    branches = EXCLUDED.branches,
    additional_notes = EXCLUDED.additional_notes;

INSERT INTO eligibility_criteria (company_id, cgpa_cutoff, backlogs_allowed, branches, additional_notes)
SELECT id, 8.00, 0, 'B.Tech (All Branches)',
       'KIIT Notice (KIIT-DU/T&P/26/591 - Marketing ABM Intern cum PPO): 75% or above in 10th & 12th/Diploma; 8.00+ CGPA in B.Tech; no backlogs.'
FROM companies WHERE name = 'HighRadius'
ON CONFLICT (company_id) DO UPDATE SET
    cgpa_cutoff = EXCLUDED.cgpa_cutoff,
    backlogs_allowed = EXCLUDED.backlogs_allowed,
    branches = EXCLUDED.branches,
    additional_notes = EXCLUDED.additional_notes;

INSERT INTO eligibility_criteria (company_id, cgpa_cutoff, backlogs_allowed, branches, additional_notes)
SELECT id, 6.00, 0, 'B.Tech (CSE/CS&CE/CS&SE/IT), M.Tech (CSE/AI&DS/Cybersecurity), MCA',
       'KIIT Notice (KIIT-DU/T&P/26/845): 60% throughout academic career; no backlogs; fluent written and spoken communication skills.'
FROM companies WHERE name = 'IBM'
ON CONFLICT (company_id) DO UPDATE SET
    cgpa_cutoff = EXCLUDED.cgpa_cutoff,
    backlogs_allowed = EXCLUDED.backlogs_allowed,
    branches = EXCLUDED.branches,
    additional_notes = EXCLUDED.additional_notes;

INSERT INTO eligibility_criteria (company_id, cgpa_cutoff, backlogs_allowed, branches, additional_notes)
SELECT id, 5.00, 0, 'B.Tech (CSE/CS&CE/CS&SE/IT/ETC/E&CSE/EEE/EE), M.Tech (CSE/AI&DS/CyberSecurity/VLSI/AES/Comm)',
       'KIIT Notice (KIIT-DU/T&P/26/1021 - Digital Catalyst AI Engineer): 50% throughout academic career; no backlogs.'
FROM companies WHERE name = 'Tech Mahindra'
ON CONFLICT (company_id) DO UPDATE SET
    cgpa_cutoff = EXCLUDED.cgpa_cutoff,
    backlogs_allowed = EXCLUDED.backlogs_allowed,
    branches = EXCLUDED.branches,
    additional_notes = EXCLUDED.additional_notes;

INSERT INTO eligibility_criteria (company_id, cgpa_cutoff, backlogs_allowed, branches, additional_notes)
SELECT id, 6.00, 0, 'CSE, IT, CSSE, CSCE, ECE, EEE, E&I',
       'Baseline placeholder: minimum 60% throughout 10th, 12th, and graduation (verify against official drive notice when added).'
FROM companies WHERE name = 'Infosys'
ON CONFLICT (company_id) DO UPDATE SET
    cgpa_cutoff = EXCLUDED.cgpa_cutoff,
    backlogs_allowed = EXCLUDED.backlogs_allowed,
    branches = EXCLUDED.branches,
    additional_notes = EXCLUDED.additional_notes;

INSERT INTO eligibility_criteria (company_id, cgpa_cutoff, backlogs_allowed, branches, additional_notes)
SELECT id, 6.00, 0, 'All B.Tech branches',
       'Baseline placeholder: minimum 60% in 10th & 12th, and 6.0 CGPA in B.Tech (verify against official drive notice when added).'
FROM companies WHERE name = 'Wipro'
ON CONFLICT (company_id) DO UPDATE SET
    cgpa_cutoff = EXCLUDED.cgpa_cutoff,
    backlogs_allowed = EXCLUDED.backlogs_allowed,
    branches = EXCLUDED.branches,
    additional_notes = EXCLUDED.additional_notes;

INSERT INTO eligibility_criteria (company_id, cgpa_cutoff, backlogs_allowed, branches, additional_notes)
SELECT id, 6.00, 0, 'CSE, IT, CSSE, CSCE, ECE, EEE',
       'Baseline placeholder: minimum 60% in 10th, 12th, and current B.Tech aggregate (verify against official drive notice when added).'
FROM companies WHERE name = 'Capgemini'
ON CONFLICT (company_id) DO UPDATE SET
    cgpa_cutoff = EXCLUDED.cgpa_cutoff,
    backlogs_allowed = EXCLUDED.backlogs_allowed,
    branches = EXCLUDED.branches,
    additional_notes = EXCLUDED.additional_notes;


-- 3. Seed / Refresh Selection Rounds (Ordered by round_number per company)
-- Clear existing rounds for these 10 seeded companies so round numbers stay clean on re-run
DELETE FROM selection_rounds
WHERE company_id IN (
    SELECT id FROM companies
    WHERE name IN (
        'TCS', 'Accenture', 'Cognizant', 'Deloitte', 'HighRadius',
        'IBM', 'Tech Mahindra', 'Infosys', 'Wipro', 'Capgemini'
    )
);

-- TCS (Verified from KIIT NQT notice & company_info.md)
INSERT INTO selection_rounds (company_id, round_number, round_name, description) VALUES
((SELECT id FROM companies WHERE name = 'TCS'), 1, 'TCS NQT Integrated Test (190 min)', 'Part A Foundation (75 min: Numerical 25m, Verbal 25m, Reasoning 25m) + Part B Advanced (115 min: Adv Quant & Reasoning 25m, Adv Coding 90m).'),
((SELECT id FROM companies WHERE name = 'TCS'), 2, 'Technical Interview', 'Shortlisted for Prime/Digital/Ninja based on NQT score; evaluates core CS, coding, and selected skills.'),
((SELECT id FROM companies WHERE name = 'TCS'), 3, 'HR Interview', 'Behavioral assessment, document verification, and background check.');

-- Accenture (Verified from resources/companies/Accenture/07_notes/company_info.md)
INSERT INTO selection_rounds (company_id, round_number, round_name, description) VALUES
((SELECT id FROM companies WHERE name = 'Accenture'), 1, 'Behavioral, Cognitive, Technical & Coding Assessment', 'Online assessment evaluating problem-solving, logical reasoning, applied technical knowledge, and coding approach.'),
((SELECT id FROM companies WHERE name = 'Accenture'), 2, 'Communication Assessment', 'Evaluates spoken and comprehension proficiency.'),
((SELECT id FROM companies WHERE name = 'Accenture'), 3, 'Interviews', 'Technical and HR evaluation based on projects, fundamentals, and role fit.');

-- Cognizant (Verified from 2027 Campus hiring DN 5.0 brochure)
INSERT INTO selection_rounds (company_id, round_number, round_name, description) VALUES
((SELECT id FROM companies WHERE name = 'Cognizant'), 1, 'Communication Assessment (Online)', 'Initial online communication screening before 3-week self-learning upskilling.'),
((SELECT id FROM companies WHERE name = 'Cognizant'), 2, 'Qualifier Assessment (Online)', 'Online qualifier conducted after 3 weeks of upskilling, leading into 7-week deep skilling.'),
((SELECT id FROM companies WHERE name = 'Cognizant'), 3, 'Technical Assessment (Offline)', 'In-person technical evaluation conducted after 7 weeks of deep skilling.'),
((SELECT id FROM companies WHERE name = 'Cognizant'), 4, 'Technical Interview (Online)', 'Final online technical interview prior to Letter of Intent (LOI).');

-- Deloitte (Note: company_info.md states universal campus round sequence is not fixed in supplied PDFs)
INSERT INTO selection_rounds (company_id, round_number, round_name, description) VALUES
((SELECT id FROM companies WHERE name = 'Deloitte'), 1, 'Online Aptitude & Technical Assessment', 'Typical initial screening (exact pattern varies by Analytics/Engineering/Consulting role).'),
((SELECT id FROM companies WHERE name = 'Deloitte'), 2, 'Group Discussion / Case Discussion', 'Role-dependent communication and structured analytical problem-solving.'),
((SELECT id FROM companies WHERE name = 'Deloitte'), 3, 'Technical & Managerial Interview', 'Evaluates projects, SQL/Python/cloud/domain skills, and client-facing aptitude.');

-- HighRadius (Verified from KIIT-DU/T&P/26/591)
INSERT INTO selection_rounds (company_id, round_number, round_name, description) VALUES
((SELECT id FROM companies WHERE name = 'HighRadius'), 1, 'Online Test', 'Initial online screening assessment (physical campus recruitment drive).'),
((SELECT id FROM companies WHERE name = 'HighRadius'), 2, 'Speech Test', 'Verbal communication, fluency, and articulation evaluation.'),
((SELECT id FROM companies WHERE name = 'HighRadius'), 3, 'Interview', 'Role-fit, analytical thinking, and business/communication interview.');

-- IBM (Verified from KIIT-DU/T&P/26/845)
INSERT INTO selection_rounds (company_id, round_number, round_name, description) VALUES
((SELECT id FROM companies WHERE name = 'IBM'), 1, 'PPT (Pre-Placement Talk)', 'Company briefing on IBM Consulting Associate System Engineer role.'),
((SELECT id FROM companies WHERE name = 'IBM'), 2, 'Coding Assessment 1 (Virtual)', 'First online coding assessment (Java, C++, Python, or Node.js).'),
((SELECT id FROM companies WHERE name = 'IBM'), 3, 'Coding Assessment 2 (In-Person)', 'Proctored in-person coding assessment.'),
((SELECT id FROM companies WHERE name = 'IBM'), 4, 'Knockri Assessment (In-Person)', 'Behavioral and competency-based video/AI assessment.'),
((SELECT id FROM companies WHERE name = 'IBM'), 5, 'SHL Spoken English Assessment (In-Person)', 'Spoken English and communication proficiency test.'),
((SELECT id FROM companies WHERE name = 'IBM'), 6, 'Interviews (In-Person)', 'Final technical and HR interviews.');

-- Tech Mahindra (Verified from KIIT-DU/T&P/26/1021)
INSERT INTO selection_rounds (company_id, round_number, round_name, description) VALUES
((SELECT id FROM companies WHERE name = 'Tech Mahindra'), 1, 'Shortlisting', 'Screening from registered eligible candidates.'),
((SELECT id FROM companies WHERE name = 'Tech Mahindra'), 2, 'Coding Assessment', 'Programming proficiency (Python preferred; Java/C++/JS advantage), DSA, and SQL.'),
((SELECT id FROM companies WHERE name = 'Tech Mahindra'), 3, 'Cognitive Assessment', 'Logical reasoning, analytical problem-solving, and aptitude.'),
((SELECT id FROM companies WHERE name = 'Tech Mahindra'), 4, 'Verbal Assessment', 'English comprehension and communication assessment.'),
((SELECT id FROM companies WHERE name = 'Tech Mahindra'), 5, 'Interviews (Tech + HR)', 'Evaluates ML/AI basics, Python, SQL, REST APIs, and problem-solving.');

-- Infosys (Baseline)
INSERT INTO selection_rounds (company_id, round_number, round_name, description) VALUES
((SELECT id FROM companies WHERE name = 'Infosys'), 1, 'Online Assessment', 'Logical reasoning, mathematical ability, verbal ability, and pseudocode.'),
((SELECT id FROM companies WHERE name = 'Infosys'), 2, 'Technical Interview', 'Programming fundamentals, DBMS, SQL queries, and project discussion.'),
((SELECT id FROM companies WHERE name = 'Infosys'), 3, 'HR Interview', 'Situational questions, adaptability, and background check.');

-- Wipro (Baseline)
INSERT INTO selection_rounds (company_id, round_number, round_name, description) VALUES
((SELECT id FROM companies WHERE name = 'Wipro'), 1, 'Online Assessment', 'Aptitude (Quant, Logical, Verbal), written essay, and 2 coding questions.'),
((SELECT id FROM companies WHERE name = 'Wipro'), 2, 'Technical Interview', 'Core coding concepts, OOP, DBMS, and academic projects.'),
((SELECT id FROM companies WHERE name = 'Wipro'), 3, 'HR Interview', 'Communication skills, strengths/weaknesses, and service agreement review.');

-- Capgemini (Baseline)
INSERT INTO selection_rounds (company_id, round_number, round_name, description) VALUES
((SELECT id FROM companies WHERE name = 'Capgemini'), 1, 'Technical & Pseudocode Test', 'Pseudocode analysis, data structures, and IT fundamentals.'),
((SELECT id FROM companies WHERE name = 'Capgemini'), 2, 'English Communication Test', 'Grammar, vocabulary, and comprehension assessment.'),
((SELECT id FROM companies WHERE name = 'Capgemini'), 3, 'Game-Based Aptitude Test', 'Interactive cognitive problem-solving games.'),
((SELECT id FROM companies WHERE name = 'Capgemini'), 4, 'Technical & HR Interview', 'Resume walkthrough, CS core concepts, and behavioral discussion.');


-- 4. Seed Sample Questions (Inserted only if table is empty to avoid duplicates)
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM questions LIMIT 1) THEN
        INSERT INTO questions (
            company_id, category, topic, difficulty, question_type, year, source,
            question_text, option_a, option_b, option_c, option_d, correct_option, explanation
        ) VALUES
        (
            (SELECT id FROM companies WHERE name = 'TCS'),
            'Aptitude', 'Time & Work', 'Easy', 'PYQ', 2024, 'TCS NQT',
            'A can complete a work in 12 days and B can complete the same work in 18 days. How many days will they take to complete it together?',
            '6.8 days', '7.2 days', '7.5 days', '8.0 days', 'B',
            'Combined 1-day work = 1/12 + 1/18 = 5/36. Total days = 36/5 = 7.2 days.'
        ),
        (
            NULL,
            'Aptitude', 'Percentages', 'Easy', 'Practice', NULL, 'Internal Question Bank',
            'If the price of a product increases by 25%, by what percentage must a consumer reduce consumption so that expenditure remains unchanged?',
            '20%', '25%', '16.67%', '15%', 'A',
            'Required reduction = (25 / (100 + 25)) * 100 = (25/125)*100 = 20%.'
        ),
        (
            (SELECT id FROM companies WHERE name = 'Infosys'),
            'Aptitude', 'Probability', 'Medium', 'PYQ', 2024, 'Infosys Campus Drive',
            'Two fair dice are thrown simultaneously. What is the probability of getting a sum of 8?',
            '5/36', '1/6', '4/36', '7/36', 'A',
            'Favorable pairs: (2,6), (3,5), (4,4), (5,3), (6,2) = 5 out of 36 outcomes.'
        ),
        (
            (SELECT id FROM companies WHERE name = 'Accenture'),
            'Reasoning', 'Number Series', 'Easy', 'PYQ', 2024, 'Accenture Cognitive Test',
            'Find the next number in the series: 3, 7, 15, 31, 63, ?',
            '95', '126', '127', '128', 'C',
            'Each term follows (previous * 2) + 1: (63 * 2) + 1 = 127.'
        ),
        (
            (SELECT id FROM companies WHERE name = 'Capgemini'),
            'Reasoning', 'Blood Relations', 'Medium', 'Practice', NULL, 'Internal Question Bank',
            'Pointing to a photograph, Rahul said, "She is the daughter of my grandfather''s only son." How is the girl in the photograph related to Rahul?',
            'Cousin', 'Sister', 'Aunt', 'Mother', 'B',
            'Grandfather''s only son is Rahul''s father, so his daughter is Rahul''s sister.'
        ),
        (
            (SELECT id FROM companies WHERE name = 'Deloitte'),
            'Verbal', 'Grammar & Correction', 'Medium', 'PYQ', 2023, 'Deloitte NLA',
            'Choose the grammatically correct sentence:',
            'Neither the manager nor the employees was present.',
            'Neither the manager nor the employees were present.',
            'Neither the manager or the employees were present.',
            'Neither the manager nor the employees is present.', 'B',
            'With "neither...nor", the verb agrees with the nearer subject ("employees", plural -> "were").'
        ),
        (
            (SELECT id FROM companies WHERE name = 'Cognizant'),
            'Technical', 'DBMS', 'Medium', 'PYQ', 2024, 'Cognizant GenC',
            'Which normal form eliminates transitive dependency?',
            '1NF', '2NF', '3NF', 'BCNF', 'C',
            'Third Normal Form (3NF) removes transitive dependencies of non-prime attributes on candidate keys.'
        ),
        (
            (SELECT id FROM companies WHERE name = 'Wipro'),
            'Technical', 'Operating Systems', 'Medium', 'Practice', NULL, 'Internal Question Bank',
            'Which of the following is NOT one of the four necessary conditions for a deadlock?',
            'Mutual Exclusion', 'Hold and Wait', 'Preemption', 'Circular Wait', 'C',
            'The four Coffman conditions are Mutual Exclusion, Hold and Wait, No Preemption, and Circular Wait.'
        ),
        (
            NULL,
            'Technical', 'Data Structures', 'Easy', 'Practice', NULL, 'Internal Question Bank',
            'What is the average-case time complexity of searching for an element in a balanced Binary Search Tree (BST)?',
            'O(1)', 'O(log n)', 'O(n)', 'O(n log n)', 'B',
            'A balanced BST has height O(log n), making search O(log n).'
        ),
        (
            (SELECT id FROM companies WHERE name = 'TCS'),
            'Coding', 'Arrays', 'Easy', 'PYQ', 2024, 'TCS NQT',
            'Given an integer array nums, move all 0''s to the end of it while maintaining the relative order of the non-zero elements. Write a function to solve this in-place.',
            NULL, NULL, NULL, NULL, NULL,
            'Use a two-pointer approach: track the next non-zero write index and swap non-zero elements forward in O(n) time and O(1) space.'
        ),
        (
            (SELECT id FROM companies WHERE name = 'Accenture'),
            'Coding', 'Strings', 'Medium', 'PYQ', 2024, 'Accenture Coding Round',
            'Write a program to check whether two given strings are anagrams of each other (ignoring case and spaces).',
            NULL, NULL, NULL, NULL, NULL,
            'Normalize strings (lowercase, strip spaces), then compare character frequency maps in O(n) time.'
        );
    END IF;
END $$;
