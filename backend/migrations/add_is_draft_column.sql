-- Migration: Add is_draft column to notes table
-- Run this script to add draft functionality to notes

-- Add is_draft column with default value false
ALTER TABLE notes 
ADD COLUMN IF NOT EXISTS is_draft BOOLEAN NOT NULL DEFAULT FALSE;

-- Create index on is_draft for faster queries
CREATE INDEX IF NOT EXISTS idx_notes_is_draft ON notes(is_draft);

-- Update any existing notes to be non-drafts (they're already saved)
UPDATE notes SET is_draft = FALSE WHERE is_draft IS NULL;
