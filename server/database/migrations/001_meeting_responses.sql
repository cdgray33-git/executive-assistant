-- Meeting Response Tracking Enhancement
-- Add columns to meetings table for response monitoring

ALTER TABLE meetings 
ADD COLUMN IF NOT EXISTS response_status VARCHAR(50) DEFAULT 'pending',
ADD COLUMN IF NOT EXISTS attendee_responses JSONB DEFAULT '[]'::jsonb,
ADD COLUMN IF NOT EXISTS message_id VARCHAR(255),
ADD COLUMN IF NOT EXISTS last_checked TIMESTAMP,
ADD COLUMN IF NOT EXISTS ics_uid VARCHAR(255);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_meetings_response_status ON meetings(response_status);
CREATE INDEX IF NOT EXISTS idx_meetings_last_checked ON meetings(last_checked);
CREATE INDEX IF NOT EXISTS idx_meetings_message_id ON meetings(message_id);

-- Calendar blocks table (for user availability management)
CREATE TABLE IF NOT EXISTS calendar_blocks (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(100) NOT NULL,
    title VARCHAR(255) NOT NULL,
    start_time TIMESTAMP NOT NULL,
    end_time TIMESTAMP NOT NULL,
    block_type VARCHAR(50) DEFAULT 'busy',
    recurring BOOLEAN DEFAULT FALSE,
    recurrence_rule TEXT,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_blocks_user ON calendar_blocks(user_id);
CREATE INDEX IF NOT EXISTS idx_blocks_time ON calendar_blocks(start_time, end_time);

COMMENT ON TABLE calendar_blocks IS 'User calendar blocks for managing availability';
COMMENT ON COLUMN calendar_blocks.block_type IS 'busy, out-of-office, lunch, meeting, personal';
