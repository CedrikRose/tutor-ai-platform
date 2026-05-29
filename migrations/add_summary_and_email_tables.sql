-- Migration: Add course summary and email automation tables
-- Created: 2026-05-18
-- Description: Adds tables for course summaries and email automations

-- Course Summaries
CREATE TABLE IF NOT EXISTS course_summaries (
    summary_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    course_id UUID NOT NULL REFERENCES courses(course_id) ON DELETE CASCADE,

    -- Date range
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    days_back INTEGER NOT NULL,

    -- Summary content
    summary_text TEXT NOT NULL,
    statistics JSONB,

    -- Metadata
    generated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    generated_by VARCHAR(50) DEFAULT 'system'
);

CREATE INDEX IF NOT EXISTS idx_course_summaries_course ON course_summaries(course_id);
CREATE INDEX IF NOT EXISTS idx_course_summaries_date ON course_summaries(end_date);
CREATE INDEX IF NOT EXISTS idx_course_summaries_generated ON course_summaries(generated_at);

-- Email Automations
-- Logic: Every X days at 8 AM → summary of last X days
-- Example: days_back=7 → Every 7 days, send summary of last 7 days
CREATE TABLE IF NOT EXISTS email_automations (
    automation_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    course_id UUID NOT NULL REFERENCES courses(course_id) ON DELETE CASCADE,
    professor_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,

    -- Configuration
    enabled BOOLEAN DEFAULT TRUE,
    days_back INTEGER NOT NULL CHECK (days_back >= 1 AND days_back <= 7),
    send_time_hour INTEGER DEFAULT 8,

    -- Email recipients
    recipient_emails VARCHAR[] NOT NULL,

    -- Metadata
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    last_sent_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_email_automations_course ON email_automations(course_id);
CREATE INDEX IF NOT EXISTS idx_email_automations_professor ON email_automations(professor_id);
CREATE INDEX IF NOT EXISTS idx_email_automations_enabled ON email_automations(enabled);

-- Email Logs
CREATE TABLE IF NOT EXISTS email_logs (
    log_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    automation_id UUID REFERENCES email_automations(automation_id) ON DELETE SET NULL,
    summary_id UUID REFERENCES course_summaries(summary_id) ON DELETE SET NULL,

    -- Email details
    recipient_emails VARCHAR[] NOT NULL,
    subject VARCHAR(255) NOT NULL,

    -- Status
    sent_at TIMESTAMP NOT NULL DEFAULT NOW(),
    status VARCHAR(50) DEFAULT 'sent',
    error_message TEXT
);

CREATE INDEX IF NOT EXISTS idx_email_logs_automation ON email_logs(automation_id);
CREATE INDEX IF NOT EXISTS idx_email_logs_sent ON email_logs(sent_at);
CREATE INDEX IF NOT EXISTS idx_email_logs_status ON email_logs(status);
