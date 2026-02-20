-- JARVIS Executive Assistant Database Schema
-- PostgreSQL + pgvector for conversation memory

-- Conversations table (with vector embeddings)
CREATE TABLE IF NOT EXISTS conversations (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(100) NOT NULL,
    session_id UUID NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    role VARCHAR(20) NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    message_text TEXT NOT NULL,
    embedding vector(384),
    function_calls JSONB,
    metadata JSONB
);

CREATE INDEX IF NOT EXISTS idx_user_id ON conversations(user_id);
CREATE INDEX IF NOT EXISTS idx_session_id ON conversations(session_id);
CREATE INDEX IF NOT EXISTS idx_timestamp ON conversations(timestamp);

-- Vector similarity index
CREATE INDEX IF NOT EXISTS conversations_embedding_idx 
ON conversations USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

-- Meetings table
CREATE TABLE IF NOT EXISTS meetings (
    id SERIAL PRIMARY KEY,
    event_id VARCHAR(255) UNIQUE NOT NULL,
    user_id VARCHAR(100) NOT NULL,
    title VARCHAR(255) NOT NULL,
    date DATE NOT NULL,
    time TIME NOT NULL,
    duration INTEGER DEFAULT 60,
    description TEXT,
    attendees JSONB NOT NULL,
    status VARCHAR(50) DEFAULT 'scheduled',
    conversation_id INTEGER REFERENCES conversations(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_user_meetings ON meetings(user_id);
CREATE INDEX IF NOT EXISTS idx_event_id ON meetings(event_id);
CREATE INDEX IF NOT EXISTS idx_meeting_date ON meetings(date);

-- Email learning table
CREATE TABLE IF NOT EXISTS email_learning (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(100) NOT NULL,
    account_id VARCHAR(255) NOT NULL,
    sender_email VARCHAR(255) NOT NULL,
    sender_name VARCHAR(255),
    original_category VARCHAR(50),
    user_category VARCHAR(50) NOT NULL,
    was_corrected BOOLEAN DEFAULT FALSE,
    confidence_score FLOAT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_learning_sender ON email_learning(sender_email);
CREATE INDEX IF NOT EXISTS idx_learning_user ON email_learning(user_id, account_id);

-- Tasks table
CREATE TABLE IF NOT EXISTS tasks (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(100) NOT NULL,
    description TEXT NOT NULL,
    status VARCHAR(50) DEFAULT 'pending',
    priority VARCHAR(20) DEFAULT 'medium',
    due_date TIMESTAMP,
    completed_at TIMESTAMP,
    conversation_id INTEGER REFERENCES conversations(id),
    related_document VARCHAR(500),
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_task_user ON tasks(user_id);
CREATE INDEX IF NOT EXISTS idx_task_status ON tasks(status);
CREATE INDEX IF NOT EXISTS idx_task_due ON tasks(due_date);

-- Uncategorized email tracking
CREATE TABLE IF NOT EXISTS uncategorized_emails (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(100) NOT NULL,
    account_id VARCHAR(255) NOT NULL,
    email_id VARCHAR(255) NOT NULL,
    sender VARCHAR(255),
    subject VARCHAR(500),
    received_date TIMESTAMP,
    needs_review BOOLEAN DEFAULT TRUE,
    moved_to_review BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(account_id, email_id)
);

CREATE INDEX IF NOT EXISTS idx_uncategorized_account ON uncategorized_emails(account_id);
CREATE INDEX IF NOT EXISTS idx_uncategorized_user ON uncategorized_emails(user_id);
