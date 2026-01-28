-- SSOT Task Manager Backup Table
-- Run in Supabase SQL Editor or via migration
-- Primary source of truth is file system (.claude/tasks/*.json)
-- This table is BACKUP only

CREATE TABLE IF NOT EXISTS ssot_task_lists (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_list_id TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    task_list_json JSONB NOT NULL,
    total_tasks INTEGER DEFAULT 0,
    completed_tasks INTEGER DEFAULT 0,
    progress_pct NUMERIC(5,2) DEFAULT 0,
    status TEXT DEFAULT 'active',
    last_active_task_id TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    session_id TEXT,
    agent_id TEXT
);

-- Indexes for fast lookups
CREATE INDEX IF NOT EXISTS idx_ssot_task_list_id ON ssot_task_lists(task_list_id);
CREATE INDEX IF NOT EXISTS idx_ssot_status ON ssot_task_lists(status);
CREATE INDEX IF NOT EXISTS idx_ssot_updated ON ssot_task_lists(updated_at DESC);

-- Auto-update timestamp trigger
CREATE OR REPLACE FUNCTION update_ssot_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS ssot_updated_at ON ssot_task_lists;
CREATE TRIGGER ssot_updated_at
    BEFORE UPDATE ON ssot_task_lists
    FOR EACH ROW
    EXECUTE FUNCTION update_ssot_timestamp();

-- RLS Policy
ALTER TABLE ssot_task_lists ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Allow all operations" ON ssot_task_lists
    FOR ALL USING (true) WITH CHECK (true);

COMMENT ON TABLE ssot_task_lists IS 'Backup storage for SSOT task lists - file system is primary source of truth';
