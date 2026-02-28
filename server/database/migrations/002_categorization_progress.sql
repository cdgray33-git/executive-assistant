-- Add categorization progress columns
ALTER TABLE email_organization_progress 
ADD COLUMN IF NOT EXISTS categorizing_count INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS categorizing_total INTEGER DEFAULT 0;
