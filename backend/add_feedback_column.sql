-- Migration: Add feedback column to messages table
-- Run this SQL script to add the feedback column to existing databases

-- Add feedback column if it doesn't exist
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 
        FROM information_schema.columns 
        WHERE table_name = 'messages' 
        AND column_name = 'feedback'
    ) THEN
        ALTER TABLE messages ADD COLUMN feedback VARCHAR;
        RAISE NOTICE 'Added feedback column to messages table';
    ELSE
        RAISE NOTICE 'Feedback column already exists';
    END IF;
END $$;
