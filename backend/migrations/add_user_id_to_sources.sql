-- Migration: Add user_id column to sources table
-- This migration adds user-level isolation to sources, ensuring users can only see their own sources
-- Run this script against your database to apply the migration

-- Step 1: Add user_id column (nullable initially to handle existing data)
ALTER TABLE sources 
ADD COLUMN IF NOT EXISTS user_id TEXT;

-- Step 2: Create index for performance
CREATE INDEX IF NOT EXISTS idx_sources_user_id ON sources(user_id);

-- Step 3: For existing sources without user_id, you may want to:
-- Option A: Set a default user_id (if you have a system/admin user)
-- UPDATE sources SET user_id = 'system' WHERE user_id IS NULL;

-- Option B: Delete orphaned sources (if you don't want to keep sources without user_id)
-- DELETE FROM sources WHERE user_id IS NULL;

-- Step 4: Make user_id NOT NULL after handling existing data
-- Uncomment the line below after you've handled existing data:
-- ALTER TABLE sources ALTER COLUMN user_id SET NOT NULL;

-- Note: After running this migration, restart your backend server for the changes to take effect.
