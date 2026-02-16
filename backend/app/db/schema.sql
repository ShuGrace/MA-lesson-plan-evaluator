-- ============================================
-- Place-Based Learning Lesson Plan Evaluator
-- Database Schema (SQLite) - Framework v3.0
-- ============================================

-- Drop existing tables (for development reset)
DROP TABLE IF EXISTS debate_sessions;
DROP TABLE IF EXISTS evaluations;

-- ============================================
-- Main Evaluations Table
-- ============================================
CREATE TABLE evaluations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    -- Lesson Plan Content
    lesson_plan_text TEXT NOT NULL,
    lesson_plan_title VARCHAR(500),
    grade_level VARCHAR(50),
    subject_area VARCHAR(100),

    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(20) DEFAULT 'pending',

    -- Evaluation Scores (0-100) — Framework v3.0: 4 dimensions
    place_based_score INTEGER,
    cultural_score INTEGER,
    critical_pedagogy_score INTEGER,
    lesson_design_score INTEGER,
    overall_score INTEGER,

    -- API Mode and Provider
    api_mode VARCHAR(10) DEFAULT 'mock',
    provider VARCHAR(20) DEFAULT 'gpt',

    -- Detailed Results (stored as JSON text in SQLite)
    agent_responses TEXT,
    debate_transcript TEXT,
    recommendations TEXT,

    -- Error handling
    error_message TEXT
);

-- Index for status queries
CREATE INDEX idx_evaluations_status ON evaluations(status);

-- Index for date-based queries
CREATE INDEX idx_evaluations_created_at ON evaluations(created_at DESC);

-- Index for API mode filtering
CREATE INDEX idx_evaluations_api_mode ON evaluations(api_mode);

-- Index for provider filtering
CREATE INDEX idx_evaluations_provider ON evaluations(provider);

-- ============================================
-- Debate Sessions Table
-- ============================================
CREATE TABLE debate_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    -- Foreign key to evaluations
    evaluation_id INTEGER NOT NULL,

    -- Debate round information
    round_number INTEGER NOT NULL,
    topic VARCHAR(200) NOT NULL,

    -- Debate content (JSON array of exchanges)
    exchanges TEXT NOT NULL,

    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    duration_seconds INTEGER,

    -- Foreign key constraint
    FOREIGN KEY (evaluation_id) REFERENCES evaluations(id) ON DELETE CASCADE
);

-- Index for evaluation lookup
CREATE INDEX idx_debate_sessions_eval_id ON debate_sessions(evaluation_id);

-- Index for round ordering
CREATE INDEX idx_debate_sessions_round ON debate_sessions(evaluation_id, round_number);