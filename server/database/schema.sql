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

-- Mailbox Organization Progress Tracking
CREATE TABLE IF NOT EXISTS email_organization_progress (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(100) NOT NULL,
    account_id VARCHAR(255) NOT NULL,
    provider VARCHAR(50) NOT NULL 
        CHECK (provider IN ('yahoo', 'gmail', 'hotmail', 'apple', 'comcast', 'imap')),
    email_address VARCHAR(255) NOT NULL,
    total_emails INTEGER NOT NULL,
    processed_count INTEGER DEFAULT 0,
    last_email_id VARCHAR(255),
    status VARCHAR(20) DEFAULT 'not_started' 
        CHECK (status IN ('not_started', 'running', 'paused', 'completed', 'cancelled', 'error')),
    batch_size INTEGER DEFAULT 3000,
    current_batch INTEGER DEFAULT 0,
    spam_count INTEGER DEFAULT 0,
    keep_count INTEGER DEFAULT 0,
    unsure_count INTEGER DEFAULT 0,
    moved_count INTEGER DEFAULT 0,
    error_count INTEGER DEFAULT 0,
    started_at TIMESTAMP,
    last_update TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP,
    estimated_completion TIMESTAMP,
    last_error TEXT,
    retry_count INTEGER DEFAULT 0,
    UNIQUE(user_id, account_id)
);

CREATE INDEX idx_org_progress_user ON email_organization_progress(user_id);
CREATE INDEX idx_org_progress_status ON email_organization_progress(status);
CREATE INDEX idx_org_progress_provider ON email_organization_progress(provider);

-- Contacts table
CREATE TABLE IF NOT EXISTS contacts (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) NOT NULL,
    phone VARCHAR(50),
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, email)
);

CREATE INDEX IF NOT EXISTS idx_contacts_user_id ON contacts(user_id);
CREATE INDEX IF NOT EXISTS idx_contacts_email ON contacts(email);
