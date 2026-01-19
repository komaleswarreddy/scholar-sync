-- Migration: Add error_message column to sources table
-- Run this SQL script to add the error_message column to existing databases

-- Add error_message column if it doesn't exist
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 
        FROM information_schema.columns 
        WHERE table_name = 'sources' 
        AND column_name = 'error_message'
    ) THEN
        ALTER TABLE sources ADD COLUMN error_message VARCHAR;
        RAISE NOTICE 'Added error_message column to sources table';
    ELSE
        RAISE NOTICE 'error_message column already exists';
    END IF;
END $$;
